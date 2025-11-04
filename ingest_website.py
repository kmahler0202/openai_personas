"""
ingest_website.py
Crawl themxgroup.com, extract clean text, embed, and upsert to Pinecone.

Usage:
  python ingest_website.py
  # optional flags:
  python ingest_website.py --domain https://themxgroup.com/ --max-pages 600 --max-chars 3000000
"""

import os
import re
import sys
import time
import math
import argparse
from datetime import datetime
from typing import List, Dict, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

import requests
from bs4 import BeautifulSoup
import tldextract
from openai import OpenAI
from dotenv import load_dotenv

# Import your Pinecone upsert
from services.pinecone_db import upsert_vectors

# -----------------------
# Config (aligns w/ PDFs)
# -----------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

EMBEDDING_MODEL = "text-embedding-3-small"  # same as PDFs (1536 dims)
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 300

DEFAULT_DOMAIN = "https://themxgroup.com/"
DEFAULT_MAX_PAGES = 600          # safety rail for Starter tier
DEFAULT_MAX_TOTAL_CHARS = 3_000_000  # ~3M chars cap before embedding

HEADERS = {
    "User-Agent": "MX-IngestBot/1.0 (+https://themxgroup.com/) Python requests"
}
TIMEOUT = 15

SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".webp", ".ico", ".mp4", ".mp3", ".zip", ".rar",
    ".7z", ".gz", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
)

# -----------------------
# Helpers
# -----------------------
def normalize_url(base: str, href: str) -> str:
    if not href:
        return ""
    url = urljoin(base, href)
    # drop fragments
    parts = list(urlparse(url))
    parts[5] = ""  # fragment
    # strip utm_* and other noisy params
    qs = [(k, v) for k, v in parse_qsl(parts[4], keep_blank_values=False) if not k.lower().startswith("utm_")]
    parts[4] = urlencode(qs)
    # remove trailing slash normalization (except root)
    url = urlunparse(parts)
    if url.endswith("/") and url.count("/") > 2:
        url = url[:-1]
    return url

def is_same_site(root: str, url: str) -> bool:
    ru = urlparse(root)
    uu = urlparse(url)
    # allow apex + subdomain variants that share the same registered domain
    r_ext = tldextract.extract(ru.netloc)
    u_ext = tldextract.extract(uu.netloc)
    return (r_ext.domain == u_ext.domain and r_ext.suffix == u_ext.suffix)

def looks_html(resp: requests.Response) -> bool:
    ctype = resp.headers.get("Content-Type", "")
    return "text/html" in ctype or "application/xhtml+xml" in ctype

def is_skip_url(u: str) -> bool:
    if any(u.lower().endswith(ext) for ext in SKIP_EXTENSIONS):
        return True
    if u.startswith("mailto:") or u.startswith("tel:"):
        return True
    return False

def fetch(url: str) -> requests.Response | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200 and looks_html(r):
            return r
        return None
    except requests.RequestException:
        return None

def extract_main_text(html: str) -> Tuple[str, str]:
    """
    Returns (title, cleaned_text)
    Strips nav/header/footer/script/style/forms/aside; favors <main> if present.
    """
    soup = BeautifulSoup(html, "html.parser")

    # kill obvious noise
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    # remove common chrome
    for sel in ["header", "footer", "nav", "form", "aside"]:
        for tag in soup.select(sel):
            tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # prefer <main>, fall back to body
    main = soup.find("main")
    container = main if main else soup.body if soup.body else soup

    text = container.get_text(separator="\n", strip=True)
    # collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return title, text

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Dict]:
    """Same chunker as your PDF script (sentence/word friendly cut)."""
    chunks = []
    start = 0
    chunk_id = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

        if end < len(text):
            last_period = chunk_text.rfind('.')
            last_newline = chunk_text.rfind('\n')
            last_space = chunk_text.rfind(' ')
            break_point = max(last_period, last_newline, last_space)
            if break_point > chunk_size * 0.8:
                end = start + break_point + 1
                chunk_text = text[start:end]

        chunks.append({
            "chunk_id": chunk_id,
            "text": chunk_text.strip(),
            "start_char": start,
            "end_char": end,
            "length": len(chunk_text.strip())
        })
        chunk_id += 1
        start = end - overlap

    return chunks

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Batch embeds with OpenAI (same as PDFs)."""
    batch_size = 100
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch
        )
        all_embeddings.extend([d.embedding for d in resp.data])
    return all_embeddings

def prepare_vectors_for_page(chunks: List[Dict], embeddings: List[List[float]], doc_id: str, url: str, title: str) -> List[Dict]:
    vectors = []
    path = urlparse(url).path or "/"
    filenameish = path.strip("/").replace("/", "_") or "root"
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        vectors.append({
            "id": f"{doc_id}_{filenameish}_chunk_{idx}",
            "values": emb,
            "metadata": {
                "text": chunk["text"][:1000],  # keep metadata lean
                "source": "website",
                "source_url": url,
                "title": title[:200] if title else "",
                "chunk_id": chunk["chunk_id"],
                "doc_id": doc_id,
                "length": chunk["length"],
            }
        })
    return vectors

# -----------------------
# Crawling
# -----------------------
def get_sitemap_urls(domain: str) -> List[str]:
    candidates = [
        urljoin(domain, "/sitemap.xml"),
        urljoin(domain, "/sitemap_index.xml"),
        urljoin(domain, "/sitemap-index.xml"),
    ]
    found: List[str] = []
    seen: Set[str] = set()
    def parse_map(xml_url: str):
        try:
            r = requests.get(xml_url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code != 200 or "xml" not in r.headers.get("Content-Type", ""):
                return
            soup = BeautifulSoup(r.text, "xml")
            # nested index
            for loc in soup.find_all("sitemap"):
                loc_tag = loc.find("loc")
                if loc_tag and loc_tag.text and loc_tag.text not in seen:
                    seen.add(loc_tag.text)
                    parse_map(loc_tag.text)
            for loc in soup.find_all("loc"):
                u = loc.text.strip()
                if u and is_same_site(domain, u):
                    found.append(u)
        except requests.RequestException:
            pass

    for c in candidates:
        parse_map(c)

    # keep only html-like URLs from sitemap (often includes PDFs)
    htmlish = [u for u in set(found) if not is_skip_url(u)]
    return sorted(htmlish)

def crawl(domain: str, max_pages: int, seed_urls: List[str]) -> List[str]:
    queue: List[str] = seed_urls[:]
    seen: Set[str] = set(seed_urls)
    results: List[str] = []

    while queue and len(results) < max_pages:
        url = queue.pop(0)
        resp = fetch(url)
        if not resp:
            continue
        results.append(url)

        # discover more links
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                nu = normalize_url(url, a["href"])
                if not nu or is_skip_url(nu):
                    continue
                if not is_same_site(domain, nu):
                    continue
                if nu not in seen:
                    seen.add(nu)
                    queue.append(nu)
        except Exception:
            pass

    return results

# -----------------------
# Main ingestion
# -----------------------
def estimate_pinecone_storage(num_vectors: int, dim: int = 1536) -> float:
    """
    Rough estimate: float32 (4 bytes) * dim per vector + ~1KB metadata.
    Returns MB.
    """
    vec_bytes = num_vectors * dim * 4
    meta_bytes = num_vectors * 1024
    total_mb = (vec_bytes + meta_bytes) / (1024 * 1024)
    return total_mb

def ingest_site(domain: str, max_pages: int, max_total_chars: int) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    doc_id = f"website_{tldextract.extract(urlparse(domain).netloc).domain}_{ts}"

    print("\n" + "="*70)
    print("🌐 WEBSITE INGEST")
    print("="*70)
    print(f"Domain: {domain}")
    print(f"Max pages: {max_pages}")
    print(f"Max total chars: {max_total_chars:,}")
    print(f"Doc ID: {doc_id}\n")

    # 1) gather URLs (sitemap preferred)
    print("🔎 Discovering URLs via sitemap…")
    site_urls = get_sitemap_urls(domain)
    if site_urls:
        print(f"✅ Found {len(site_urls)} URLs from sitemap.")
        seeds = site_urls[:max_pages]
    else:
        print("⚠️  No sitemap found. Falling back to BFS from homepage.")
        seeds = [domain.rstrip("/")]
    seeds = [normalize_url(domain, u) for u in seeds]
    seeds = [u for u in seeds if u and is_same_site(domain, u) and not is_skip_url(u)]
    seeds = list(dict.fromkeys(seeds))  # de-dupe preserve order

    # 2) if sitemap small or absent, BFS crawl to expand
    if len(seeds) < max_pages:
        print("🔄 Expanding URL set via internal crawl…")
        urls = crawl(domain, max_pages=max_pages, seed_urls=seeds)
    else:
        urls = seeds[:max_pages]

    print(f"✅ Total candidate pages: {len(urls)}\n")

    total_chars = 0
    total_chunks = 0
    total_vectors = 0
    page_count = 0

    all_vectors: List[Dict] = []

    # 3) process pages
    for i, url in enumerate(urls, start=1):
        if total_chars >= max_total_chars:
            print(f"⛔ Reached max_total_chars={max_total_chars:,}. Stopping.")
            break

        print(f"[{i}/{len(urls)}] GET {url}")
        resp = fetch(url)
        if not resp:
            print("   …skip (not HTML / non-200)")
            continue

        title, text = extract_main_text(resp.text)
        text_len = len(text)
        if text_len < 200:
            print("   …skip (thin page)")
            continue

        # cap if this page would exceed max chars
        allowed = max_total_chars - total_chars
        if text_len > allowed:
            text = text[:allowed]
            text_len = len(text)
            print(f"   …truncated to fit char budget ({text_len} chars)")

        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            print("   …skip (no chunks)")
            continue

        texts = [c["text"] for c in chunks]
        embeddings = generate_embeddings(texts)
        vectors = prepare_vectors_for_page(chunks, embeddings, doc_id, url, title)

        # accumulate
        all_vectors.extend(vectors)
        total_chars += text_len
        total_chunks += len(chunks)
        total_vectors += len(vectors)
        page_count += 1

        print(f"   ✅ {text_len:,} chars → {len(chunks)} chunks → {len(vectors)} vectors")

        # Optional: flush every N pages to Pinecone to keep memory low
        if len(all_vectors) >= 1000:
            print("   ⬆️  Flushing vectors in batches of 100…")
            batch = 100
            for i in range(0, 1000, batch):
                upsert_vectors(all_vectors[i:i+batch])
            all_vectors = all_vectors[1000:]

    # final flush
    if all_vectors:
        print(f"\n⬆️  Final upload of {len(all_vectors)} vectors to Pinecone in batches of 100…")
        batch = 100
        for i in range(0, len(all_vectors), batch):
            upsert_vectors(all_vectors[i:i+batch])

    est_mb = estimate_pinecone_storage(total_vectors)
    print("\n" + "="*70)
    print("✅ WEBSITE INGEST COMPLETE")
    print("="*70)
    print(f"Doc ID:           {doc_id}")
    print(f"Pages processed:  {page_count}")
    print(f"Total characters: {total_chars:,}")
    print(f"Total chunks:     {total_chunks}")
    print(f"Total vectors:    {total_vectors}")
    print(f"Est. PC storage:  ~{est_mb:.1f} MB (Starter limit 2048 MB)")
    print("="*70 + "\n")

    return doc_id

# -----------------------
# CLI
# -----------------------
def main():
    parser = argparse.ArgumentParser(description="Ingest website into Pinecone.")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help="Domain root to crawl (default: themxgroup.com)")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="Max pages to crawl")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_TOTAL_CHARS, help="Global character budget")
    args = parser.parse_args()

    ingest_site(args.domain, args.max_pages, args.max_chars)

if __name__ == "__main__":
    main()

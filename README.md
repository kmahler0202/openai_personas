# OpenAI API Test Directory

An AI-powered marketing automation platform that provides three core tools for marketing professionals: Buyer Ecosystem & Personas Generation, Deck Generation, and RFP LaunchPad.

## 🎯 Overview

This Flask-based application integrates with OpenAI's API, Pinecone vector database, and Google Workspace services to automate complex marketing tasks. It processes webhook requests from forms and delivers results via email.

## ✨ Features

### 1. **Buyer Ecosystem, Personas, and Content Recommendations**
Generates detailed buyer personas and marketing insights based on product categories, target markets, and geographies.

### 2. **Deck Generation**
Automatically creates professional PowerPoint presentations based on text descriptions, complete with:
- AI-generated outlines and content
- Professional formatting and templates
- Email delivery with attachments

### 3. **RFP LaunchPad**
Streamlines RFP (Request for Proposal) response workflows:
- Extracts and analyzes RFP documents from Google Drive
- Breaks down RFPs into 6 key categories:
  - Background & Context
  - Objectives/Problem Statements
  - Evaluation Criteria & Decision Logic
  - Rules/Response Guidelines/Format Instructions
  - Statement of Need/Scope of Work
  - Questions That Need to Be Answered
- Uses RAG (Retrieval-Augmented Generation) to answer questions using company knowledge base
- Emails formatted answers with relevance scores and metadata

## 🏗️ Architecture

```
openai_api_test_dir/
├── app.py                    # Main Flask application with webhook endpoints
├── processes/                # Core business logic modules
│   ├── persona_gen/         # Buyer persona generation
│   ├── deck_gen/            # PowerPoint deck generation
│   └── rfp_launchpad/       # RFP breakdown and answering
├── services/                 # External service integrations
│   ├── google_auth.py       # Google OAuth authentication
│   ├── gdrive_service.py    # Google Drive operations
│   ├── gmail_service.py     # Gmail email sending
│   └── pinecone_db.py       # Pinecone vector database operations
├── ingest_pdfs.py           # PDF document ingestion to vector DB
├── ingest_website.py        # Website crawling and ingestion to vector DB
└── test_rag.py              # RAG testing and query interface
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key
- Pinecone account and API key
- Google Cloud project with Drive and Gmail API enabled
- Google OAuth credentials

### Installation

1. **Clone the repository**
   ```bash
   cd openai_api_test_dir
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_ENVIRONMENT=your_pinecone_environment
   PINECONE_INDEX_NAME=your_index_name
   WEBHOOK_SECRET=your_webhook_secret  # Optional for local dev
   PORT=8080  # Optional, defaults to 8080
   ```

5. **Set up Google OAuth**
   
   Place your Google OAuth credentials in `services/auth/credentials.json`

### Running the Application

**Development Server:**
```bash
python app.py
```

The server will start on `http://0.0.0.0:8080`

**Production (with Gunicorn):**
```bash
gunicorn app:app --bind 0.0.0.0:8080
```

## 📚 Usage

### Webhook Endpoint

The main endpoint is `/forms-webhook` which accepts POST requests with form data.

**Request Format:**
```json
{
  "Product Category": "Software",
  "Target Market Segments": "Enterprise",
  "Target Geographies": "North America",
  "MX Email": "user@example.com",
  "Client": "Acme Corp",
  "Select Desired Tool": "Buyer Ecosystem, Personas, and Content Reccomendations",
  "Description": "Create a deck about our product",
  "Submit RFP Here": ["google_drive_file_id"]
}
```

**Authentication:**
Include `X-Webhook-Secret` header if `WEBHOOK_SECRET` is configured.

### Knowledge Base Management

**Ingest PDF Documents:**
```bash
# Single file
python ingest_pdfs.py path/to/document.pdf

# Directory (batch)
python ingest_pdfs.py --dir path/to/documents/
```

**Ingest Website Content:**
```bash
python ingest_website.py --domain https://yourcompany.com --max-pages 500
```

**Test RAG System:**
```bash
# Single question
python test_rag.py "What is your approach to marketing campaigns?"

# Interactive mode
python test_rag.py --interactive

# Show retrieved context
python test_rag.py --context "Your question here"
```

## 🔧 Configuration

### Vector Database Settings

- **Embedding Model:** `text-embedding-3-small` (1536 dimensions)
- **Chunk Size:** 1500 characters
- **Chunk Overlap:** 300 characters
- **Top K Retrieval:** 20 chunks (configurable)

### AI Models

- **RFP Breakdown:** `gpt-5`
- **RFP Answering:** `gpt-4o-mini`
- **RAG Testing:** `gpt-4o-mini` (configurable to `gpt-4o`)

## 📁 Key Components

### Core Modules

- **`app.py`** - Flask application with webhook routing and orchestration
- **`processes/persona_gen/`** - Buyer persona generation logic
- **`processes/deck_gen/`** - PowerPoint deck creation pipeline
- **`processes/rfp_launchpad/`** - RFP analysis and answering system

### Services

- **`services/google_auth.py`** - Google OAuth 2.0 authentication
- **`services/gdrive_service.py`** - Google Drive file operations and PDF extraction
- **`services/gmail_service.py`** - Email composition and sending with attachments
- **`services/pinecone_db.py`** - Vector database operations (upsert, query)

### Utilities

- **`ingest_pdfs.py`** - PDF text extraction, chunking, embedding, and vector storage
- **`ingest_website.py`** - Web crawling, text extraction, and vector storage
- **`test_rag.py`** - RAG pipeline testing and interactive query interface

## 🔐 Security

- API keys stored in `.env` file (gitignored)
- Google OAuth credentials in `services/auth/credentials.json` (gitignored)
- Webhook secret validation for production endpoints
- Token-based authentication with Google services

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Hello world test endpoint |
| `/health` | GET | Health check endpoint |
| `/version` | GET | Returns application version |
| `/forms-webhook` | POST | Main webhook for processing form submissions |

## 🛠️ Development

### Project Structure

```
processes/
├── persona_gen/          # Persona generation
│   └── generate_personas.py
├── deck_gen/             # Deck generation
│   ├── generate_deck.py
│   ├── outline_generator.py
│   ├── content_generator.py
│   ├── build_deck.py
│   └── outline_to_ppt.py
└── rfp_launchpad/        # RFP processing
    ├── rfp_breakdown.py
    └── rfp_answer.py
```

### Adding New Tools

1. Create a new module in `processes/`
2. Implement the core logic
3. Add routing logic in `app.py` under `/forms-webhook`
4. Update form payload normalization in `_normalize_payload()`

## 🧪 Testing

Test the RAG system:
```bash
python test_rag.py "Your test question"
```

Test individual components:
```bash
# Test persona generation
python -m processes.persona_gen.generate_personas

# Test deck generation
python -m processes.deck_gen.generate_deck
```

## 📝 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for embeddings and completions |
| `PINECONE_API_KEY` | Yes | Pinecone API key for vector database |
| `PINECONE_ENVIRONMENT` | Yes | Pinecone environment (e.g., `us-east-1-aws`) |
| `PINECONE_INDEX_NAME` | Yes | Name of your Pinecone index |
| `WEBHOOK_SECRET` | No | Secret for webhook authentication (optional for local dev) |
| `PORT` | No | Server port (defaults to 8080) |

## 🤝 Contributing

This is an internal testing directory for OpenAI API integrations.

## 📄 License

Internal use only.

## 🐛 Troubleshooting

### Common Issues

**"Missing OPENAI_API_KEY in .env file"**
- Ensure `.env` file exists in project root
- Verify `OPENAI_API_KEY` is set correctly

**"Pinecone connection failed"**
- Check `PINECONE_API_KEY` and `PINECONE_ENVIRONMENT`
- Verify index exists in Pinecone dashboard

**"Google authentication failed"**
- Ensure `credentials.json` is in `services/auth/`
- Delete `token.json` and re-authenticate
- Verify Google Drive and Gmail APIs are enabled

**"No relevant context found"**
- Ingest documents using `ingest_pdfs.py` or `ingest_website.py`
- Verify documents were successfully uploaded to Pinecone

## 📞 Support

For issues or questions, contact the development team.

---

**Built with:** OpenAI API, Pinecone, Flask, Google Workspace APIs
# Sentiment Intelligence Dashboard

A brand sentiment analysis application that scrapes social media data, processes sentiment information, and visualizes brand insights using a graph-based approach with Neo4j.

Repository: https://github.com/rugvedp/reddit_sentiment_graph_rag

![demo gif](ezgif-784871d70fcf98b1.gif)

Neo4j Database

![Neo4j Graph](image.png)

## Features

- 📊 **Real-time Sentiment Analysis** - Analyze brand sentiment from Reddit
- 🎨 **Interactive Dashboard** - Streamlit-based web interface  
- 📈 **Graph Database** - Neo4j backend for relationship data
- 🤖 **AI-Powered Chatbot** - Chat with sentiment data using Groq LLM
- 🧠 **Semantic Embeddings** - SentenceTransformers for semantic understanding
- 🔄 **ETL Pipeline** - Complete data ingestion and processing
- 💻 **CLI Tool** - Command-line batch processing

## Tech Stack

- **Frontend**: Streamlit
- **Database**: Neo4j
- **LLM**: Groq API (Llama models)
- **Embeddings**: SentenceTransformers
- **ML**: scikit-learn, PyTorch
- **Viz**: PyVis, Streamlit

## Prerequisites

- Python 3.11+
- Neo4j (local or cloud)
- Groq API key

## Quick Start

### Fastest Setup (One Command)
```bash
make setup
```

This will:
- Check for uv installation (or tell you how to install)
- Create virtual environment
- Install all dependencies
- Create `.env` file
- You just need to add your GROQ_API_KEY

### Step 1: Setup Python Environment

**Option A: Using uv (Recommended - Fast & Simple)**
```bash
# Install uv if not already installed
# macOS: brew install uv
# Linux: pip install uv
# or see https://docs.astral.sh/uv/

# Create virtual environment and install dependencies
uv sync

# Activate venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

**Option B: Using pip**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Option C: Using Makefile**
```bash
make setup       # Full setup
make install     # Just install deps
make dev         # Install with dev tools
```

### Step 2: Install Neo4j
**Local Option:**
- Download from [neo4j.com/download](https://neo4j.com/download/)
- Install and start the service
- Connection: `bolt://localhost:7687`

**Cloud Option:**
- Use [Neo4j Aura](https://neo4j.com/cloud/)
- Get connection string from dashboard

### Step 3: Create .env File
```bash
cat > .env << EOF
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
GROQ_API_KEY=your_api_key_here
EOF
```

### Step 4: Get Groq API Key
1. Sign up at [console.groq.com](https://console.groq.com)
2. Create API key
3. Add to `.env`

### Step 5: Run Dashboard
```bash
streamlit run main.py
```

Open your browser to `http://localhost:8501`

## Usage

### Quick Commands with Make
```bash
make dashboard              # Start dashboard
make cli BRAND=nvidia       # Run CLI ingestion
make lint                   # Format & lint
make clean                  # Clean cache
```

### Using uv Commands

```bash
# Run dashboard with uv
uv run streamlit run main.py

# Run CLI ingestion with uv
uv run python cli_ingest.py "nvidia"

# Add new dependency
uv pip install package-name

# Update dependencies
uv sync --upgrade
```

### Using Direct Commands (After Activation)

```bash
# Activate venv first
source .venv/bin/activate

# Run dashboard
streamlit run main.py

# Run CLI ingestion
python cli_ingest.py "nvidia"
```

## Project Structure
```
graph_brand_sentiment/
├── main.py                 # Streamlit dashboard
├── cli_ingest.py          # CLI ingestion tool
├── requirements.txt       # Dependencies
├── .env                   # Configuration (create locally)
├── core/
│   ├── config.py          # App configuration
│   ├── database.py        # Neo4j manager
│   └── schemas.py         # Data models
├── modules/
│   ├── scraper.py         # Reddit scraper
│   ├── pipeline.py        # ETL pipeline
│   └── chatbot.py         # AI chatbot
└── utils/
    ├── logger.py          # Logging
    └── visualization.py   # Graph viz
```

## Configuration

Edit `core/config.py` to customize:
- Embedding model
- LLM models
- Device (CPU/GPU/MPS)
- Thread pools

Environment variables in `.env`:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
GROQ_API_KEY=your_api_key
```

## Troubleshooting

### Neo4j Not Connected
```bash
# Check if running
curl -u neo4j:password http://localhost:7474

# Verify connection string
bolt://username:password@localhost:7687
```

### API Errors
- Check GROQ_API_KEY in `.env`
- Verify API quota
- Check internet connection

### Memory Issues
- Reduce batch size in `core/config.py`
- Use CPU mode instead of GPU
- Close other applications

### Model Downloads
- First run downloads ~400MB embedding model
- Stored in `~/.cache/huggingface/`
- Requires internet on first run

## Dependencies

Managed via `pyproject.toml` and `uv`:

**Core:**
- streamlit: Web dashboard
- neo4j: Graph database driver
- groq: LLM API client
- sentence-transformers: Embeddings
- torch: Deep learning
- scikit-learn: ML utilities
- pyvis: Graph visualization
- pydantic: Data validation

**Dev (optional):**
- black: Code formatter
- ruff: Linter
- pytest: Testing

Install dev dependencies:
```bash
uv sync --all-extras
```

See `pyproject.toml` for complete list.

## Support

Having issues?
1. Check troubleshooting section
2. Verify `.env` configuration
3. Ensure Neo4j is running
4. Check API key validity

## License

MIT License

---

**Local Development Only** - For production, Docker setup available upon request.

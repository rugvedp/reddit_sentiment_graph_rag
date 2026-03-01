#!/bin/bash
# Quick setup script for local development with uv

echo "🚀 Sentiment Dashboard - Local Setup"
echo "===================================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed"
    echo "Install it with:"
    echo "  macOS: brew install uv"
    echo "  Linux: pip install uv"
    echo "  Windows: https://docs.astral.sh/uv/installation/"
    exit 1
fi

echo "✅ uv found: $(uv --version)"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file..."
    cat > .env << EOF
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
GROQ_API_KEY=your_api_key_here
EOF
    echo "✓ .env created"
    echo "⚠️  Edit .env and add your GROQ_API_KEY"
fi

# Sync dependencies
echo ""
echo "📦 Installing dependencies with uv..."
uv sync

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add GROQ_API_KEY"
echo "  2. Start Neo4j locally"
echo "  3. Run: uv run streamlit run main.py"
echo ""
echo "Commands:"
echo "  uv run streamlit run main.py          # Start dashboard"
echo "  uv run python cli_ingest.py 'nvidia'  # Run ingestion"
echo "  source .venv/bin/activate             # Activate venv"
echo "  deactivate                            # Deactivate venv"

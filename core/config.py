import os
import torch
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Resource Management
    CORES = max(1, int((os.cpu_count() or 4) * 0.7))
    DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
    
    # API / DB
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USER = os.getenv("NEO4J_USER")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
    
    # Models
    EMBED_MODEL = "all-mpnet-base-v2"
    EXTRACT_MODEL = "llama-3.1-8b-instant"
    CHAT_MODEL = "llama-3.3-70b-versatile"
    # openai/gpt-oss-120b
    # llama-3.3-70b-versatile
    @staticmethod
    def init_environment():
        os.environ["OMP_NUM_THREADS"] = str(Config.CORES)
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
import os
from pathlib import Path
from dotenv import load_dotenv

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# API Keys: Unify into a single key to avoid SDK duplication notice
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
GOOGLE_API_KEY = GEMINI_API_KEY

# Set only GEMINI_API_KEY in environment to prevent "Both keys are set" notice
if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
    if "GOOGLE_API_KEY" in os.environ:
        del os.environ["GOOGLE_API_KEY"]

# Hugging Face Token for serverless embeddings
HUGGINGFACE_API_KEY = (
    os.getenv("HUGGINGFACEHUB_API_TOKEN")
    or os.getenv("HUGGINGFACE_API_KEY")
    or os.getenv("HF_TOKEN", "")
)
HUGGINGFACEHUB_API_TOKEN = HUGGINGFACE_API_KEY

if HUGGINGFACE_API_KEY:
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = HUGGINGFACE_API_KEY
    os.environ["HF_TOKEN"] = HUGGINGFACE_API_KEY

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

DOCUMENTS_DIR = BASE_DIR / "documents"
DATA_DIR = BASE_DIR / "data"
CHUNKS_FILE = DATA_DIR / "chunks.json"

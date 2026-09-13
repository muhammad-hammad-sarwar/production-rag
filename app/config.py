import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_ENDPOINT = os.getenv("QDRANT_ENDPOINT")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-120b"
ENVIRONMENT="development"
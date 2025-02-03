import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
MODEL = os.getenv("MODEL")
# Add further configuration variables as needed 
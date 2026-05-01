import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("OLLAMA_BASE_URL")
MODEL = os.getenv("OLLAMA_MODEL")

def call_ollama(text):
    url = f"{BASE_URL}/v1/chat/completions"

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是发票识别助手"},
            {"role": "user", "content": text}
        ]
    }

    response = requests.post(url, json=data)

    return response.json()
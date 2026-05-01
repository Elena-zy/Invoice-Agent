import os
from dotenv import load_dotenv

from services.dify_service import call_dify_agent
from services.qwen_service import call_qwen
from services.ollama_service import call_ollama

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER")


def call_llm(text):
    if PROVIDER == "dify":
        return call_dify_agent(text)

    elif PROVIDER == "qwen":
        return call_qwen(text)

    elif PROVIDER == "ollama":
        return call_ollama(text)

    else:
        return {
            "error": True,
            "message": "未配置 LLM_PROVIDER"
        }
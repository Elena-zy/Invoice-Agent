import os
import uuid
import requests
from dotenv import load_dotenv

load_dotenv()

DIFY_API_URL = os.getenv("DIFY_API_URL")
DIFY_API_KEY = os.getenv("DIFY_API_KEY")


def call_dify_agent(text):
    if not DIFY_API_URL or not DIFY_API_KEY:
        return {
            "error": True,
            "message": "请先在 .env 中配置 DIFY_API_URL 和 DIFY_API_KEY"
        }

    data = {
        "inputs": {
            "text": text
        },
        "query": text,
        "response_mode": "blocking",
        "user": str(uuid.uuid4())
    }

    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            DIFY_API_URL,
            headers=headers,
            json=data,
            timeout=120
        )

        try:
            result = response.json()
        except Exception:
            return {
                "error": True,
                "message": "Dify 返回的不是 JSON",
                "raw": response.text
            }

        if result.get("code") or result.get("status") == 400:
            return {
                "error": True,
                "message": result.get("message", "Dify 调用失败"),
                "raw": result
            }

        return result

    except Exception as e:
        return {
            "error": True,
            "message": str(e)
        }


def extract_answer(result):
    if not result:
        return ""

    if "answer" in result:
        return result.get("answer", "")

    if "data" in result:
        data = result.get("data", {})
        if isinstance(data, dict):
            outputs = data.get("outputs", {})
            if isinstance(outputs, dict):
                if "answer" in outputs:
                    return outputs["answer"]
                if "text" in outputs:
                    return outputs["text"]

    return ""
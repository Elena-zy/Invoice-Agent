import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

QWEN_API_KEY = os.getenv("QWEN_API_KEY")

QWEN_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


STRICT_PROMPT = """
你是一个发票信息抽取程序。

你的任务：从用户提供的PDF文本中抽取发票信息。

你只能输出 JSON 数组，不能输出任何解释、总结、markdown、标题、符号或额外文字。

输出格式必须严格如下：

[
  {
    "file_name": "",
    "invoice_number": "",
    "city": "",
    "type": "",
    "amount": 0,
    "date": "",
    "invoice_title": "",
    "seller": "",
    "is_abnormal": false,
    "abnormal_reason": ""
  }
]

字段规则：
1. invoice_number：发票号码。
2. date：开票日期，格式必须是 YYYY-MM-DD。
3. invoice_title：购买方名称。
4. seller：销售方名称。
5. amount：价税合计小写金额，必须是数字。
6. type：只能是 餐饮、交通、住宿、办公、通信、出行、其他。
7. city：从销售方或发票内容判断，无法判断则为空字符串。
8. 无法判断的字段填空字符串或0。
9. 不要编造信息。

重要要求：
只返回 JSON 数组。
不要返回说明文字。
不要返回“以下是”。
不要返回 markdown。
不要返回 ```json。
"""


def _request_qwen(messages):
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "qwen-plus",
        "messages": messages,
        "temperature": 0.01
    }

    response = requests.post(
        QWEN_URL,
        headers=headers,
        json=data,
        timeout=120
    )

    return response.json()


def _extract_content(result):
    try:
        return result["choices"][0]["message"]["content"]
    except Exception:
        return ""


def _is_json_array(text):
    try:
        data = json.loads(text)
        return isinstance(data, list)
    except Exception:
        return False


def call_qwen(text):
    if not QWEN_API_KEY:
        return {
            "error": True,
            "message": "请先在 .env 中配置 QWEN_API_KEY"
        }

    messages = [
        {
            "role": "system",
            "content": STRICT_PROMPT
        },
        {
            "role": "user",
            "content": f"请抽取下面PDF文本中的发票信息，只返回JSON数组：\n\n{text}"
        }
    ]

    result = _request_qwen(messages)
    content = _extract_content(result)

    # 如果第一次不是JSON数组，再强制修复一次
    if not _is_json_array(content):
        repair_messages = [
            {
                "role": "system",
                "content": "你是JSON格式修复工具。你只能输出合法JSON数组，不能输出任何解释。"
            },
            {
                "role": "user",
                "content": f"""
请把下面内容转换成合法 JSON 数组。

要求：
1. 只输出 JSON 数组
2. 不要解释
3. 不要 markdown
4. amount 必须是数字
5. date 格式必须是 YYYY-MM-DD

原始内容：
{text}
"""
            }
        ]

        result = _request_qwen(repair_messages)

    return result
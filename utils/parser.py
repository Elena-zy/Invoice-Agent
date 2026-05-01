import json
import re


def parse_json(answer):
    if not answer:
        return []

    answer = answer.strip()
    answer = answer.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(answer)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
    except Exception:
        pass

    array_match = re.search(r"\[.*\]", answer, re.DOTALL)
    if array_match:
        try:
            data = json.loads(array_match.group())
            if isinstance(data, list):
                return data
        except Exception:
            pass

    obj_match = re.search(r"\{.*\}", answer, re.DOTALL)
    if obj_match:
        try:
            data = json.loads(obj_match.group())
            return [data]
        except Exception:
            pass

    return []
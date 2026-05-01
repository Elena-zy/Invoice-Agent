import re

ALLOWED_TYPES = ["餐饮", "交通", "住宿", "办公", "通信", "其他"]


def clean_amount(value):
    if value is None:
        return 0

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value)
    value = value.replace("￥", "")
    value = value.replace("¥", "")
    value = value.replace("元", "")
    value = value.replace(",", "")
    value = value.strip()

    match = re.search(r"\d+(\.\d+)?", value)

    if match:
        return float(match.group())

    return 0


def validate_item(item):
    if not isinstance(item, dict):
        item = {}

    expense_type = item.get("type", "")

    if expense_type not in ALLOWED_TYPES:
        expense_type = "其他"

    amount = clean_amount(item.get("amount", 0))

    is_abnormal = bool(item.get("is_abnormal", False))
    abnormal_reason = item.get("abnormal_reason", "")

    if amount == 0:
        is_abnormal = True
        abnormal_reason = abnormal_reason or "未识别到金额"

    if not item.get("date"):
        is_abnormal = True
        abnormal_reason = abnormal_reason or "未识别到日期"

    return {
        "来源": item.get("source", ""),
        "文件名": item.get("file_name", ""),
        "发票号码": item.get("invoice_number", ""),
        "城市": item.get("city", ""),
        "类型": expense_type,
        "金额": amount,
        "日期": item.get("date", ""),
        "发票抬头": item.get("invoice_title", ""),
        "销售方": item.get("seller", ""),
        "状态": "异常" if is_abnormal else "正常",
        "异常原因": abnormal_reason
    }
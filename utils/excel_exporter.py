import tempfile
from openpyxl import Workbook


def generate_excel(results):
    wb = Workbook()
    ws = wb.active
    ws.title = "发票报销表"

    headers = [
        "来源",
        "文件名",
        "发票号码",
        "城市",
        "类型",
        "金额",
        "日期",
        "发票抬头",
        "销售方",
        "状态",
        "异常原因"
    ]

    ws.append(headers)

    for item in results:
        ws.append([item.get(h, "") for h in headers])

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(tmp.name)

    return tmp.name
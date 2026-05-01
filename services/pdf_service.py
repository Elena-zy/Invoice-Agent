import fitz
import re


def extract_pdf_text_from_file(uploaded_file):
    file_bytes = uploaded_file.read()
    pdf = fitz.open(stream=file_bytes, filetype="pdf")

    all_text = f"\n\n===== 文件名：{uploaded_file.name} =====\n"

    for page_num, page in enumerate(pdf, start=1):
        text = page.get_text()
        all_text += f"\n--- 第 {page_num} 页 ---\n{text}"

    return all_text


def extract_pdf_text_from_path(file_path):
    pdf = fitz.open(file_path)

    all_text = f"\n\n===== 文件名：{file_path} =====\n"

    for page_num, page in enumerate(pdf, start=1):
        text = page.get_text()
        all_text += f"\n--- 第 {page_num} 页 ---\n{text}"

    return all_text


def clean_pdf_text(text):
    if not text:
        return ""

    text = text.replace("\u3000", " ")
    text = text.replace("￥", "¥")
    text = text.replace("：", ":")
    text = text.replace("，", ",")
    text = text.replace("。", ".")
    text = text.replace("（", "(").replace("）", ")")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)

    return text.strip()
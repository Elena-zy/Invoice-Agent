import imaplib
import email
import os
import re
from email.header import decode_header
from datetime import datetime, timedelta
from pathlib import Path
import email
from datetime import datetime, timedelta


EMAIL_PROVIDERS = {
    "QQ邮箱": {
        "imap_server": "imap.qq.com",
        "imap_port": 993
    },
    "163邮箱": {
        "imap_server": "imap.163.com",
        "imap_port": 993
    },
    "126邮箱": {
        "imap_server": "imap.126.com",
        "imap_port": 993
    }
}


def decode_mime_words(value):
    if not value:
        return ""

    decoded_parts = decode_header(value)
    result = ""

    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                result += part.decode(charset or "utf-8", errors="ignore")
            except Exception:
                result += part.decode("utf-8", errors="ignore")
        else:
            result += part

    return result


def safe_filename(filename):
    filename = decode_mime_words(filename)
    filename = re.sub(r'[\\/:*?"<>|]', "_", filename)
    return filename


def connect_email(provider_name, email_account, auth_code):
    provider = EMAIL_PROVIDERS[provider_name]

    mail = imaplib.IMAP4_SSL(
        provider["imap_server"],
        provider["imap_port"]
    )

    mail.login(email_account, auth_code)
    return mail


def search_invoice_emails(mail, days=30):
    mail.select("INBOX")

    since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")

    search_queries = [
        f'(SINCE "{since_date}" SUBJECT "发票")',
        f'(SINCE "{since_date}" SUBJECT "电子发票")',
        f'(SINCE "{since_date}" TEXT "发票")',
        f'(SINCE "{since_date}" TEXT "invoice")'
    ]

    all_ids = set()

    for query in search_queries:
        try:
            status, data = mail.search(None, query)
            if status == "OK" and data and data[0]:
                ids = data[0].split()
                all_ids.update(ids)
        except Exception:
            continue

    return list(all_ids)


def download_pdf_attachments(mail, message_ids, save_dir="downloads"):
    Path(save_dir).mkdir(exist_ok=True)

    downloaded_files = []

    for message_id in message_ids:
        status, msg_data = mail.fetch(message_id, "(RFC822)")

        if status != "OK":
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = decode_mime_words(msg.get("Subject", ""))
        sender = decode_mime_words(msg.get("From", ""))

        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            filename = part.get_filename()

            if not filename:
                continue

            filename = safe_filename(filename)

            if not filename.lower().endswith(".pdf"):
                continue

            file_data = part.get_payload(decode=True)

            if not file_data:
                continue

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_path = os.path.join(save_dir, f"{timestamp}_{filename}")

            with open(file_path, "wb") as f:
                f.write(file_data)

            downloaded_files.append({
                "file_path": file_path,
                "file_name": filename,
                "subject": subject,
                "sender": sender
            })

    return downloaded_files


def close_email(mail):
    try:
        mail.close()
    except Exception:
        pass

    try:
        mail.logout()
    except Exception:
        pass

    import email
from datetime import datetime, timedelta

def search_invoice_emails(mail, days=7, max_results=20):
    mail.select("INBOX")

    since_date = datetime.now() - timedelta(days=days)

    # 不用中文搜索，避免 IMAP ascii 编码报错
    status, data = mail.search(None, "ALL")

    if status != "OK":
        return []

    message_ids = data[0].split()

    valid_ids = []

    for msg_id in reversed(message_ids):
        status, msg_data = mail.fetch(msg_id, "(RFC822.HEADER)")

        if status != "OK":
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # 时间过滤
        date_str = msg.get("Date")

        try:
            msg_date = email.utils.parsedate_to_datetime(date_str)
        except Exception:
            continue

        if msg_date.replace(tzinfo=None) < since_date:
            continue

        # 标题过滤
        subject = decode_mime_words(msg.get("Subject", ""))
        subject_lower = subject.lower()

        keywords = ["发票", "电子发票", "invoice"]

        if not any(keyword in subject_lower for keyword in keywords):
            continue

        valid_ids.append(msg_id)

        if len(valid_ids) >= max_results:
            break

    return valid_ids
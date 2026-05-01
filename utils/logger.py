import csv
import os
from datetime import datetime

LOG_FILE = "test_logs.csv"

HEADERS = [
    "测试轮次",
    "测试时间",
    "来源",
    "文件名",
    "是否成功",
    "金额",
    "状态",
    "异常原因",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "耗时秒"
]


def write_test_log(
    test_round="",
    source="",
    file_name="",
    is_success=False,
    amount=0,
    status="",
    abnormal_reason="",
    prompt_tokens=0,
    completion_tokens=0,
    total_tokens=0,
    duration_seconds=0
):
    file_exists = os.path.exists(LOG_FILE)

    with open(LOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(HEADERS)

        writer.writerow([
            test_round,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            source,
            file_name,
            "成功" if is_success else "失败",
            amount,
            status,
            abnormal_reason,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            round(duration_seconds, 2)
        ])
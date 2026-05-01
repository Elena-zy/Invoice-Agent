# app.py

import imaplib
import time
import streamlit as st

from services.pdf_service import (
    extract_pdf_text_from_file,
    extract_pdf_text_from_path,
    clean_pdf_text
)

from services.llm_service import call_llm

from services.email_service import (
    connect_email,
    search_invoice_emails,
    download_pdf_attachments,
    close_email
)

from utils.parser import parse_json
from utils.validator import validate_item
from utils.excel_exporter import generate_excel
from utils.logger import write_test_log
from utils.test_reporter import (
    load_logs,
    build_round_summary,
    build_total_summary,
    export_test_report,
    TOKEN_LIMIT
)


st.set_page_config(
    page_title="AI发票报销助手 V5",
    layout="wide"
)


def extract_answer_unified(result):
    if not result:
        return ""

    if isinstance(result, dict) and result.get("error"):
        return ""

    if isinstance(result, dict) and "answer" in result:
        return result.get("answer", "")

    if isinstance(result, dict) and "data" in result:
        data = result.get("data", {})
        if isinstance(data, dict):
            outputs = data.get("outputs", {})
            if isinstance(outputs, dict):
                if "answer" in outputs:
                    return outputs["answer"]
                if "text" in outputs:
                    return outputs["text"]

    if isinstance(result, dict) and "choices" in result:
        try:
            return result["choices"][0]["message"]["content"]
        except Exception:
            return ""

    return str(result)


def extract_usage(result):
    if not isinstance(result, dict):
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }

    usage = result.get("usage", {})

    return {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0)
    }


def build_error_result(source, file_name, reason):
    return {
        "来源": source,
        "文件名": file_name,
        "发票号码": "",
        "城市": "",
        "类型": "其他",
        "金额": 0,
        "日期": "",
        "发票抬头": "",
        "销售方": "",
        "状态": "异常",
        "异常原因": reason
    }


def recognize_text_to_results(text, source="", file_name="", debug=False):
    start_time = time.time()

    cleaned_text = clean_pdf_text(text)

    empty_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

    if not cleaned_text:
        duration = time.time() - start_time

        return [
            build_error_result(
                source,
                file_name,
                "PDF未读取到文字，可能是扫描版，需要OCR"
            )
        ], empty_usage, duration

    result = call_llm(cleaned_text)
    usage = extract_usage(result)

    if isinstance(result, dict) and result.get("error"):
        duration = time.time() - start_time

        return [
            build_error_result(
                source,
                file_name,
                f"AI调用失败：{result.get('message', '未知错误')}"
            )
        ], usage, duration

    answer = extract_answer_unified(result)
    data = parse_json(answer)

    if debug:
        with st.expander(f"调试信息：{file_name or source}"):
            st.write("清洗后的PDF文本：")
            st.text(cleaned_text)

            st.write("AI原始返回：")
            st.write(result)

            st.write("提取出的 answer：")
            st.write(answer)

            st.write("解析后的 JSON：")
            st.write(data)

            st.write("Token 使用：")
            st.json(usage)

    if not data:
        duration = time.time() - start_time

        return [
            build_error_result(
                source,
                file_name,
                "AI未返回有效JSON"
            )
        ], usage, duration

    results = []

    for item in data:
        if isinstance(item, dict):
            item["source"] = source
            item["file_name"] = file_name or item.get("file_name", "")
            results.append(validate_item(item))

    if not results:
        duration = time.time() - start_time

        return [
            build_error_result(
                source,
                file_name,
                "AI返回格式异常"
            )
        ], usage, duration

    duration = time.time() - start_time

    return results, usage, duration


def add_usage(total_usage, usage):
    total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
    total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
    total_usage["total_tokens"] += usage.get("total_tokens", 0)
    return total_usage


def log_results(test_round, results, usage, duration):
    for item in results:
        is_success = item.get("状态") == "正常"

        write_test_log(
            test_round=test_round,
            source=item.get("来源", ""),
            file_name=item.get("文件名", ""),
            is_success=is_success,
            amount=item.get("金额", 0),
            status=item.get("状态", ""),
            abnormal_reason=item.get("异常原因", ""),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            duration_seconds=duration
        )


def show_results(results, total_usage):
    if not results:
        st.warning("没有识别到发票信息")
        return

    st.success(f"识别完成，共识别 {len(results)} 条发票信息")

    total_amount = sum(float(item.get("金额", 0)) for item in results)
    abnormal_count = len([x for x in results if x.get("状态") == "异常"])
    success_count = len(results) - abnormal_count
    success_rate = success_count / len(results) if results else 0
    avg_token = total_usage.get("total_tokens", 0) / len(results) if results else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("发票数量", len(results))
    col2.metric("成功识别数量", success_count)
    col3.metric("异常数量", abnormal_count)
    col4.metric("成功率", f"{success_rate:.1%}")
    col5.metric("总 Token", int(total_usage.get("total_tokens", 0)))

    col6, col7 = st.columns(2)
    col6.metric("合计金额", f"{total_amount:.2f} 元")
    col7.metric("平均 Token / 张", f"{avg_token:.0f}")

    with st.expander("Token 消耗明细"):
        st.write(f"输入 Token：{total_usage.get('prompt_tokens', 0)}")
        st.write(f"输出 Token：{total_usage.get('completion_tokens', 0)}")
        st.write(f"总 Token：{total_usage.get('total_tokens', 0)}")

    st.dataframe(results, use_container_width=True)

    excel_path = generate_excel(results)

    with open(excel_path, "rb") as f:
        st.download_button(
            label="📥 下载Excel发票表",
            data=f,
            file_name="发票报销表.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


def show_test_dashboard():
    logs_df = load_logs()

    if logs_df.empty:
        st.info("暂无测试记录。开启测试记录后，识别结果会自动写入 test_logs.csv。")
        return

    total_summary = build_total_summary(logs_df)
    round_summary = build_round_summary(logs_df)

    st.subheader("📊 测试总体汇总")

    total = total_summary.iloc[0]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("发票数量", int(total["发票数量"]))
    col2.metric("成功识别数量", int(total["成功识别数量"]))
    col3.metric("异常数量", int(total["异常数量"]))
    col4.metric("成功率", f"{total['成功率']:.1%}")
    col5.metric("总 Token", int(total["总Token"]))

    col6, col7, col8, col9 = st.columns(4)
    col6.metric("合计金额", f"{total['合计金额']:.2f} 元")
    col7.metric("平均 Token / 张", f"{total['平均Token/张']:.0f}")
    col8.metric("预计成本", f"{total['预计成本']:.4f} 元")
    col9.metric("平均识别耗时", f"{total['平均识别耗时']:.2f} 秒")

    st.subheader("💰 Token 预算控制")

    used_tokens = total["总Token"]
    remaining_tokens = TOKEN_LIMIT - used_tokens
    usage_rate = used_tokens / TOKEN_LIMIT

    st.write(f"Token 预算上限：{TOKEN_LIMIT}")
    st.write(f"已使用 Token：{int(used_tokens)}")
    st.write(f"剩余 Token：{int(remaining_tokens)}")
    st.progress(min(usage_rate, 1.0))

    if used_tokens >= TOKEN_LIMIT:
        st.error("Token 已超过 10 万预算，请暂停测试。")
    elif used_tokens >= TOKEN_LIMIT * 0.8:
        st.warning("Token 已使用超过 80%，建议控制后续测试规模。")
    else:
        st.success("Token 消耗仍在预算范围内。")

    st.subheader("📌 分轮测试指标")
    st.dataframe(round_summary, use_container_width=True)

    st.subheader("📄 测试明细")
    st.dataframe(logs_df, use_container_width=True)

    report_path = export_test_report()

    if report_path:
        with open(report_path, "rb") as f:
            st.download_button(
                label="📥 下载产品测试报告 Excel",
                data=f,
                file_name="产品测试报告.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


st.title("📊 AI发票报销助手 V5")
st.write("支持上传 PDF 发票，也支持通过 QQ邮箱 / 163邮箱 / 126邮箱授权码自动读取发票附件。")

with st.sidebar:
    st.header("🧪 测试设置")

    enable_test_log = st.checkbox("开启测试记录", value=True)

    test_round = st.text_input(
        "测试轮次",
        value="第1轮-功能测试",
        help="例如：第1轮-功能测试 / 第2轮-准确率测试 / 第3轮-稳定性测试"
    )

    st.divider()
    st.subheader("💰 Token预算控制")

    logs_df = load_logs()

    if not logs_df.empty:
        used_tokens = logs_df["total_tokens"].sum()
        remaining_tokens = TOKEN_LIMIT - used_tokens
        usage_rate = used_tokens / TOKEN_LIMIT

        st.metric("累计 Token", int(used_tokens))
        st.metric("剩余 Token 预算", int(remaining_tokens))
        st.progress(min(usage_rate, 1.0))

        if used_tokens >= TOKEN_LIMIT:
            st.error("Token 已超过 10 万预算，建议暂停测试。")
        elif used_tokens >= TOKEN_LIMIT * 0.8:
            st.warning("Token 已使用超过 80%，请控制测试规模。")
    else:
        st.info("暂无 Token 消耗记录")


tab1, tab2, tab3 = st.tabs(["📄 上传PDF识别", "📩 邮箱自动读取", "📊 测试统计"])


with tab1:
    st.subheader("📄 上传PDF发票识别")

    uploaded_files = st.file_uploader(
        "上传一个或多个 PDF 发票",
        type=["pdf"],
        accept_multiple_files=True
    )

    debug_mode_upload = st.checkbox("显示上传PDF调试信息", value=False)

    if st.button("🚀 开始识别上传的PDF"):
        if not uploaded_files:
            st.warning("请先上传 PDF 发票")
            st.stop()

        all_results = []
        total_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }

        for uploaded_file in uploaded_files:
            with st.spinner(f"正在识别：{uploaded_file.name}"):
                raw_text = extract_pdf_text_from_file(uploaded_file)

                results, usage, duration = recognize_text_to_results(
                    raw_text,
                    source="手动上传",
                    file_name=uploaded_file.name,
                    debug=debug_mode_upload
                )

                all_results.extend(results)
                total_usage = add_usage(total_usage, usage)

                if enable_test_log:
                    log_results(test_round, results, usage, duration)

        show_results(all_results, total_usage)


with tab2:
    st.subheader("📩 邮箱自动读取PDF发票")

    st.info("请填写邮箱授权码，不是邮箱登录密码。需要先在邮箱设置中开启 IMAP/SMTP 服务。")

    provider = st.selectbox(
        "邮箱类型",
        ["QQ邮箱", "163邮箱", "126邮箱"]
    )

    email_account = st.text_input(
        "邮箱账号",
        placeholder="例如：123456@qq.com / xxx@163.com / xxx@126.com"
    )

    auth_code = st.text_input(
        "邮箱授权码",
        type="password",
        placeholder="请输入邮箱授权码，不是登录密码"
    )

    days = st.selectbox(
        "搜索最近多少天的发票",
        [7, 30, 90],
        index=1
    )

    max_files = st.number_input(
        "最多识别PDF附件数量",
        min_value=1,
        max_value=100,
        value=20
    )

    debug_mode_email = st.checkbox("显示邮箱PDF调试信息", value=False)

    if st.button("📩 连接邮箱并读取发票"):
        if not email_account or not auth_code:
            st.warning("请填写邮箱账号和授权码")
            st.stop()

        mail = None

        try:
            with st.spinner("正在连接邮箱..."):
                mail = connect_email(provider, email_account, auth_code)

            st.success("邮箱连接成功")

            with st.spinner("正在搜索发票邮件..."):
                message_ids = search_invoice_emails(
                    mail,
                    days=days,
                    max_results=max_files
                )

            st.write(f"找到 {len(message_ids)} 封可能包含发票的邮件")

            if not message_ids:
                st.warning("没有找到发票相关邮件")
                st.stop()

            with st.spinner("正在下载 PDF 附件..."):
                attachments = download_pdf_attachments(
                    mail,
                    message_ids,
                    save_dir="downloads"
                )

            attachments = attachments[:max_files]

            st.write(f"下载到 {len(attachments)} 个 PDF 附件")

            if not attachments:
                st.warning("没有找到 PDF 附件")
                st.stop()

            all_results = []
            total_usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }

            for attachment in attachments:
                file_path = attachment["file_path"]
                file_name = attachment["file_name"]

                with st.spinner(f"正在识别：{file_name}"):
                    raw_text = extract_pdf_text_from_path(file_path)

                    results, usage, duration = recognize_text_to_results(
                        raw_text,
                        source=f"邮箱：{provider}",
                        file_name=file_name,
                        debug=debug_mode_email
                    )

                    all_results.extend(results)
                    total_usage = add_usage(total_usage, usage)

                    if enable_test_log:
                        log_results(test_round, results, usage, duration)

            show_results(all_results, total_usage)

        except imaplib.IMAP4.error:
            st.error("邮箱登录失败。请检查邮箱账号、授权码，以及是否已开启 IMAP 服务。")

        except Exception as e:
            st.error(f"邮箱读取失败：{e}")

        finally:
            if mail:
                close_email(mail)


with tab3:
    show_test_dashboard()
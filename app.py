import imaplib
import time
import textwrap
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
def html(content):
    st.markdown(textwrap.dedent(content), unsafe_allow_html=True)

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



# =========================
# 产品级官网 + 功能体验页面（视觉版修复）
# =========================

import textwrap


def html(content: str):
    """稳定渲染 HTML，避免缩进导致 HTML 被 Streamlit 当成代码块显示。"""
    st.markdown(textwrap.dedent(content).strip(), unsafe_allow_html=True)


html("""
<style>
.stApp {
    background: #f7f2ec;
}

.block-container {
    max-width: 1200px;
    padding-top: 0.5rem;
    padding-bottom: 5rem;
}

header[data-testid="stHeader"] {
    background: transparent;
}

/* 顶部导航 */
.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 18px 0 20px 0;
}

.logo-wrap {
    display: flex;
    align-items: center;
    gap: 14px;
}

.logo-icon {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    background: linear-gradient(135deg, #6fa4cc, #9b8cc8);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 12px 28px rgba(111, 164, 204, 0.35);
    font-size: 22px;
}

.logo-text {
    font-size: 22px;
    font-weight: 850;
    color: #2b3b4e;
}

/* 首页 */
.hero-section {
    min-height: 620px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    overflow: hidden;
    text-align: center;
}

.hero-badge {
    width: fit-content;
    margin: 0 auto;
    padding: 9px 22px;
    border-radius: 999px;
    background: #e8eef3;
    color: #5b91bd;
    font-weight: 750;
    border: 1px solid #cfdbe6;
    position: relative;
    z-index: 2;
}

.hero-title {
    font-size: 72px;
    font-weight: 950;
    color: #2b3b4e;
    margin-top: 34px;
    margin-bottom: 22px;
    letter-spacing: -2px;
    position: relative;
    z-index: 2;
}

.hero-subtitle {
    font-size: 26px;
    color: #6f879f;
    line-height: 1.8;
    position: relative;
    z-index: 2;
}

.hero-points {
    color: #6f879f;
    margin-top: 38px;
    font-size: 17px;
    position: relative;
    z-index: 2;
}

/* 装饰圆 */
.circle-blue {
    position: absolute;
    width: 210px;
    height: 210px;
    border-radius: 50%;
    background: rgba(120, 166, 195, 0.20);
    left: 10px;
    top: 70px;
}

.circle-purple {
    position: absolute;
    width: 150px;
    height: 150px;
    border-radius: 50%;
    background: rgba(158, 143, 201, 0.15);
    left: 48%;
    top: 250px;
}

.circle-green {
    position: absolute;
    width: 130px;
    height: 130px;
    border-radius: 50%;
    background: rgba(134, 173, 142, 0.18);
    right: 80px;
    top: 270px;
}

.circle-pink {
    position: absolute;
    width: 115px;
    height: 115px;
    border-radius: 50%;
    background: rgba(196, 138, 145, 0.13);
    right: 5px;
    bottom: 30px;
}

/* 功能卡片 */
.feature-card {
    background: #ffffff;
    border-radius: 26px;
    padding: 32px;
    min-height: 190px;
    border: 1px solid #eee7dd;
    box-shadow: 0 18px 45px rgba(69, 88, 110, 0.08);
    transition: 0.25s ease;
}

.feature-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 28px 70px rgba(69, 88, 110, 0.16);
}

.feature-icon {
    width: 58px;
    height: 58px;
    border-radius: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    margin-bottom: 22px;
    color: white;
}

.icon-blue { background: linear-gradient(135deg, #5c97bf, #9b8cc8); }
.icon-purple { background: linear-gradient(135deg, #9b8cc8, #7c6db5); }
.icon-green { background: linear-gradient(135deg, #6fa47f, #8ebc9c); }
.icon-red { background: linear-gradient(135deg, #c88a91, #b56f78); }

.feature-title {
    font-size: 23px;
    font-weight: 850;
    color: #2b3b4e;
    margin-bottom: 12px;
}

.feature-desc {
    color: #6f879f;
    font-size: 16px;
    line-height: 1.8;
}

.step-title {
    text-align: center;
    font-size: 38px;
    font-weight: 900;
    color: #2b3b4e;
    margin-top: 90px;
}

.step-sub {
    text-align: center;
    color: #6f879f;
    font-size: 18px;
    margin-bottom: 46px;
}

/* 页面标题 */
.page-title {
    text-align: center;
    font-size: 42px;
    font-weight: 900;
    color: #2b3b4e;
    margin-top: 32px;
}

.page-sub {
    text-align: center;
    color: #6f879f;
    font-size: 18px;
    margin-bottom: 46px;
}

/* 选择方式页 */
.choose-card {
    background: white;
    border-radius: 28px;
    padding: 48px;
    border: 1px solid #e8e0d8;
    box-shadow: 0 18px 45px rgba(69, 88, 110, 0.08);
    min-height: 380px;
    text-align: center;
    transition: 0.25s ease;
}

.choose-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 32px 80px rgba(69, 88, 110, 0.18);
    border-color: #9b8cc8;
}

/* 选择卡片按钮：视觉上与卡片融为一体 */
.choose-button-wrap button {
    margin-top: -62px;
    border-radius: 0 0 28px 28px !important;
    min-height: 58px !important;
}

/* 安全提示 */
.security-box {
    background: #f7f4fa;
    border: 1px solid #ebe5f3;
    border-radius: 18px;
    padding: 20px;
    margin: 24px 0;
    color: #6f879f;
}

/* 普通按钮 */
div.stButton > button {
    border-radius: 18px;
    border: 1px solid #d8e3ec;
    background: linear-gradient(135deg, #6fa4cc, #9b8cc8);
    color: white;
    font-weight: 850;
    min-height: 48px;
    transition: 0.25s ease;
}

div.stButton > button:hover {
    border: 1px solid #7c6db5;
    color: white;
    transform: translateY(-3px);
    box-shadow: 0 14px 32px rgba(111, 164, 204, 0.35);
    filter: brightness(1.05);
}

/* 返回按钮 */
.back-button button {
    width: fit-content !important;
    padding-left: 22px;
    padding-right: 22px;
}

/* 输入控件宽度更舒服 */
.stTextInput, .stSelectbox, .stNumberInput, .stFileUploader {
    max-width: 900px;
    margin-left: auto;
    margin-right: auto;
}
</style>
""")

if "page" not in st.session_state:
    st.session_state.page = "home"


def go_home():
    st.session_state.page = "home"


def go_choose():
    st.session_state.page = "choose"


def go_pdf():
    st.session_state.page = "pdf"


def go_email():
    st.session_state.page = "email"


# =========================
# 首页
# =========================

if st.session_state.page == "home":
    html("""
    <div class="topbar">
        <div class="logo-wrap">
            <div class="logo-icon">📄</div>
            <div class="logo-text">发票报销助手</div>
        </div>
        <div style="color:#6f879f;">AI Invoice Agent</div>
    </div>
    """)

    st.markdown(
    """
    <div class="hero-badge">● AI 驱动 · 智能报销</div>
    <div class="hero-title">AI发票报销助手</div>
    <div class="hero-subtitle">
    自动识别发票邮件、提取发票信息<br>
    并生成报销表，让报销从此不再繁琐
    </div>
    <div class="hero-points">
    ✅ 数据安全加密&nbsp;&nbsp;&nbsp;&nbsp;
    ✅ 识别准确率95%+&nbsp;&nbsp;&nbsp;&nbsp;
    ✅ 自动生成报销表
    </div>
        """,
        unsafe_allow_html=True
    )

    center1, center2, center3 = st.columns([1, 1, 1])
    with center2:
        if st.button("立即体验  →", use_container_width=True):
            go_choose()
            st.rerun()

    st.markdown("<br><br><br>", unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns(4)

    with f1:
        html("""
        <div class="feature-card">
            <div class="feature-icon icon-blue">🧠</div>
            <div class="feature-title">AI智能识别</div>
            <div class="feature-desc">自动识别发票内容，提取关键信息。</div>
        </div>
        """)

    with f2:
        html("""
        <div class="feature-card">
            <div class="feature-icon icon-purple">📄</div>
            <div class="feature-title">PDF发票解析</div>
            <div class="feature-desc">上传PDF发票，精准提取报销数据。</div>
        </div>
        """)

    with f3:
        html("""
        <div class="feature-card">
            <div class="feature-icon icon-green">📧</div>
            <div class="feature-title">邮箱自动识别</div>
            <div class="feature-desc">授权邮箱，自动获取发票信息。</div>
        </div>
        """)

    with f4:
        html("""
        <div class="feature-card">
            <div class="feature-icon icon-red">📊</div>
            <div class="feature-title">一键生成报表</div>
            <div class="feature-desc">自动整理并生成报销表格文档。</div>
        </div>
        """)

    html('<div class="step-title">简单三步，轻松报销</div>')
    html('<div class="step-sub">从上传到生成报表，只需几分钟</div>')

    s1, s2, s3 = st.columns(3)

    with s1:
        html("""
        <div style="text-align:center;">
            <h2 style="color:#5c97bf;">01</h2>
            <h3>上传或授权</h3>
            <p style="color:#6f879f;">上传发票PDF或授权邮箱</p>
        </div>
        """)

    with s2:
        html("""
        <div style="text-align:center;">
            <h2 style="color:#9b8cc8;">02</h2>
            <h3>AI识别</h3>
            <p style="color:#6f879f;">自动提取发票关键信息</p>
        </div>
        """)

    with s3:
        html("""
        <div style="text-align:center;">
            <h2 style="color:#6fa47f;">03</h2>
            <h3>生成报表</h3>
            <p style="color:#6f879f;">一键导出报销表格文档</p>
        </div>
        """)


# =========================
# 选择识别方式
# =========================

elif st.session_state.page == "choose":
    html('<div class="back-button">')
    if st.button("‹ 返回首页", key="back_from_choose"):
        go_home()
        st.rerun()
    html('</div>')

    html("""
    <div class="topbar" style="justify-content:center;">
        <div class="logo-wrap">
            <div class="logo-icon">📄</div>
            <div class="logo-text">AI发票报销助手</div>
        </div>
    </div>
    """)

    html('<div class="page-title">选择识别方式</div>')
    html('<div class="page-sub">选择适合您的方式来识别发票信息</div>')

    c1, c2 = st.columns(2, gap="large")

    with c1:
        html("""
        <div class="choose-card">
            <div style="font-size:54px;margin-bottom:18px;">☁️</div>
            <h2 style="color:#2b3b4e;font-size:34px;">上传发票PDF</h2>
            <p style="color:#6f879f;font-size:17px;">上传PDF格式的发票文件，AI自动识别发票内容</p>
            <ul style="color:#6f879f;line-height:2.1;text-align:left;margin-top:28px;font-size:16px;">
                <li>支持批量上传多个PDF</li>
                <li>精准识别发票关键信息</li>
                <li>一键导出报销表格</li>
            </ul>
        </div>
        """)
        html('<div class="choose-button-wrap">')
        if st.button("上传发票PDF", use_container_width=True, key="choose_pdf_card"):
            go_pdf()
            st.rerun()
        html('</div>')

    with c2:
        html("""
        <div class="choose-card">
            <div style="font-size:54px;margin-bottom:18px;">✉️</div>
            <h2 style="color:#2b3b4e;font-size:34px;">授权邮箱自动识别</h2>
            <p style="color:#6f879f;font-size:17px;">授权邮箱后，自动识别邮件中的发票信息</p>
            <ul style="color:#6f879f;line-height:2.1;text-align:left;margin-top:28px;font-size:16px;">
                <li>自动扫描邮箱中的发票</li>
                <li>安全授权，保护隐私</li>
                <li>无需手动下载附件</li>
            </ul>
        </div>
        """)
        html('<div class="choose-button-wrap">')
        if st.button("授权邮箱自动识别", use_container_width=True, key="choose_email_card"):
            go_email()
            st.rerun()
        html('</div>')


# =========================
# PDF 上传识别页
# =========================

elif st.session_state.page == "pdf":
    html('<div class="back-button">')
    if st.button("‹ 返回首页", key="back_from_pdf"):
        go_home()
        st.rerun()
    html('</div>')

    html("""
    <div class="topbar" style="justify-content:center;">
        <div class="logo-wrap">
            <div class="logo-icon">📄</div>
            <div class="logo-text">AI发票报销助手</div>
        </div>
    </div>
    """)

    html('<div class="page-title">上传发票PDF</div>')
    html('<div class="page-sub">拖拽或点击上传PDF格式的发票文件</div>')

    uploaded_files = st.file_uploader(
        "拖拽PDF文件到此处，或点击选择文件，支持批量上传",
        type=["pdf"],
        accept_multiple_files=True
    )

    if st.button("开始AI识别  ⚡", use_container_width=True):
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
                    debug=False
                )

                all_results.extend(results)
                total_usage = add_usage(total_usage, usage)

        show_results(all_results, total_usage)


# =========================
# 邮箱自动识别页
# =========================

elif st.session_state.page == "email":
    html('<div class="back-button">')
    if st.button("‹ 返回首页", key="back_from_email"):
        go_home()
        st.rerun()
    html('</div>')

    html("""
    <div class="topbar" style="justify-content:center;">
        <div class="logo-wrap">
            <div class="logo-icon">📄</div>
            <div class="logo-text">AI发票报销助手</div>
        </div>
    </div>
    """)

    html('<div class="page-title">授权邮箱自动识别</div>')
    html('<div class="page-sub">输入邮箱号和授权码，自动识别发票邮件</div>')

    provider = st.selectbox(
        "邮箱类型",
        ["QQ邮箱", "163邮箱", "126邮箱"]
    )

    email_account = st.text_input(
        "邮箱地址",
        placeholder="请输入您的邮箱地址"
    )

    auth_code = st.text_input(
        "授权码",
        type="password",
        placeholder="请输入邮箱授权码"
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

    html("""
    <div class="security-box">
        🛡️ <b>安全保障</b><br>
        您的授权信息仅用于识别发票邮件，不会泄露给第三方。
    </div>
    """)

    if st.button("授权并开始识别  ⚡", use_container_width=True):
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
                        debug=False
                    )

                    all_results.extend(results)
                    total_usage = add_usage(total_usage, usage)

            show_results(all_results, total_usage)

        except imaplib.IMAP4.error:
            st.error("邮箱登录失败，请检查账号、授权码，以及是否开启 IMAP 服务。")

        except Exception as e:
            st.error(f"邮箱读取失败：{e}")

        finally:
            if mail:
                close_email(mail)


# =========================
# 管理员入口
# =========================

st.markdown("---")

with st.expander("管理员入口"):
    admin_password = st.text_input("请输入管理员密码", type="password")

    if admin_password == "admin123":
        st.success("管理员验证成功")
        show_test_dashboard()

    elif admin_password:
        st.error("管理员密码错误")

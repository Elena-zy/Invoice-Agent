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

# =========================
# 产品级官网 + 功能体验页面
# =========================

st.markdown("""
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

.badge {
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

.main-title {
    font-size: 72px;
    font-weight: 950;
    color: #2b3b4e;
    margin-top: 34px;
    margin-bottom: 22px;
    letter-spacing: -2px;
    position: relative;
    z-index: 2;
}

.sub-title {
    font-size: 26px;
    color: #6f879f;
    line-height: 1.8;
    position: relative;
    z-index: 2;
}

.footer-points {
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

/* 把 Streamlit 按钮做成覆盖卡片的大按钮 */
.choose-btn button {
    margin-top: -380px;
    height: 380px;
    opacity: 0;
}

.choose-btn button:hover {
    opacity: 0.04;
}

/* 表单页 */
.form-card {
    max-width: 760px;
    margin: 0 auto;
    background: white;
    border-radius: 26px;
    padding: 42px;
    border: 1px solid #dbe5ee;
    box-shadow: 0 18px 45px rgba(69, 88, 110, 0.08);
}

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
</style>
""", unsafe_allow_html=True)


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
    st.markdown("""
    <style>
    .hero-box {
        min-height: 620px;
        text-align: center;
        padding-top: 120px;
        position: relative;
    }

    .hero-badge {
        display: inline-block;
        padding: 10px 22px;
        border-radius: 999px;
        background: #e8eef3;
        color: #5b91bd;
        font-weight: 700;
        border: 1px solid #cfdbe6;
    }

    .hero-title {
        font-size: 72px;
        font-weight: 900;
        color: #2b3b4e;
        margin-top: 36px;
        margin-bottom: 24px;
    }

    .hero-subtitle {
        font-size: 26px;
        color: #6f879f;
        line-height: 1.8;
    }

    .hero-points {
        margin-top: 40px;
        color: #6f879f;
        font-size: 17px;
    }

    .decor-circle-1 {
        position: absolute;
        width: 210px;
        height: 210px;
        border-radius: 50%;
        background: rgba(120,166,195,0.20);
        left: 0;
        top: 100px;
    }

    .decor-circle-2 {
        position: absolute;
        width: 150px;
        height: 150px;
        border-radius: 50%;
        background: rgba(158,143,201,0.15);
        left: 48%;
        top: 270px;
    }

    .decor-circle-3 {
        position: absolute;
        width: 130px;
        height: 130px;
        border-radius: 50%;
        background: rgba(134,173,142,0.18);
        right: 80px;
        top: 290px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="topbar">
        <div class="logo-wrap">
            <div class="logo-icon">📄</div>
            <div class="logo-text">发票报销助手</div>
        </div>
        <div style="color:#6f879f;">AI Invoice Agent</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hero-box">
        <div class="decor-circle-1"></div>
        <div class="decor-circle-2"></div>
        <div class="decor-circle-3"></div>

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
    </div>
    """, unsafe_allow_html=True)

    center1, center2, center3 = st.columns([1, 1, 1])
    with center2:
        if st.button("立即体验  →", use_container_width=True):
            go_choose()
            st.rerun()

    st.markdown("<br><br><br>", unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns(4)

    with f1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon icon-blue">🧠</div>
            <div class="feature-title">AI智能识别</div>
            <div class="feature-desc">自动识别发票内容，提取关键信息。</div>
        </div>
        """, unsafe_allow_html=True)

    with f2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon icon-purple">📄</div>
            <div class="feature-title">PDF发票解析</div>
            <div class="feature-desc">上传PDF发票，精准提取报销数据。</div>
        </div>
        """, unsafe_allow_html=True)

    with f3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon icon-green">📧</div>
            <div class="feature-title">邮箱自动识别</div>
            <div class="feature-desc">授权邮箱，自动获取发票信息。</div>
        </div>
        """, unsafe_allow_html=True)

    with f4:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon icon-red">📊</div>
            <div class="feature-title">一键生成报表</div>
            <div class="feature-desc">自动整理并生成报销表格文档。</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="step-title">简单三步，轻松报销</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-sub">从上传到生成报表，只需几分钟</div>', unsafe_allow_html=True)

    s1, s2, s3 = st.columns(3)

    with s1:
        st.markdown("""
        <div style="text-align:center;">
            <h2 style="color:#5c97bf;">01</h2>
            <h3>上传或授权</h3>
            <p style="color:#6f879f;">上传发票PDF或授权邮箱</p>
        </div>
        """, unsafe_allow_html=True)

    with s2:
        st.markdown("""
        <div style="text-align:center;">
            <h2 style="color:#9b8cc8;">02</h2>
            <h3>AI识别</h3>
            <p style="color:#6f879f;">自动提取发票关键信息</p>
        </div>
        """, unsafe_allow_html=True)

    with s3:
        st.markdown("""
        <div style="text-align:center;">
            <h2 style="color:#6fa47f;">03</h2>
            <h3>生成报表</h3>
            <p style="color:#6f879f;">一键导出报销表格文档</p>
        </div>
        """, unsafe_allow_html=True)
   
# =========================
# 选择识别方式
# =========================

elif st.session_state.page == "choose":
    st.markdown('<div class="back-button">', unsafe_allow_html=True)
    if st.button("‹ 返回首页"):
        go_home()
        st.rerun()


    st.markdown("""
    <div class="topbar" style="justify-content:center;">
        <div class="logo-wrap">
            <div class="logo-icon">📄</div>
            <div class="logo-text">AI发票报销助手</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-title">选择识别方式</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">选择适合您的方式来识别发票信息</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("""
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
        """, unsafe_allow_html=True)

        st.markdown('<div class="choose-btn">', unsafe_allow_html=True)
        if st.button("上传发票PDF", use_container_width=True, key="choose_pdf_card"):
            go_pdf()
            st.rerun()
  

    with c2:
        st.markdown("""
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
        """, unsafe_allow_html=True)

        st.markdown('<div class="choose-btn">', unsafe_allow_html=True)
        if st.button("授权邮箱自动识别", use_container_width=True, key="choose_email_card"):
            go_email()
            st.rerun()



# =========================
# PDF 上传识别页
# =========================

elif st.session_state.page == "pdf":
    st.markdown('<div class="back-button">', unsafe_allow_html=True)
    if st.button("‹ 返回首页"):
        go_home()
        st.rerun()


    st.markdown("""
    <div class="topbar" style="justify-content:center;">
        <div class="logo-wrap">
            <div class="logo-icon">📄</div>
            <div class="logo-text">AI发票报销助手</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-title">上传发票PDF</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">拖拽或点击上传PDF格式的发票文件</div>', unsafe_allow_html=True)

   

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
    st.markdown('<div class="back-button">', unsafe_allow_html=True)
    if st.button("‹ 返回首页"):
        go_home()
        st.rerun()
   

    st.markdown("""
    <div class="topbar" style="justify-content:center;">
        <div class="logo-wrap">
            <div class="logo-icon">📄</div>
            <div class="logo-text">AI发票报销助手</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-title">授权邮箱自动识别</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">输入邮箱号和授权码，自动识别发票邮件</div>', unsafe_allow_html=True)

  

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

    st.markdown("""
    <div class="security-box">
        🛡️ <b>安全保障</b><br>
        您的授权信息仅用于识别发票邮件，不会泄露给第三方。
    </div>
    """, unsafe_allow_html=True)

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
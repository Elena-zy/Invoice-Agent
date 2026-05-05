# AI发票报销助手（Invoice Agent）

AI发票报销助手是一个基于大模型的智能发票识别与报销整理工具，支持 PDF 发票上传识别、邮箱自动读取发票附件、结构化信息提取、Excel 报销表导出。本项目适用于个人报销整理、小团队财务归档等场景。

---

## 功能特点

### 1. PDF 发票识别
- 支持上传单个或多个 PDF 发票
- 自动提取发票号码、金额、日期、销售方、发票类型等字段

### 2. 邮箱自动读取发票
- 支持 QQ 邮箱、163 邮箱、126 邮箱
- 通过 IMAP 授权码读取邮箱
- 自动搜索发票相关邮件
- 自动下载 PDF 附件并进入识别流程

### 3. 大模型结构化识别
- 支持通义千问
- 可扩展 Dify / Ollama 等模型调用方式

### 4. Excel 报销表导出
- 支持一键下载 Excel 文件

---

## 安装步骤

1. 确保已安装 Python 3.8 或更高版本  
2. 克隆或下载本项目代码  
3. 安装依赖：

```bash
git clone https://github.com/Elena-zy/Invoice-Agent.git
cd invoice_agent
uv sync
```

## 命令行模式

直接运行主程序：

```bash
uv run app.py
```

## 邮箱授权说明

本项目读取邮箱时使用的是邮箱授权码，不是邮箱登录密码。

使用前需要：  
1.登录 QQ / 163 / 126 邮箱网页版  
2.开启 IMAP / SMTP 服务  
3.生成授权码  
4.在页面中填写邮箱账号和授权码  

## 配置说明

请在项目根目录创建 .env 文件：

```bash
# 模型选择：qwen / dify / ollama
LLM_PROVIDER=qwen

# 通义千问 API Key
QWEN_API_KEY=你的通义千问API_KEY

# Dify，可选
DIFY_API_URL=
DIFY_API_KEY=

# Ollama，可选
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

## 目录结构

```bash
invoice_agent

├── app.py                         # Streamlit 主程序   
├── .gitignore                     # Git 忽略文件配置
├── .python-version                # 指定 Python 版本
├── LICENSE                        # 开源协议
├── README.md                      # 项目说明文档
├── uv.lock                        # uv 依赖锁文件
├── pyproject。toml         
│  
├── invoice_agent- website/        # 前端页面文件  
│   ├── index.html                 # 前端页面结构  
│   ├── style.css                  # 前端样式  
│   └── admin.html                 # 前端交互逻辑  
│
├── services/                      # 核心服务模块  
│   ├── email_service.py           # 邮箱读取与附件下载  
│   ├── pdf_service.py             # PDF文本提取与清洗  
│   ├── llm_service.py             # 大模型统一调用入口  
│   ├── qwen_service.py            # 通义千问调用，可选  
│   ├── dify_service.py            # Dify调用，可选  
│   └── ollama_service.py          # Ollama调用，可选  
│  
├── utils/                         # 工具模块  
│   ├── parser.py                  # JSON解析  
│   ├── validator.py               # 字段校验  
│   ├── excel_exporter.py          # Excel导出  
│   ├── logger.py                  # 测试日志记录  
```

# Discord 多账号自动化系统 🤖

> 多账号管理 · 关键词AI回复 · 时间段随机定时发言 · Web UI 管理

---

## 📋 功能

| 功能 | 说明 |
|------|------|
| 👥 **多账号管理** | 同时管理 20+ 个 Discord 账号，Web UI 一键启停 |
| 🎯 **关键词触发 AI 回复** | OR 逻辑匹配关键词 → DeepSeek 自动回复 |
| ⏰ **定时发言** | 设置时间段（如 06:00-12:00），随机时间自动发送 |
| 📝 **多种消息模式** | 顺序轮换 / 随机选取 / AI 生成 / 混合模式 |
| 📊 **Web 管理面板** | 深色主题，账号/频道/关键词/定时任务/日志管理 |
| 📜 **日志系统** | 发言和 AI 回复日志，自动保留 1 年，支持手动清除 |

---

## 🚀 快速开始

### 前置条件

- Python 3.10+
- pip
- DeepSeek API Key（[获取](https://platform.deepseek.com/api_keys)）
- Discord 账号 Token

### 安装

```bash
# 1. 克隆项目
git clone https://github.com/kkk2791/discord-auto.git
cd discord-auto

# 2. 创建虚拟环境并安装依赖
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 .\venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 DeepSeek API Key
nano .env
```

### 启动

```bash
source venv/bin/activate
python run.py
```

打开浏览器访问 **http://localhost:8000**

---

## 🎮 使用教程

### 第一步：添加 Discord 账号

1. 打开 http://localhost:8000 → **账号管理**
2. 点 **添加账号**，填入名称和 Token
3. 保存后自动连接，显示 🟢 在线

> ⚠️ 建议用小号操作！使用个人 Token 违反 Discord 服务条款，有封号风险。

**获取 Token 方法：**
1. 打开 Discord（[网页版](https://discord.com/app) 或客户端）
2. 按 `F12` 打开开发者工具
3. 进入 **Application → Local Storage → `https://discord.com`**
4. 找到 `token` 字段，复制其值

### 第二步：配置频道

进入 **定时任务** 页面 → 选择账号：

| 操作 | 说明 |
|------|------|
| 添加频道 | 填写名称、频道 ID |
| 监听回复 | ✅ 此频道消息会检查关键词触发 AI 回复 |
| 定时发言 | ✅ 此频道用于定时自动发消息 |

> **获取频道 ID：** Discord → 用户设置 → 高级 → 开启开发者模式 → 右键频道 → 复制 ID

### 第三步：设置关键词（AI 自动回复）

- **OR 逻辑**：消息包含任意关键词即触发
- 可绑定特定频道，或留空全局生效

### 第四步：设置定时发言

| 配置项 | 说明 |
|--------|------|
| 时间段 | 如 `06:00-12:00`，系统在此时段内随机时间发送 |
| 消息模式 | 📝 顺序 / 🎲 随机 / 🤖 AI / 🔄 混合 |
| 条数/每次 | 一个时段内发几条（时段等分，每条各自时段发） |
| 跨天支持 | 如 `22:00-06:00` 跨夜时段 |

#### 消息模式说明

| 模式 | 图标 | 说明 |
|------|------|------|
| 顺序 | 📝 | 按添加顺序轮流发送预设消息 |
| 随机 | 🎲 | 每次从预设消息中随机选一条 |
| AI 生成 | 🤖 | DeepSeek 每次自动生成内容 |
| 混合 | 🔄 | 轮流使用预设消息和 AI 生成 |

---

## 🌐 Web UI 页面

| 页面 | 路径 | 功能 |
|------|------|------|
| 📊 仪表盘 | `/` | 账号状态、统计概览 |
| 👤 账号管理 | `/accounts` | 添加/删除/连接/编辑账号 |
| ⏰ 定时任务 | `/schedules` | 频道、关键词、定时任务管理 |
| 📝 日志 | `/logs` | 发言记录和 AI 回复记录 |

---

## ⚙️ 配置文件

### .env

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | `***`（必填） |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型 | `deepseek-chat` |
| `APP_HOST` | 监听地址 | `0.0.0.0` |
| `APP_PORT` | 端口 | `8000` |
| `SCHEDULER_TIMEZONE` | 时区 | `Asia/Shanghai` |

---

## 🗂️ 项目结构

```
discord-auto/
├── run.py                  # 启动入口
├── requirements.txt        # Python 依赖
├── .env                    # 环境变量（不提交到 Git）
├── .env.example            # 环境变量示例
├── start.sh                # 一键启动脚本
├── app/
│   ├── main.py             # FastAPI 主入口
│   ├── config.py           # 配置管理
│   ├── database.py         # SQLite 数据库
│   ├── models/             # 数据模型
│   │   ├── account.py      # 账号
│   │   ├── channel.py      # 频道配置
│   │   ├── keyword.py      # 触发关键词
│   │   ├── schedule.py     # 定时发言任务
│   │   ├── message.py      # 预设消息
│   │   └── log.py          # 日志
│   ├── services/           # 核心服务
│   │   ├── discord_client.py # Discord 连接管理
│   │   ├── deepseek.py     # AI 接口
│   │   ├── scheduler.py    # 定时调度器
│   │   └── message_handler.py # 消息处理
│   └── routers/            # API 路由
├── templates/              # Web UI 模板
└── static/                 # 静态资源（CSS）
```

---

## 🔒 安全说明

- API Key 和 Token 通过 `.env` 和数据库管理，**不提交到 Git**
- `data/`、`venv/`、`logs/` 等均已加入 `.gitignore`
- 建议使用测试账号操作，不要使用主号

---

## ⚠️ 免责声明

- 使用个人 Discord 账号 Token 进行自动化操作违反 Discord 服务条款
- 本工具仅供学习和研究使用，使用者需自行承担风险
- 作者不对因使用本工具导致的账号封禁或其他损失负责

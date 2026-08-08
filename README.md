# 阀门工程知识库 V1.1

本地可运行的阀门工程参数知识库，技术栈：**Vue 3 + Vite + Element Plus + FastAPI + SQLAlchemy + SQLite**。

V1.1 已打通完整使用闭环：

**用户登录 → 知识库总览 → Excel 上传 → Sheet / 表头识别 → 字段映射 → 预览校验 → SQLite 入库 → 自动生成参数页面 → 查询 / 筛选 / 编辑 / 导出 → 退出登录**。

## 已实现

### 登录与账号

- 登录页
- Bearer Session 登录鉴权
- 密码使用 PBKDF2-SHA256 + 随机 Salt 保存，不明文落库
- 7 天登录会话
- 获取当前用户
- 修改密码
- 修改密码后注销其他登录会话
- 主界面右上角退出登录
- 未登录访问 API / 页面自动返回登录页

首次启动默认账号：

```text
用户名：admin
密码：Admin@123456
```

登录后建议右上角 **管理员 → 修改密码**。

也可以在首次启动前设置环境变量：

```text
VALVE_ADMIN_USERNAME
VALVE_ADMIN_PASSWORD
VALVE_ADMIN_DISPLAY_NAME
```

如果忘记密码，不需要删除数据库：

```bash
cd backend
python reset_admin_password.py --username admin --password NewPassword123!
```

### Excel 导入

- 支持 `.xlsx` / `.xls`
- 单文件最大 20MB
- 自动读取 Sheet
- 自动检测表头行
- 支持“第 1 行是表标题、第 2 行才是字段名”的工程 Excel
- 自动猜测字段编码
- 自动判断文本 / 数值字段
- 字段显示名、字段编码、类型、单位可人工调整
- 导入前预览
- 写入 SQLite
- 动态 JSON 字段，不同 Excel 可以拥有完全不同的列
- 导入完成后自动进入参数展示页面
- 支持搜索、动态筛选、排序、分页、编辑、删除、导出 Excel
- 导入历史记录

示例 Excel 在：

```text
samples/口径基础表示例.xlsx
samples/压力等级表示例.xlsx
```

## 目录

```text
famen/
├─ backend/
│  ├─ app/
│  │  ├─ auth.py             登录、密码、Session 鉴权
│  │  ├─ database.py         SQLite / SQLAlchemy
│  │  ├─ main.py             FastAPI 接口
│  │  ├─ models.py           数据模型
│  │  ├─ schemas.py          请求模型
│  │  ├─ seed.py             默认知识库 + admin 初始化
│  │  └─ services/
│  │     └─ excel_service.py Excel 智能识别
│  ├─ data/                  SQLite 数据库运行时生成
│  ├─ uploads/               上传文件运行时保存
│  ├─ requirements.txt
│  └─ reset_admin_password.py
├─ frontend/
│  ├─ src/
│  │  ├─ api/
│  │  ├─ components/
│  │  ├─ layouts/
│  │  ├─ router/
│  │  ├─ stores/
│  │  └─ views/
│  └─ package.json
├─ samples/
├─ start.bat
└─ start.sh
```

## Windows 一键启动

需要：

- Python 3.11+
- Node.js 20+

双击：

```text
start.bat
```

第一次会自动安装依赖。随后访问：

```text
Web：http://localhost:5173
API：http://127.0.0.1:8000/docs
```

## 手动启动

### 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

macOS / Linux：

```bash
source .venv/bin/activate
```

### 前端

另开终端：

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://localhost:5173
```

## SQLite

运行后自动创建：

```text
backend/data/valve_knowledge.db
```

程序使用 `SQLAlchemy`，以后需要改 PostgreSQL / MySQL 时，业务层可继续复用。

也可以通过环境变量指定 SQLite 文件位置：

```text
VALVE_DB_PATH=D:\data\valve_knowledge.db
```

## 数据模型

核心表：

```text
users
user_sessions
knowledge_bases
datasets
dataset_fields
dataset_records
import_jobs
```

工程参数采用：

```text
dataset
  ↓
dataset_field       定义 Excel 有哪些列
  ↓
dataset_record      JSON 保存每一行参数
```

因此：

```text
ASME B16.5 法兰尺寸.xlsx
球体参数.xlsx
阀杆参数.xlsx
材料参数.xlsx
企业公式.xlsx
```

即使列完全不同，也可以导入同一个系统，不需要每次改数据库表结构。

## 已验证的后端闭环

本版本已用 FastAPI TestClient 实际验证：

```text
未登录访问 → 401
默认账号登录 → 成功
获取当前用户 → 成功
知识库总览 → 成功
口径 Excel 上传 → 自动识别第 2 行表头
字段映射入库 → 成功
查询 DN300 → 成功返回
修改密码 → 成功
退出登录 → 原 Token 失效
新密码重新登录 → 成功
```

## 生产部署提醒

V1.1 定位为本地 / 内网小团队工程知识库。正式公网部署时建议再补：HTTPS、反向代理、备份策略、登录失败限流、操作审计和更完整的角色权限。

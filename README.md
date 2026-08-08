# 阀门工程知识库 V1

一个本地可运行的阀门工程参数知识库：Vue 3 + FastAPI + SQLite。

核心闭环：**Excel 上传 → 自动识别表头 → 字段映射 → 预览校验 → 写入 SQLite → 自动生成参数查询页面**。

## 已实现

- 知识库总览仪表盘
- 基础字典库 / 标准数字库 / 企业公式库 / 阀门参数库 / 材料标准库 / BOM规则库
- Excel `.xlsx` / `.xls` 上传
- 自动识别 Sheet、表头行、字段与数据类型
- 字段映射：显示名、字段编码、启用/停用
- 动态字段入库：`dataset + dataset_field + dataset_record(JSON)`
- 参数表格自动生成
- 任意字段搜索、动态筛选、排序、分页
- 单条数据编辑 / 删除
- 数据集导出 Excel
- 导入记录
- 首次启动自动创建 SQLite 数据库，并附带“口径基础表 / 压力等级表”演示数据

> 演示数据用于展示系统能力，正式工程数据请以你们确认过的标准/企业数据为准。

## 目录

```text
valve-knowledge-base/
├─ backend/                 FastAPI + SQLite
│  ├─ app/
│  ├─ data/                 SQLite 数据库自动生成在这里
│  └─ uploads/              上传的 Excel
├─ frontend/                Vue3 + Vite + Element Plus
├─ samples/                 测试 Excel
├─ start.bat                Windows 一键启动
└─ start.sh                 macOS/Linux 启动
```

## Windows 启动

推荐 Python 3.11+、Node.js 20+。

### 最省事

双击：

```text
start.bat
```

首次运行会安装 Python 与 npm 依赖，需要可以访问 pip/npm。npm 默认源失败时，`start.bat` 会自动尝试 npmmirror。

随后浏览器访问：

```text
http://localhost:5173
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

## 手工启动

### 1. 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

macOS / Linux 激活虚拟环境：

```bash
source .venv/bin/activate
```

### 2. 前端

打开另一个终端：

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。

## SQLite 数据库

首次启动后自动生成：

```text
backend/data/valve_knowledge.db
```

删除这个文件后重启后端，会重新生成一个干净数据库和演示基础字典。

## Excel 导入建议

系统支持 Excel 第一行是标题、第二行才是字段名，例如：

```text
第1行：口径基础表
第2行：公称口径 | NPS数值 | DN | 英寸显示 | 毫米参考 | 备注
第3行开始：数据
```

系统会自动尝试识别真正的表头行。

## 数据模型

稳定的知识库/数据集信息使用结构化表；工程参数使用动态字段 + JSON：

- `knowledge_bases`
- `datasets`
- `dataset_fields`
- `dataset_records`
- `import_jobs`

这种结构允许不同 Excel 拥有完全不同的列，而不需要反复修改数据库表结构。

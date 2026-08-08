from __future__ import annotations

import json
import shutil
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from .database import Base, SessionLocal, engine, get_db
from .models import Dataset, DatasetField, DatasetRecord, ImportJob, KnowledgeBase
from .schemas import (
    DatasetQuery,
    ImportCommitRequest,
    ImportPreviewRequest,
    KnowledgeBaseCreate,
    RecordUpdate,
)
from .seed import seed
from .services.excel_service import (
    frame_to_json_records,
    list_sheets,
    preview_payload,
    read_frame,
    detect_header_row,
)

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR = BASE_DIR / "data" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="阀门工程知识库 API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)


def dt(v):
    return v.strftime("%Y-%m-%d %H:%M:%S") if v else None


def kb_out(kb: KnowledgeBase, db: Session):
    datasets = db.scalars(select(Dataset).where(Dataset.knowledge_base_id == kb.id)).all()
    return {
        "id": kb.id,
        "name": kb.name,
        "code": kb.code,
        "type": kb.type,
        "description": kb.description,
        "accent": kb.accent,
        "enabled": kb.enabled,
        "dataset_count": len(datasets),
        "record_count": sum(d.record_count for d in datasets),
        "updated_at": dt(kb.updated_at),
    }


@app.get("/api/health")
def health():
    return {"ok": True, "service": "valve-knowledge-base"}


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    kbs = db.scalars(select(KnowledgeBase).order_by(KnowledgeBase.id)).all()
    kb_payload = [kb_out(kb, db) for kb in kbs]
    standard_ids = [k.id for k in kbs if k.type in {"standard", "dictionary", "material"}]
    formula_ids = [k.id for k in kbs if k.type == "formula"]
    standard_count = db.scalar(select(func.coalesce(func.sum(Dataset.record_count), 0)).where(Dataset.knowledge_base_id.in_(standard_ids))) if standard_ids else 0
    formula_count = db.scalar(select(func.coalesce(func.sum(Dataset.record_count), 0)).where(Dataset.knowledge_base_id.in_(formula_ids))) if formula_ids else 0
    today_str = date.today().isoformat()
    today_imported = 0
    jobs = db.scalars(select(ImportJob).order_by(ImportJob.created_at.desc()).limit(8)).all()
    for job in jobs:
        if job.created_at.date().isoformat() == today_str:
            today_imported += job.success_rows or 0
    recent = [
        {
            "id": j.id,
            "filename": j.filename,
            "status": j.status,
            "sheet_name": j.sheet_name,
            "total_rows": j.total_rows,
            "success_rows": j.success_rows,
            "failed_rows": j.failed_rows,
            "message": j.message,
            "created_at": dt(j.created_at),
        }
        for j in jobs
    ]
    return {
        "knowledge_base_count": len(kbs),
        "standard_record_count": int(standard_count or 0),
        "formula_record_count": int(formula_count or 0),
        "today_import_count": int(today_imported),
        "knowledge_bases": kb_payload,
        "recent_imports": recent,
    }


@app.get("/api/knowledge-bases")
def knowledge_bases(db: Session = Depends(get_db)):
    kbs = db.scalars(select(KnowledgeBase).order_by(KnowledgeBase.id)).all()
    return [kb_out(kb, db) for kb in kbs]


@app.post("/api/knowledge-bases")
def create_knowledge_base(body: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    if db.scalar(select(KnowledgeBase).where(or_(KnowledgeBase.name == body.name, KnowledgeBase.code == body.code))):
        raise HTTPException(409, "知识库名称或编码已存在")
    kb = KnowledgeBase(**body.model_dump())
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb_out(kb, db)


@app.get("/api/knowledge-bases/{kb_id}/datasets")
def knowledge_base_datasets(kb_id: int, db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    datasets = db.scalars(select(Dataset).where(Dataset.knowledge_base_id == kb_id).order_by(Dataset.updated_at.desc())).all()
    return {
        "knowledge_base": kb_out(kb, db),
        "datasets": [
            {
                "id": d.id,
                "name": d.name,
                "category": d.category,
                "standard_no": d.standard_no,
                "source_file_name": d.source_file_name,
                "sheet_name": d.sheet_name,
                "record_count": d.record_count,
                "field_count": d.field_count,
                "updated_at": dt(d.updated_at),
            }
            for d in datasets
        ],
    }


@app.get("/api/datasets")
def datasets(db: Session = Depends(get_db)):
    rows = db.scalars(select(Dataset).options(selectinload(Dataset.knowledge_base)).order_by(Dataset.updated_at.desc())).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "knowledge_base_id": d.knowledge_base_id,
            "knowledge_base_name": d.knowledge_base.name if d.knowledge_base else "",
            "category": d.category,
            "standard_no": d.standard_no,
            "record_count": d.record_count,
            "field_count": d.field_count,
            "updated_at": dt(d.updated_at),
        }
        for d in rows
    ]


@app.get("/api/datasets/{dataset_id}")
def dataset_detail(dataset_id: int, db: Session = Depends(get_db)):
    d = db.scalar(
        select(Dataset)
        .options(selectinload(Dataset.fields), selectinload(Dataset.knowledge_base))
        .where(Dataset.id == dataset_id)
    )
    if not d:
        raise HTTPException(404, "数据集不存在")
    return {
        "id": d.id,
        "name": d.name,
        "category": d.category,
        "standard_no": d.standard_no,
        "source_file_name": d.source_file_name,
        "sheet_name": d.sheet_name,
        "record_count": d.record_count,
        "field_count": d.field_count,
        "updated_at": dt(d.updated_at),
        "knowledge_base": {"id": d.knowledge_base.id, "name": d.knowledge_base.name, "code": d.knowledge_base.code},
        "fields": [
            {
                "id": f.id,
                "source_name": f.source_name,
                "field_code": f.field_code,
                "field_name": f.field_name,
                "data_type": f.data_type,
                "unit": f.unit,
                "searchable": f.searchable,
                "filterable": f.filterable,
            }
            for f in d.fields
        ],
    }


@app.post("/api/datasets/{dataset_id}/query")
def query_dataset(dataset_id: int, body: DatasetQuery, db: Session = Depends(get_db)):
    d = db.scalar(select(Dataset).options(selectinload(Dataset.fields)).where(Dataset.id == dataset_id))
    if not d:
        raise HTTPException(404, "数据集不存在")
    stmt = select(DatasetRecord).where(DatasetRecord.dataset_id == dataset_id)

    searchable_codes = [f.field_code for f in d.fields if f.searchable]
    if body.search and searchable_codes:
        term = f"%{body.search.strip()}%"
        clauses = [cast(func.json_extract(DatasetRecord.data, f'$."{code}"'), String).ilike(term) for code in searchable_codes]
        stmt = stmt.where(or_(*clauses))

    for code, value in (body.filters or {}).items():
        if value in (None, "", []):
            continue
        expr = cast(func.json_extract(DatasetRecord.data, f'$."{code}"'), String)
        stmt = stmt.where(expr.ilike(f"%{str(value)}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(db.scalar(count_stmt) or 0)

    if body.sort_by:
        expr = cast(func.json_extract(DatasetRecord.data, f'$."{body.sort_by}"'), String)
        stmt = stmt.order_by(expr.desc() if body.sort_order.lower() == "desc" else expr.asc())
    else:
        stmt = stmt.order_by(DatasetRecord.id.asc())

    offset = (body.page - 1) * body.page_size
    records = db.scalars(stmt.offset(offset).limit(body.page_size)).all()
    return {
        "total": total,
        "page": body.page,
        "page_size": body.page_size,
        "rows": [{"_id": r.id, **(r.data or {})} for r in records],
    }


@app.put("/api/records/{record_id}")
def update_record(record_id: int, body: RecordUpdate, db: Session = Depends(get_db)):
    r = db.get(DatasetRecord, record_id)
    if not r:
        raise HTTPException(404, "记录不存在")
    r.data = body.data
    db.commit()
    return {"ok": True}


@app.delete("/api/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    r = db.get(DatasetRecord, record_id)
    if not r:
        raise HTTPException(404, "记录不存在")
    dataset_id = r.dataset_id
    db.delete(r)
    db.flush()
    d = db.get(Dataset, dataset_id)
    if d:
        d.record_count = db.scalar(select(func.count()).select_from(DatasetRecord).where(DatasetRecord.dataset_id == dataset_id)) or 0
    db.commit()
    return {"ok": True}


@app.get("/api/datasets/{dataset_id}/export")
def export_dataset(dataset_id: int, db: Session = Depends(get_db)):
    d = db.scalar(select(Dataset).options(selectinload(Dataset.fields)).where(Dataset.id == dataset_id))
    if not d:
        raise HTTPException(404, "数据集不存在")
    records = db.scalars(select(DatasetRecord).where(DatasetRecord.dataset_id == dataset_id).order_by(DatasetRecord.id)).all()
    columns = [f.field_code for f in d.fields]
    display = {f.field_code: (f"{f.field_name}({f.unit})" if f.unit else f.field_name) for f in d.fields}
    rows = [{display[c]: (r.data or {}).get(c) for c in columns} for r in records]
    output = EXPORT_DIR / f"{d.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    pd.DataFrame(rows).to_excel(output, index=False)
    return FileResponse(output, filename=output.name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.post("/api/imports/inspect")
async def inspect_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(400, "仅支持 .xlsx / .xls 文件")
    stored = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    with stored.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    job = ImportJob(filename=file.filename or stored.name, stored_path=str(stored), status="INSPECTING")
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        sheets = list_sheets(stored)
        if not sheets:
            raise ValueError("Excel 中没有可读取的 Sheet")
        sheet = sheets[0]
        header_row = detect_header_row(stored, sheet)
        payload = preview_payload(stored, sheet, header_row)
        payload["sheets"] = sheets
        job.status = "READY"
        job.sheet_name = sheet
        job.header_row = header_row
        job.preview_json = payload
        job.total_rows = payload["row_count"]
        db.commit()
        return {"import_id": job.id, "filename": job.filename, **payload}
    except Exception as e:
        job.status = "FAILED"
        job.message = str(e)
        db.commit()
        raise HTTPException(400, f"Excel 解析失败：{e}")


@app.post("/api/imports/{import_id}/preview")
def preview_excel(import_id: int, body: ImportPreviewRequest, db: Session = Depends(get_db)):
    job = db.get(ImportJob, import_id)
    if not job:
        raise HTTPException(404, "导入任务不存在")
    path = Path(job.stored_path)
    try:
        payload = preview_payload(path, body.sheet_name, body.header_row)
        payload["sheets"] = list_sheets(path)
        job.sheet_name = body.sheet_name
        job.header_row = body.header_row
        job.preview_json = payload
        job.total_rows = payload["row_count"]
        job.status = "READY"
        db.commit()
        return {"import_id": job.id, "filename": job.filename, **payload}
    except Exception as e:
        raise HTTPException(400, f"预览失败：{e}")


@app.post("/api/imports/{import_id}/commit")
def commit_import(import_id: int, body: ImportCommitRequest, db: Session = Depends(get_db)):
    job = db.get(ImportJob, import_id)
    if not job:
        raise HTTPException(404, "导入任务不存在")
    kb = db.get(KnowledgeBase, body.knowledge_base_id)
    if not kb:
        raise HTTPException(404, "目标知识库不存在")
    enabled_mappings = [m.model_dump() for m in body.mappings if m.enabled]
    if not enabled_mappings:
        raise HTTPException(400, "至少保留一个字段")
    codes = [m["field_code"] for m in enabled_mappings]
    if len(codes) != len(set(codes)):
        raise HTTPException(400, "字段编码不能重复")
    try:
        frame = read_frame(Path(job.stored_path), body.sheet_name, body.header_row)
        for m in enabled_mappings:
            if m["source_name"] not in frame.columns:
                raise ValueError(f"找不到源字段：{m['source_name']}")
        rows = frame_to_json_records(frame, enabled_mappings)
        dataset = Dataset(
            knowledge_base_id=kb.id,
            name=body.dataset_name,
            category=body.category,
            standard_no=body.standard_no,
            source_file_name=job.filename,
            sheet_name=body.sheet_name,
            record_count=len(rows),
            field_count=len(enabled_mappings),
        )
        db.add(dataset)
        db.flush()
        for i, m in enumerate(enabled_mappings, start=1):
            db.add(DatasetField(
                dataset_id=dataset.id,
                source_name=m["source_name"],
                field_code=m["field_code"],
                field_name=m["field_name"],
                data_type=m["data_type"],
                unit=m.get("unit") or None,
                order_no=i,
                searchable=m["searchable"],
                filterable=m["filterable"],
            ))
        db.bulk_save_objects([DatasetRecord(dataset_id=dataset.id, data=row) for row in rows])
        job.status = "SUCCESS"
        job.sheet_name = body.sheet_name
        job.header_row = body.header_row
        job.success_rows = len(rows)
        job.failed_rows = 0
        job.message = f"已导入到 {kb.name} / {dataset.name}"
        db.commit()
        return {"ok": True, "dataset_id": dataset.id, "record_count": len(rows)}
    except Exception as e:
        db.rollback()
        job = db.get(ImportJob, import_id)
        if job:
            job.status = "FAILED"
            job.message = str(e)
            db.commit()
        raise HTTPException(400, f"导入失败：{e}")


@app.get("/api/imports/recent")
def recent_imports(limit: int = 20, db: Session = Depends(get_db)):
    jobs = db.scalars(select(ImportJob).order_by(ImportJob.created_at.desc()).limit(min(limit, 100))).all()
    return [
        {
            "id": j.id,
            "filename": j.filename,
            "status": j.status,
            "sheet_name": j.sheet_name,
            "total_rows": j.total_rows,
            "success_rows": j.success_rows,
            "failed_rows": j.failed_rows,
            "message": j.message,
            "created_at": dt(j.created_at),
        }
        for j in jobs
    ]

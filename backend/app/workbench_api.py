from __future__ import annotations

import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import require_user
from .database import get_db
from .models import Dataset, DatasetField, DatasetRecord, KnowledgeBase, User
from .schemas import WorkbenchSaveRequest

router = APIRouter(prefix="/api/workbench", tags=["workbench"])

RESULT_KB_CODE = "design_result"
RESULT_KB_NAME = "设计成果库"

RESULT_FIELDS = [
    ("SECTION", "分类", "text"),
    ("PARAMETER", "参数", "text"),
    ("VALUE", "取值", "text"),
    ("UNIT", "单位", "text"),
    ("SOURCE", "来源", "text"),
    ("STATUS", "状态", "text"),
]

INPUT_LABELS = [
    ("valve_structure", "阀门结构", "-"),
    ("nps", "公称口径", "-"),
    ("pressure_class", "压力等级", "-"),
    ("bore_type", "通径形式", "-"),
    ("end_connection", "端部连接", "-"),
    ("body_material", "阀体材料", "-"),
    ("ball_material_group", "球体材料组", "-"),
    ("seat_material", "阀座材料", "-"),
    ("design_pressure", "设计压力", "MPa"),
    ("design_temperature", "设计温度", "℃"),
    ("leakage_level", "泄漏等级", "-"),
    ("medium", "介质", "-"),
]


def ensure_result_library(db: Session) -> KnowledgeBase:
    kb = db.scalar(select(KnowledgeBase).where(KnowledgeBase.code == RESULT_KB_CODE))
    if kb:
        return kb
    kb = KnowledgeBase(
        name=RESULT_KB_NAME,
        code=RESULT_KB_CODE,
        type="result",
        description="保存参数工作台每一次生成的输入快照、几何参数、装配参数、来源与状态。",
        accent="blue",
        enabled=True,
    )
    db.add(kb)
    db.flush()
    return kb


def normalize_value(value):
    if value is None:
        return "-"
    text = str(value).strip()
    return text if text else "-"


def safe_name_piece(value) -> str:
    text = normalize_value(value)
    text = re.sub(r'[\\/:*?"<>|]+', '-', text)
    text = re.sub(r"\s+", " ", text).strip(" .-")
    return (text or "未填写")[:48]


def result_row(section: str, parameter: str, value, unit: str = "-", source: str = "-", status: str = "已保存") -> dict:
    return {
        "SECTION": section,
        "PARAMETER": parameter,
        "VALUE": normalize_value(value),
        "UNIT": normalize_value(unit),
        "SOURCE": normalize_value(source),
        "STATUS": normalize_value(status),
    }


@router.post("/save")
def save_workbench_result(
    body: WorkbenchSaveRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not body.geometry_results and not body.assembly_results:
        raise HTTPException(status_code=400, detail="请先生成综合参数后再保存")

    kb = ensure_result_library(db)
    snapshot = body.input_snapshot or {}
    now = datetime.now()
    nps = normalize_value(snapshot.get("nps"))
    pressure = normalize_value(snapshot.get("pressure_class"))
    leakage = normalize_value(snapshot.get("leakage_level"))
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:4].upper()

    if body.name and body.name.strip():
        dataset_name = safe_name_piece(body.name)
    else:
        dataset_name = f"固定球阀-{safe_name_piece(nps)}-{safe_name_piece(pressure)}-{safe_name_piece(leakage)}-{timestamp}-{suffix}"
    dataset_name = dataset_name[:180]

    dataset = Dataset(
        knowledge_base_id=kb.id,
        name=dataset_name,
        category="参数生成记录",
        standard_no=f"{nps} / {pressure} / {leakage}",
        source_file_name=f"参数生成工作台 · {user.display_name}",
        sheet_name=None,
        record_count=0,
        field_count=len(RESULT_FIELDS),
    )
    db.add(dataset)
    db.flush()

    for order_no, (code, field_name, data_type) in enumerate(RESULT_FIELDS, start=1):
        db.add(
            DatasetField(
                dataset_id=dataset.id,
                source_name=field_name,
                field_code=code,
                field_name=field_name,
                data_type=data_type,
                unit=None,
                order_no=order_no,
                searchable=True,
                filterable=code in {"SECTION", "PARAMETER", "SOURCE", "STATUS"},
            )
        )

    rows: list[dict] = []
    rows.append(result_row("保存信息", "保存人", user.display_name, "-", "系统", "已保存"))
    rows.append(result_row("保存信息", "保存时间", now.strftime("%Y-%m-%d %H:%M:%S"), "-", "系统", "已保存"))

    for key, label, unit in INPUT_LABELS:
        rows.append(result_row("输入条件", label, snapshot.get(key), unit, "用户输入", "已保存"))

    for item in body.geometry_results:
        rows.append(
            result_row(
                "零件几何参数",
                item.name,
                item.value,
                item.unit or "-",
                item.source or "-",
                item.status or "待确认",
            )
        )

    for item in body.assembly_results:
        rows.append(
            result_row(
                "装配/接口参数",
                item.name,
                item.value,
                item.unit or "-",
                item.source or "-",
                item.status or "待确认",
            )
        )

    db.bulk_save_objects([DatasetRecord(dataset_id=dataset.id, data=row) for row in rows])
    dataset.record_count = len(rows)
    kb.updated_at = now
    db.commit()
    db.refresh(dataset)

    return {
        "ok": True,
        "knowledge_base_id": kb.id,
        "knowledge_base_name": kb.name,
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "record_count": dataset.record_count,
        "saved_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    }

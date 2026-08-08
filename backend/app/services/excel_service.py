from __future__ import annotations

import json
import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd


KNOWN_CODES = {
    "nps": "NPS",
    "nps数值": "NPS_VALUE",
    "公称口径": "NPS",
    "口径": "NPS",
    "dn": "DN",
    "公称直径": "DN",
    "英寸显示": "INCH_DISPLAY",
    "毫米参考": "MM_REFERENCE",
    "备注": "REMARK",
    "压力等级": "PRESSURE_CLASS",
    "等级数值": "CLASS_VALUE",
    "常用写法": "COMMON_NAME",
    "固定球阀适用性": "FIXED_BALL_APPLICABLE",
    "主要关联标准": "RELATED_STANDARDS",
    "数据状态": "DATA_STATUS",
    "型号": "MODEL",
    "阀门类型": "VALVE_TYPE",
    "球体直径": "BALL_DIAMETER",
    "流道直径": "BORE_DIAMETER",
    "结构长度": "FACE_TO_FACE",
    "材料牌号": "MATERIAL_GRADE",
    "标准": "STANDARD",
    "标准号": "STANDARD_NO",
    "温度": "TEMPERATURE",
    "许用应力": "ALLOWABLE_STRESS",
}


def _safe(v: Any):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, (pd.Timestamp, datetime, date)):
        return v.isoformat()
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass
    return v


def unique_columns(columns: list[Any]) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for i, col in enumerate(columns, start=1):
        base = str(col).strip() if col is not None else ""
        if not base or base.lower().startswith("unnamed"):
            base = f"字段{i}"
        if base in seen:
            seen[base] += 1
            base = f"{base}_{seen[base]}"
        else:
            seen[base] = 1
        result.append(base)
    return result


def detect_header_row(path: Path, sheet_name: str) -> int:
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=30, dtype=object)
    if raw.empty:
        return 0
    scores: list[tuple[int, float]] = []
    for idx, row in raw.iterrows():
        vals = [v for v in row.tolist() if not pd.isna(v) and str(v).strip()]
        if not vals:
            continue
        non_empty = len(vals)
        stringish = sum(1 for v in vals if isinstance(v, str))
        unique_ratio = len(set(map(str, vals))) / max(non_empty, 1)
        score = non_empty * 3 + stringish * 1.5 + unique_ratio
        scores.append((int(idx), score))
    if not scores:
        return 0
    max_score = max(s for _, s in scores)
    # choose the earliest row close to the best score; this favors the real header above data rows
    candidates = [idx for idx, score in scores if score >= max_score * 0.92]
    return min(candidates) if candidates else max(scores, key=lambda x: x[1])[0]


def read_frame(path: Path, sheet_name: str, header_row: int) -> pd.DataFrame:
    frame = pd.read_excel(path, sheet_name=sheet_name, header=header_row, dtype=object)
    frame = frame.dropna(axis=0, how="all").dropna(axis=1, how="all")
    frame.columns = unique_columns(list(frame.columns))
    return frame


def guess_code(name: str, index: int) -> str:
    key = str(name).strip().lower().replace(" ", "")
    if key in KNOWN_CODES:
        return KNOWN_CODES[key]
    ascii_code = re.sub(r"[^A-Za-z0-9]+", "_", str(name)).strip("_").upper()
    if ascii_code and re.search(r"[A-Z]", ascii_code):
        return ascii_code[:80]
    return f"FIELD_{index:03d}"


def guess_type(values: list[Any]) -> str:
    non_null = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not non_null:
        return "text"
    numeric = 0
    for v in non_null:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            numeric += 1
            continue
        try:
            float(str(v).strip())
            numeric += 1
        except Exception:
            pass
    return "number" if numeric / len(non_null) >= 0.72 else "text"


def preview_payload(path: Path, sheet_name: str, header_row: int, limit: int = 8) -> dict:
    frame = read_frame(path, sheet_name, header_row)
    columns = []
    for i, col in enumerate(frame.columns, start=1):
        sample = [_safe(v) for v in frame[col].head(20).tolist()]
        columns.append(
            {
                "source_name": col,
                "field_name": col,
                "field_code": guess_code(col, i),
                "data_type": guess_type(sample),
                "unit": "",
                "searchable": True,
                "filterable": True,
                "enabled": True,
            }
        )
    preview_rows = []
    for _, row in frame.head(limit).iterrows():
        preview_rows.append({col: _safe(row[col]) for col in frame.columns})
    return {
        "sheet_name": sheet_name,
        "header_row": header_row,
        "columns": columns,
        "preview": preview_rows,
        "row_count": int(len(frame)),
    }


def list_sheets(path: Path) -> list[str]:
    book = pd.ExcelFile(path)
    return list(book.sheet_names)


def frame_to_json_records(frame: pd.DataFrame, mappings: list[dict]) -> list[dict]:
    enabled = [m for m in mappings if m.get("enabled", True)]
    rows: list[dict] = []
    for _, row in frame.iterrows():
        data = {}
        all_empty = True
        for m in enabled:
            src = m["source_name"]
            code = m["field_code"]
            value = _safe(row.get(src))
            if value not in (None, ""):
                all_empty = False
            data[code] = value
        if not all_empty:
            rows.append(data)
    return rows

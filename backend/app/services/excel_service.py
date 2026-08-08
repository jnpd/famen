from __future__ import annotations

import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

AUTO_HEADER = -2
NO_HEADER = -1

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

# 只用于增强“像表头”的结构判断，不是字段白名单。
GENERIC_HEADER_HINTS = (
    "名称", "编号", "编码", "类型", "类别", "型号", "规格", "尺寸", "口径", "压力", "等级",
    "材料", "单位", "备注", "说明", "状态", "来源", "标准", "日期", "时间", "数量", "数值",
    "参数", "字段", "变量", "项目", "内容", "范围", "方式", "用途", "是否", "示例", "序号",
    "name", "id", "code", "type", "category", "model", "size", "pressure", "material",
    "unit", "remark", "note", "status", "source", "standard", "date", "time", "count",
    "value", "parameter", "field", "variable", "description", "no", "number",
)
OUTLINE_RE = re.compile(r"^\s*\d+(?:\.\d+)*\s*$")
DATA_CODE_RE = re.compile(r"(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_.\-/|]+$")
GENERIC_SHEET_RE = re.compile(r"^(sheet|工作表)\s*\d*$", re.I)
FOOTER_PREFIXES = (
    "备注", "说明", "注：", "注:", "数据来源", "来源：", "来源:", "合计", "总计", "小计",
    "note", "source", "total", "summary",
)


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


def _is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return not str(v).strip()


def _kind(v: Any) -> str:
    if _is_empty(v):
        return "empty"
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return "number"
    text = str(v).strip().replace(",", "")
    try:
        float(text)
        return "number"
    except Exception:
        return "text"


def _row_values(row) -> list[Any]:
    return row.tolist() if hasattr(row, "tolist") else list(row)


def _non_empty(values: list[Any]) -> list[Any]:
    return [v for v in values if not _is_empty(v)]


def _row_features(values: list[Any]) -> dict[str, float | int | bool]:
    non_empty = _non_empty(values)
    width = max(len(values), 1)
    if not non_empty:
        return {
            "non_empty": 0,
            "non_ratio": 0.0,
            "text_ratio": 0.0,
            "number_ratio": 0.0,
            "unique_ratio": 0.0,
            "outline_ratio": 0.0,
            "hint_ratio": 0.0,
            "dataish_ratio": 0.0,
            "avg_length": 0.0,
            "title_like": False,
        }

    texts = [str(v).strip() for v in non_empty]
    kinds = [_kind(v) for v in non_empty]
    text_ratio = kinds.count("text") / len(non_empty)
    number_ratio = kinds.count("number") / len(non_empty)
    unique_ratio = len(set(texts)) / len(texts)
    outline_ratio = sum(bool(OUTLINE_RE.match(text)) for text in texts) / len(texts)

    hint_hits = 0
    for text in texts:
        lower = text.lower()
        if any(hint.lower() in lower for hint in GENERIC_HEADER_HINTS):
            hint_hits += 1

    dataish = 0
    for value, text in zip(non_empty, texts):
        if _kind(value) == "number":
            dataish += 1
        elif DATA_CODE_RE.fullmatch(text):
            dataish += 1
        elif len(text) <= 24 and any(ch.isdigit() for ch in text) and not any(
            hint.lower() in text.lower() for hint in GENERIC_HEADER_HINTS
        ):
            dataish += 1

    rest_outline = (
        len(texts) > 1
        and not OUTLINE_RE.match(texts[0])
        and all(OUTLINE_RE.match(text) for text in texts[1:])
    )
    title_like = len(non_empty) == 1 or rest_outline

    return {
        "non_empty": len(non_empty),
        "non_ratio": len(non_empty) / width,
        "text_ratio": text_ratio,
        "number_ratio": number_ratio,
        "unique_ratio": unique_ratio,
        "outline_ratio": outline_ratio,
        "hint_ratio": hint_hits / len(non_empty),
        "dataish_ratio": dataish / len(non_empty),
        "avg_length": sum(len(text) for text in texts) / len(texts),
        "title_like": title_like,
    }


def _mask(values: list[Any]) -> list[bool]:
    return [not _is_empty(v) for v in values]


def _mask_similarity(left: list[Any], right: list[Any]) -> float:
    size = max(len(left), len(right))
    lm = _mask(left) + [False] * (size - len(left))
    rm = _mask(right) + [False] * (size - len(right))
    union = sum(a or b for a, b in zip(lm, rm))
    if not union:
        return 0.0
    intersection = sum(a and b for a, b in zip(lm, rm))
    return intersection / union


def _next_non_empty_rows(raw: pd.DataFrame, row_index: int, limit: int = 6) -> list[list[Any]]:
    result: list[list[Any]] = []
    for idx in range(row_index + 1, len(raw)):
        values = _row_values(raw.iloc[idx])
        if _non_empty(values):
            result.append(values)
        if len(result) >= limit:
            break
    return result


def _type_stability(rows: list[list[Any]]) -> float:
    if len(rows) < 2:
        return 0.0
    width = max(len(row) for row in rows)
    column_scores: list[float] = []
    for col in range(width):
        kinds = []
        for row in rows:
            if col < len(row) and not _is_empty(row[col]):
                kinds.append(_kind(row[col]))
        if len(kinds) < 2:
            continue
        number = kinds.count("number")
        text = kinds.count("text")
        column_scores.append(max(number, text) / len(kinds))
    return sum(column_scores) / len(column_scores) if column_scores else 0.0


def _score_header_candidate(raw: pd.DataFrame, row_index: int) -> tuple[float, dict[str, Any]]:
    values = _row_values(raw.iloc[row_index])
    features = _row_features(values)
    if not features["non_empty"]:
        return -999.0, features

    following = _next_non_empty_rows(raw, row_index, 6)
    below_mask_similarity = (
        sum(_mask_similarity(values, row) for row in following) / len(following)
        if following else 0.0
    )
    stability = _type_stability(following)
    below_text_ratio = (
        sum(float(_row_features(row)["text_ratio"]) for row in following) / len(following)
        if following else 0.0
    )
    contrast = max(0.0, float(features["text_ratio"]) - below_text_ratio)

    score = 0.0
    score += min(int(features["non_empty"]), 12) * 2.0
    score += float(features["non_ratio"]) * 8.0
    score += float(features["text_ratio"]) * 18.0
    score += float(features["unique_ratio"]) * 12.0
    score += float(features["hint_ratio"]) * 15.0
    score += below_mask_similarity * 12.0
    score += stability * 14.0
    score += contrast * 10.0
    score += min(len(following), 4) * 2.0

    score -= float(features["outline_ratio"]) * 28.0
    score -= float(features["number_ratio"]) * 8.0
    if bool(features["title_like"]):
        score -= 32.0
    if float(features["avg_length"]) > 45:
        score -= 8.0

    features = {
        **features,
        "below_mask_similarity": below_mask_similarity,
        "type_stability": stability,
        "type_contrast": contrast,
    }
    return score, features


def _suggest_title(raw: pd.DataFrame, header_row: int | None, sheet_name: str) -> tuple[str, int | None]:
    end = header_row if header_row is not None else min(len(raw), 8)
    best: tuple[int, str] | None = None

    for idx in range(max(0, end)):
        values = _non_empty(_row_values(raw.iloc[idx]))
        if not values:
            continue
        texts = [str(v).strip() for v in values]

        candidate = None
        if len(values) == 1 and _kind(values[0]) == "text":
            candidate = texts[0]
        elif (
            len(values) > 1
            and _kind(values[0]) == "text"
            and all(OUTLINE_RE.match(text) for text in texts[1:])
        ):
            candidate = texts[0]

        if candidate and 1 <= len(candidate) <= 100:
            best = (idx, candidate)

    clean_sheet = (sheet_name or "").strip()
    if clean_sheet and not GENERIC_SHEET_RE.match(clean_sheet):
        return clean_sheet, best[0] if best else None
    if best:
        return best[1], best[0]
    return clean_sheet or "未命名数据集", None


def _confidence(score: float, features: dict[str, Any], has_title_above: bool) -> int:
    base = max(0.0, min(100.0, (score - 45.0) / 55.0 * 100.0))
    base += float(features.get("hint_ratio", 0.0)) * 16.0
    base += float(features.get("type_contrast", 0.0)) * 10.0
    base += float(features.get("below_mask_similarity", 0.0)) * 8.0
    base += 6.0 if has_title_above else 0.0
    base -= float(features.get("dataish_ratio", 0.0)) * 24.0
    return int(round(max(0.0, min(100.0, base))))


def analyze_sheet_structure(path: Path, sheet_name: str, scan_rows: int = 60) -> dict[str, Any]:
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=scan_rows, dtype=object)
    raw = raw.dropna(axis=1, how="all")
    if raw.empty:
        return {
            "header_row": None,
            "header_confidence": 0,
            "confidence_level": "low",
            "analysis_message": "该 Sheet 没有可识别的数据。",
            "suggested_dataset_name": sheet_name or "未命名数据集",
            "title_row": None,
            "structure_type": "empty",
            "header_candidates": [],
        }

    candidates: list[tuple[int, float, dict[str, Any]]] = []
    for idx in range(len(raw)):
        score, features = _score_header_candidate(raw, idx)
        if features.get("non_empty") and not features.get("title_like"):
            candidates.append((idx, score, features))

    ranked = sorted(candidates, key=lambda item: item[1], reverse=True)
    if not ranked:
        suggested_name, title_row = _suggest_title(raw, None, sheet_name)
        return {
            "header_row": None,
            "header_confidence": 0,
            "confidence_level": "low",
            "analysis_message": "没有找到明显的表头行，可选择“无表头”或手动指定。",
            "suggested_dataset_name": suggested_name,
            "title_row": title_row,
            "structure_type": "document",
            "header_candidates": [],
        }

    best_score = ranked[0][1]
    threshold = max(55.0, best_score * 0.90)
    close_candidates = [item for item in candidates if item[1] >= threshold]
    selected = min(close_candidates, key=lambda item: item[0]) if close_candidates else ranked[0]
    header_row, selected_score, features = selected

    suggested_name, title_row = _suggest_title(raw, header_row, sheet_name)
    has_title_above = title_row is not None and title_row < header_row
    confidence = _confidence(selected_score, features, has_title_above)

    # 对“整页都是键值说明/文档”的 Sheet 宁可低置信度，也不强行误导用户。
    if best_score < 55.0 or (features.get("non_empty", 0) <= 2 and features.get("below_mask_similarity", 0) < 0.45):
        header_row = None
        confidence = min(confidence, 45)
        level = "low"
        message = "该 Sheet 更像说明/配置页，没有找到可靠表头；建议人工选择表头或使用“无表头”。"
        structure_type = "document"
    else:
        level = "high" if confidence >= 85 else "medium" if confidence >= 60 else "low"
        structure_type = "table"
        if level == "high":
            message = f"已自动识别第 {header_row + 1} 行为表头，结构较稳定。"
        elif level == "medium":
            message = f"推荐第 {header_row + 1} 行为表头，请在导入前确认预览。"
        else:
            message = f"表头识别可信度较低，当前推荐第 {header_row + 1} 行，请人工确认。"

    header_candidates = [
        {"row": idx, "display_row": idx + 1, "score": round(float(score), 1)}
        for idx, score, _ in ranked[:5]
        if score >= 40
    ]

    return {
        "header_row": header_row,
        "header_confidence": confidence,
        "confidence_level": level,
        "analysis_message": message,
        "suggested_dataset_name": suggested_name,
        "title_row": title_row,
        "structure_type": structure_type,
        "header_candidates": header_candidates,
    }


def detect_header_row(path: Path, sheet_name: str) -> int:
    """返回 0-based 表头；低可信度时宁可返回 NO_HEADER，避免误吞第一条数据。"""
    analysis = analyze_sheet_structure(path, sheet_name)
    header = analysis.get("header_row")
    if header is None or int(analysis.get("header_confidence", 0)) < 60:
        return NO_HEADER
    return int(header)


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


def _looks_like_footer(row: pd.Series) -> bool:
    values = _non_empty(_row_values(row))
    if not values or len(values) > 2:
        return False
    first = str(values[0]).strip().lower()
    return any(first.startswith(prefix.lower()) for prefix in FOOTER_PREFIXES)


def _trim_footer_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    cut_at = None
    for pos in range(len(frame)):
        if pos < 2:
            continue
        if _looks_like_footer(frame.iloc[pos]):
            cut_at = pos
            break
    return frame.iloc[:cut_at].copy() if cut_at is not None else frame


def _resolve_header(path: Path, sheet_name: str, header_row: int) -> tuple[int, dict[str, Any]]:
    analysis = analyze_sheet_structure(path, sheet_name)
    if header_row == AUTO_HEADER:
        detected = analysis.get("header_row")
        confidence = int(analysis.get("header_confidence", 0))
        if detected is None or confidence < 60:
            return NO_HEADER, analysis
        return int(detected), analysis
    return header_row, analysis


def read_frame(path: Path, sheet_name: str, header_row: int) -> pd.DataFrame:
    resolved_header, _ = _resolve_header(path, sheet_name, header_row) if header_row == AUTO_HEADER else (header_row, {})

    if resolved_header == NO_HEADER:
        frame = pd.read_excel(path, sheet_name=sheet_name, header=None, dtype=object)
        frame = frame.dropna(axis=0, how="all").dropna(axis=1, how="all")
        frame.columns = [f"字段{i}" for i in range(1, len(frame.columns) + 1)]
    else:
        frame = pd.read_excel(path, sheet_name=sheet_name, header=resolved_header, dtype=object)
        frame = frame.dropna(axis=0, how="all").dropna(axis=1, how="all")
        frame.columns = unique_columns(list(frame.columns))

    frame = _trim_footer_rows(frame)
    return frame.reset_index(drop=True)


def guess_code(name: str, index: int) -> str:
    key = str(name).strip().lower().replace(" ", "")
    if key in KNOWN_CODES:
        return KNOWN_CODES[key]
    ascii_code = re.sub(r"[^A-Za-z0-9]+", "_", str(name)).strip("_").upper()
    if ascii_code and re.search(r"[A-Z]", ascii_code):
        return ascii_code[:80]
    return f"FIELD_{index:03d}"


def guess_type(values: list[Any]) -> str:
    non_null = [v for v in values if not _is_empty(v)]
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
    resolved_header, analysis = _resolve_header(path, sheet_name, header_row)
    frame = read_frame(path, sheet_name, resolved_header)

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

    has_header = resolved_header >= 0
    data_start_row = resolved_header + 2 if has_header else 1
    if header_row == AUTO_HEADER:
        mode = "auto"
    elif resolved_header == NO_HEADER:
        mode = "none"
    else:
        mode = "row"

    return {
        "sheet_name": sheet_name,
        "header_row": resolved_header,
        "header_mode": mode,
        "has_header": has_header,
        "data_start_row": data_start_row,
        "columns": columns,
        "preview": preview_rows,
        "row_count": int(len(frame)),
        "header_confidence": analysis.get("header_confidence", 0),
        "confidence_level": analysis.get("confidence_level", "low"),
        "analysis_message": analysis.get("analysis_message", ""),
        "suggested_dataset_name": analysis.get("suggested_dataset_name") or sheet_name,
        "structure_type": analysis.get("structure_type", "table"),
        "header_candidates": analysis.get("header_candidates", []),
        "detected_header_row": (
            NO_HEADER if analysis.get("header_row") is None else int(analysis.get("header_row"))
        ),
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

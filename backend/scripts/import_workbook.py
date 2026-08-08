from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Dataset, DatasetField, DatasetRecord, KnowledgeBase
from app.seed import seed
from app.services.excel_service import (
    analyze_sheet_structure,
    frame_to_json_records,
    list_sheets,
    preview_payload,
    read_frame,
)


METADATA_WORDS = ("目录", "说明", "总览", "汇总", "索引")
UNIT_COLUMN_NAMES = {"单位", "unit", "units", "uom"}
HEADER_UNIT_RE = re.compile(
    r"(?:\(|（|\[|【)\s*(mm|cm|m|in|inch|mpa|kpa|pa|bar|n|kn|n·m|nm|℃|°c|°f|个|%)\s*(?:\)|）|\]|】)",
    re.I,
)
DIMENSION_HINTS = (
    "直径", "外径", "内径", "孔径", "通径", "半径", "长度", "深度", "厚度", "高度", "宽度",
    "中心圆", "壁厚", "间隙", "截面", "槽深", "槽宽", "导角", "凸台", "凹槽", "轴径", "键b", "键宽",
    "键高", "有效长度", "面对面", "端到端", "毫米", "diameter", "radius", "length", "depth", "thickness",
    "width", "height", "bore", "wall", "circle",
)
NON_DIMENSION_HINTS = (
    "数量", "个数", "牙数", "等级", "状态", "来源", "材料", "类型", "型式", "型号", "规格", "编号", "代码",
    "备注", "说明", "是否", "名称", "pressure", "temperature", "count", "status", "material", "type", "model",
)
EXACT_UNIT_HINTS = {
    "nps数值": "in",
    "毫米参考": "mm",
}


def recommend_library_code(sheet_name: str, default_code: str = "parameter") -> str:
    """Only routes a detected table to a knowledge base; it does not affect structure detection."""
    name = (sheet_name or "").strip().lower()

    if any(word in name for word in ("材料", "material")):
        return "material"
    if any(word in name for word in ("solidworks", "参数映射", "生成日志", "用户输入", "bom")):
        return "bom"
    if any(word in name for word in ("校核", "公式", "计算规则", "formula")):
        return "formula"
    if any(word in name for word in ("口径基础", "压力等级", "泄漏等级", "字典", "dictionary")):
        return "dictionary"
    if any(
        word in name
        for word in (
            "通径", "结构长度", "法兰尺寸", "壁厚", "键槽", "o形圈", "o-ring",
            "npt", "iso5211", "标准", "standard",
        )
    ):
        return "standard"
    if any(word in name for word in ("球体", "阀座", "阀杆", "注脂", "泄放", "设计工况", "参数")):
        return "parameter"
    return default_code


def is_metadata_sheet(sheet_name: str) -> bool:
    name = (sheet_name or "").strip().lower()
    return any(word.lower() in name for word in METADATA_WORDS)


def make_unique_codes(columns: list[dict]) -> list[dict]:
    seen: dict[str, int] = {}
    result: list[dict] = []
    for item in columns:
        row = dict(item)
        base = (row.get("field_code") or "FIELD").strip() or "FIELD"
        seen[base] = seen.get(base, 0) + 1
        row["field_code"] = base if seen[base] == 1 else f"{base}_{seen[base]}"
        result.append(row)
    return result


def normalize_unit(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "-", "/", "待定", "待确认"}:
        return None
    aliases = {
        "毫米": "mm",
        "millimeter": "mm",
        "millimetre": "mm",
        "英寸": "in",
        "inch": "in",
        "inches": "in",
        "mpa": "MPa",
        "kpa": "kPa",
        "pa": "Pa",
        "n": "N",
        "kn": "kN",
        "nm": "N·m",
        "n·m": "N·m",
        "°c": "℃",
        "c": "℃",
    }
    return aliases.get(text.lower(), text)


def most_common_unit(values) -> str | None:
    units = [normalize_unit(v) for v in values]
    units = [u for u in units if u]
    if not units:
        return None
    counts = Counter(units)
    unit, count = counts.most_common(1)[0]
    # Static DatasetField.unit is safe only when one unit dominates the column.
    if len(units) >= 2 and count / len(units) < 0.8:
        return None
    return unit


def unit_from_header(name: str) -> str | None:
    text = str(name or "").strip()
    exact = EXACT_UNIT_HINTS.get(text.lower().replace(" ", ""))
    if exact:
        return exact
    match = HEADER_UNIT_RE.search(text)
    return normalize_unit(match.group(1)) if match else None


def looks_like_dimension(name: str) -> bool:
    text = str(name or "").strip().lower()
    if any(word.lower() in text for word in NON_DIMENSION_HINTS):
        return False
    return any(word.lower() in text for word in DIMENSION_HINTS)


def infer_column_units(frame, columns: list[dict]) -> list[dict]:
    """Infer field metadata units without changing row data.

    Priority: explicit unit in header > adjacent Unit column > conservative
    engineering-dimension fallback. Unknown units stay empty rather than guessing.
    """
    result = [dict(item) for item in columns]
    index_by_source = {str(item.get("source_name")): idx for idx, item in enumerate(result)}

    # 1) Explicit unit embedded in the header, e.g. Diameter(mm).
    for item in result:
        if not item.get("unit"):
            item["unit"] = unit_from_header(item.get("field_name") or item.get("source_name")) or ""

    # 2) A stable Unit column usually describes the immediately preceding value column.
    for pos, col in enumerate(list(frame.columns)):
        col_name = str(col).strip().lower()
        if col_name not in UNIT_COLUMN_NAMES:
            continue
        unit = most_common_unit(frame[col].head(100).tolist())
        if not unit or pos <= 0:
            continue
        previous = str(frame.columns[pos - 1])
        target_idx = index_by_source.get(previous)
        if target_idx is None:
            continue
        # Do not assign one static unit to generic row-wise value tables where units vary per row.
        prev_name = str(result[target_idx].get("field_name") or previous).strip().lower()
        if prev_name in {"取值", "值", "示例值", "value", "sample value"}:
            continue
        if not result[target_idx].get("unit"):
            result[target_idx]["unit"] = unit

    # 3) Conservative fallback for mechanical geometry tables. This intentionally
    # avoids pressure/temperature/count/status fields.
    for item in result:
        if item.get("unit"):
            continue
        name = item.get("field_name") or item.get("source_name") or ""
        if looks_like_dimension(name):
            item["unit"] = "mm"

    return result


def import_dataset(db, workbook: Path, sheet_name: str, analysis: dict, kb: KnowledgeBase, replace: bool) -> tuple[str, int]:
    header_row = analysis.get("header_row")

    # Keep this call compatible with both old and new excel_service.py.
    payload = preview_payload(workbook, sheet_name, header_row)
    frame = read_frame(workbook, sheet_name, header_row)
    columns = make_unique_codes(payload.get("columns") or [])
    columns = infer_column_units(frame, columns)
    if not columns:
        return "skip:no-fields", 0

    dataset_name = (analysis.get("suggested_dataset_name") or sheet_name or "未命名数据集").strip()
    existing = db.scalar(
        select(Dataset).where(
            Dataset.knowledge_base_id == kb.id,
            Dataset.name == dataset_name,
        )
    )
    if existing and not replace:
        return "skip:exists", 0
    if existing and replace:
        db.delete(existing)
        db.flush()

    mappings = [
        {
            "source_name": c["source_name"],
            "field_name": c["field_name"],
            "field_code": c["field_code"],
            "data_type": c.get("data_type", "text"),
            "unit": c.get("unit") or None,
            "searchable": c.get("searchable", True),
            "filterable": c.get("filterable", True),
            "enabled": True,
        }
        for c in columns
    ]
    rows = frame_to_json_records(frame, mappings)
    if not rows:
        return "skip:no-data", 0

    dataset = Dataset(
        knowledge_base_id=kb.id,
        name=dataset_name,
        category="Excel整本导入",
        source_file_name=workbook.name,
        sheet_name=sheet_name,
        record_count=len(rows),
        field_count=len(mappings),
    )
    db.add(dataset)
    db.flush()

    for idx, m in enumerate(mappings, start=1):
        db.add(
            DatasetField(
                dataset_id=dataset.id,
                source_name=m["source_name"],
                field_code=m["field_code"],
                field_name=m["field_name"],
                data_type=m["data_type"],
                unit=m.get("unit"),
                order_no=idx,
                searchable=m["searchable"],
                filterable=m["filterable"],
            )
        )

    db.bulk_save_objects([DatasetRecord(dataset_id=dataset.id, data=row) for row in rows])
    return "imported", len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import all reliable table-like sheets from an Excel workbook into SQLite.")
    parser.add_argument("workbook", help="Excel file path (.xlsx/.xls)")
    parser.add_argument("--default-kb", default="parameter", help="Fallback knowledge base code (default: parameter)")
    parser.add_argument("--min-confidence", type=int, default=60, help="Minimum auto-import confidence (default: 60)")
    parser.add_argument("--include-metadata", action="store_true", help="Also import metadata/description/summary/index sheets")
    parser.add_argument("--include-low-confidence", action="store_true", help="Try importing low-confidence sheets")
    parser.add_argument("--replace", action="store_true", help="Replace an existing dataset with the same name in the same knowledge base")
    args = parser.parse_args()

    workbook = Path(args.workbook).expanduser().resolve()
    if not workbook.exists():
        print(f"[ERROR] File not found: {workbook}")
        return 2
    if workbook.suffix.lower() not in {".xlsx", ".xls"}:
        print("[ERROR] Only .xlsx / .xls files are supported")
        return 2

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
        libraries = {row.code: row for row in db.scalars(select(KnowledgeBase)).all()}
        if args.default_kb not in libraries:
            print(f"[ERROR] Default knowledge base does not exist: {args.default_kb}")
            return 2

        imported_count = 0
        imported_rows = 0
        skipped: list[str] = []

        print(f"\nWorkbook: {workbook.name}")
        print("=" * 88)
        for sheet_name in list_sheets(workbook):
            try:
                analysis = analyze_sheet_structure(workbook, sheet_name)
                confidence = int(analysis.get("header_confidence") or 0)
                structure_type = analysis.get("structure_type") or "table"
                header_row = analysis.get("header_row")

                if is_metadata_sheet(sheet_name) and not args.include_metadata:
                    skipped.append(f"{sheet_name} (metadata)")
                    print(f"[SKIP] {sheet_name} | metadata/description sheet")
                    continue
                if structure_type != "table" or header_row is None:
                    if not args.include_low_confidence:
                        skipped.append(f"{sheet_name} (no reliable header)")
                        print(f"[SKIP] {sheet_name} | no reliable header")
                        continue
                if confidence < args.min_confidence and not args.include_low_confidence:
                    skipped.append(f"{sheet_name} (confidence {confidence}%)")
                    print(f"[SKIP] {sheet_name} | confidence {confidence}%")
                    continue

                kb_code = recommend_library_code(sheet_name, args.default_kb)
                kb = libraries.get(kb_code) or libraries[args.default_kb]
                status, row_count = import_dataset(db, workbook, sheet_name, analysis, kb, args.replace)
                if status == "imported":
                    imported_count += 1
                    imported_rows += row_count
                    print(
                        f"[ OK ] {sheet_name} -> {kb.name} | "
                        f"header row {header_row + 1} | confidence {confidence}% | {row_count} rows"
                    )
                else:
                    skipped.append(f"{sheet_name} ({status})")
                    print(f"[SKIP] {sheet_name} | {status}")
            except Exception as exc:
                db.rollback()
                skipped.append(f"{sheet_name} (error: {exc})")
                print(f"[ERR ] {sheet_name} | {type(exc).__name__}: {exc}")
                continue

        db.commit()

    print("=" * 88)
    print(f"DONE: {imported_count} datasets, {imported_rows} rows imported, {len(skipped)} sheets skipped.")
    if skipped:
        print("Skipped sheets:")
        for item in skipped:
            print(f"  - {item}")
    print("\nRefresh the web page to see the imported datasets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

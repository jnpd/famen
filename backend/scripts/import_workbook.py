from __future__ import annotations

import argparse
import sys
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


def import_dataset(db, workbook: Path, sheet_name: str, analysis: dict, kb: KnowledgeBase, replace: bool) -> tuple[str, int]:
    header_row = analysis.get("header_row")

    # Keep this call compatible with both the old and new excel_service.py.
    # The structure analysis is already completed above; preview_payload is only
    # needed here to build dynamic column definitions.
    payload = preview_payload(workbook, sheet_name, header_row)
    columns = make_unique_codes(payload.get("columns") or [])
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

    frame = read_frame(workbook, sheet_name, header_row)
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

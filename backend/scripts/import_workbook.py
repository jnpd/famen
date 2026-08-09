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
from app.services.excel_service import analyze_sheet_structure, frame_to_json_records, list_sheets, preview_payload, read_frame

METADATA_WORDS = ("目录", "说明", "总览", "汇总", "索引")


def recommend_library_code(sheet_name: str, default_code: str = "parameter") -> str:
    name = (sheet_name or "").strip().lower()
    if any(x in name for x in ("材料", "material")): return "material"
    if any(x in name for x in ("solidworks", "参数映射", "生成日志", "用户输入", "bom")): return "bom"
    if any(x in name for x in ("校核", "公式", "计算规则", "formula")): return "formula"
    if any(x in name for x in ("口径基础", "压力等级", "泄漏等级", "字典", "dictionary")): return "dictionary"
    if any(x in name for x in ("通径", "结构长度", "法兰尺寸", "壁厚", "键槽", "o形圈", "o-ring", "npt", "iso5211", "标准", "standard")): return "standard"
    if any(x in name for x in ("球体", "阀座", "阀杆", "注脂", "泄放", "设计工况", "参数")): return "parameter"
    return default_code


def is_metadata_sheet(sheet_name: str) -> bool:
    return any(word in (sheet_name or "") for word in METADATA_WORDS)


def make_unique_codes(columns: list[dict]) -> list[dict]:
    seen = {}
    result = []
    for item in columns:
        row = dict(item)
        base = (row.get("field_code") or "FIELD").strip() or "FIELD"
        seen[base] = seen.get(base, 0) + 1
        row["field_code"] = base if seen[base] == 1 else f"{base}_{seen[base]}"
        result.append(row)
    return result


def import_dataset(db, workbook: Path, sheet_name: str, analysis: dict, kb: KnowledgeBase, replace: bool):
    header_row = int(analysis["header_row"])
    payload = preview_payload(workbook, sheet_name, header_row)
    columns = make_unique_codes(payload.get("columns") or [])
    frame = read_frame(workbook, sheet_name, header_row)
    if not columns:
        return "skip:no-fields", 0

    dataset_name = (analysis.get("suggested_dataset_name") or sheet_name or "未命名数据集").strip()
    existing = db.scalar(select(Dataset).where(Dataset.knowledge_base_id == kb.id, Dataset.name == dataset_name))
    if existing and not replace:
        return "skip:exists", 0
    if existing and replace:
        db.delete(existing)
        db.flush()

    mappings = [{
        "source_name": c["source_name"], "field_name": c["field_name"], "field_code": c["field_code"],
        "data_type": c.get("data_type", "text"), "unit": c.get("unit") or None,
        "searchable": c.get("searchable", True), "filterable": c.get("filterable", True), "enabled": True,
    } for c in columns]
    rows = frame_to_json_records(frame, mappings)
    if not rows:
        return "skip:no-data", 0

    dataset = Dataset(
        knowledge_base_id=kb.id, name=dataset_name, category="Excel整本导入",
        source_file_name=workbook.name, sheet_name=sheet_name,
        record_count=len(rows), field_count=len(mappings),
    )
    db.add(dataset)
    db.flush()
    for idx, m in enumerate(mappings, start=1):
        db.add(DatasetField(
            dataset_id=dataset.id, source_name=m["source_name"], field_code=m["field_code"],
            field_name=m["field_name"], data_type=m["data_type"], unit=m.get("unit"),
            order_no=idx, searchable=m["searchable"], filterable=m["filterable"],
        ))
    db.bulk_save_objects([DatasetRecord(dataset_id=dataset.id, data=row) for row in rows])
    return "imported", len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import all reliable table-like sheets from a workbook into SQLite.")
    parser.add_argument("workbook")
    parser.add_argument("--default-kb", default="parameter")
    parser.add_argument("--min-confidence", type=int, default=60)
    parser.add_argument("--include-metadata", action="store_true")
    parser.add_argument("--include-low-confidence", action="store_true")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    workbook = Path(args.workbook).expanduser().resolve()
    if not workbook.exists() or workbook.suffix.lower() not in {".xlsx", ".xls"}:
        print(f"[ERROR] Invalid workbook: {workbook}")
        return 2

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
        libraries = {x.code: x for x in db.scalars(select(KnowledgeBase)).all()}
        imported_count = imported_rows = 0
        skipped = []
        print(f"\nWorkbook: {workbook.name}\n" + "=" * 88)
        for sheet_name in list_sheets(workbook):
            try:
                analysis = analyze_sheet_structure(workbook, sheet_name)
                confidence = int(analysis.get("header_confidence") or 0)
                header_row = analysis.get("header_row")
                if is_metadata_sheet(sheet_name) and not args.include_metadata:
                    print(f"[SKIP] {sheet_name} | metadata/description sheet"); skipped.append(sheet_name); continue
                if (analysis.get("structure_type") != "table" or header_row is None) and not args.include_low_confidence:
                    print(f"[SKIP] {sheet_name} | no reliable header"); skipped.append(sheet_name); continue
                if confidence < args.min_confidence and not args.include_low_confidence:
                    print(f"[SKIP] {sheet_name} | confidence {confidence}%"); skipped.append(sheet_name); continue
                kb_code = recommend_library_code(sheet_name, args.default_kb)
                kb = libraries.get(kb_code) or libraries[args.default_kb]
                status, count = import_dataset(db, workbook, sheet_name, analysis, kb, args.replace)
                if status == "imported":
                    imported_count += 1; imported_rows += count
                    print(f"[ OK ] {sheet_name} -> {kb.name} | header row {int(header_row)+1} | confidence {confidence}% | {count} rows")
                else:
                    print(f"[SKIP] {sheet_name} | {status}"); skipped.append(sheet_name)
            except Exception as exc:
                db.rollback(); skipped.append(sheet_name)
                print(f"[ERR ] {sheet_name} | {type(exc).__name__}: {exc}")
        db.commit()

    print("=" * 88)
    print(f"DONE: {imported_count} datasets, {imported_rows} rows imported, {len(skipped)} sheets skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

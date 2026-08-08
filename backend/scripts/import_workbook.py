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
    """只做知识库路由推荐，不参与 Excel 结构识别；未知 Sheet 自动落到默认库。"""
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
    payload = preview_payload(workbook, sheet_name, header_row, analysis=analysis, header_mode="auto")
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
    parser = argparse.ArgumentParser(description="批量扫描 Excel 全部 Sheet，并写入阀门知识库 SQLite。")
    parser.add_argument("workbook", help="Excel 文件路径（.xlsx/.xls）")
    parser.add_argument("--default-kb", default="parameter", help="无法判断时默认知识库 code，默认 parameter")
    parser.add_argument("--min-confidence", type=int, default=60, help="自动导入最低表头可信度，默认 60")
    parser.add_argument("--include-metadata", action="store_true", help="同时导入目录/说明/汇总/索引类 Sheet")
    parser.add_argument("--include-low-confidence", action="store_true", help="低可信度 Sheet 也尝试导入")
    parser.add_argument("--replace", action="store_true", help="同知识库同名数据集存在时替换")
    args = parser.parse_args()

    workbook = Path(args.workbook).expanduser().resolve()
    if not workbook.exists():
        print(f"[ERROR] 文件不存在：{workbook}")
        return 2
    if workbook.suffix.lower() not in {".xlsx", ".xls"}:
        print("[ERROR] 仅支持 .xlsx / .xls")
        return 2

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
        libraries = {row.code: row for row in db.scalars(select(KnowledgeBase)).all()}
        if args.default_kb not in libraries:
            print(f"[ERROR] 默认知识库不存在：{args.default_kb}")
            return 2

        imported_count = 0
        imported_rows = 0
        skipped: list[str] = []

        print(f"\n文件：{workbook.name}")
        print("=" * 72)
        for sheet_name in list_sheets(workbook):
            analysis = analyze_sheet_structure(workbook, sheet_name)
            confidence = int(analysis.get("header_confidence") or 0)
            structure_type = analysis.get("structure_type") or "table"
            header_row = analysis.get("header_row")

            if is_metadata_sheet(sheet_name) and not args.include_metadata:
                skipped.append(f"{sheet_name}（元数据/说明类）")
                print(f"[SKIP] {sheet_name:<22} 元数据/说明类")
                continue
            if structure_type != "table" or header_row is None:
                if not args.include_low_confidence:
                    skipped.append(f"{sheet_name}（未找到可靠表头）")
                    print(f"[SKIP] {sheet_name:<22} 未找到可靠表头")
                    continue
            if confidence < args.min_confidence and not args.include_low_confidence:
                skipped.append(f"{sheet_name}（可信度 {confidence}%）")
                print(f"[SKIP] {sheet_name:<22} 可信度 {confidence}%")
                continue

            kb_code = recommend_library_code(sheet_name, args.default_kb)
            kb = libraries.get(kb_code) or libraries[args.default_kb]
            status, row_count = import_dataset(db, workbook, sheet_name, analysis, kb, args.replace)
            if status == "imported":
                imported_count += 1
                imported_rows += row_count
                print(
                    f"[ OK ] {sheet_name:<22} -> {kb.name:<10} "
                    f"表头第 {header_row + 1} 行 | 可信度 {confidence:>3}% | {row_count} 条"
                )
            else:
                skipped.append(f"{sheet_name}（{status}）")
                print(f"[SKIP] {sheet_name:<22} {status}")

        db.commit()

    print("=" * 72)
    print(f"完成：导入 {imported_count} 个数据集，共 {imported_rows} 条记录；跳过 {len(skipped)} 个 Sheet。")
    if skipped:
        print("跳过项：")
        for item in skipped:
            print(f"  - {item}")
    print("\n现在刷新 Web 页面即可看到新数据集。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

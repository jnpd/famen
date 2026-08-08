import os
from sqlalchemy import select
from sqlalchemy.orm import Session
from .auth import hash_password
from .models import Dataset, DatasetField, DatasetRecord, KnowledgeBase, User

LIBRARIES = [
    ("基础字典库", "dictionary", "dictionary", "系统统一口径、压力等级、类型、材料等基础字典", "green"),
    ("标准数字库", "standard", "standard", "ASME、API、GB 等标准数字化参数", "green"),
    ("企业公式库", "formula", "formula", "企业内部设计公式、计算规则与审批版本", "purple"),
    ("阀门参数库", "parameter", "parameter", "不同阀门、型号、规格的工程结构参数", "blue"),
    ("材料标准库", "material", "material", "材料牌号、标准号、强度与温度参数", "green"),
    ("BOM规则库", "bom", "bom", "零部件选配、规格关联与BOM生成规则", "blue"),
]


def create_dataset(db: Session, kb: KnowledgeBase, name: str, fields: list[tuple], rows: list[dict]):
    ds = Dataset(knowledge_base_id=kb.id, name=name, category="基础字典", source_file_name="系统示例数据")
    db.add(ds)
    db.flush()
    for idx, item in enumerate(fields, start=1):
        code, field_name, data_type, unit = item
        db.add(DatasetField(
            dataset_id=ds.id,
            source_name=field_name,
            field_code=code,
            field_name=field_name,
            data_type=data_type,
            unit=unit,
            order_no=idx,
            searchable=True,
            filterable=True,
        ))
    for row in rows:
        db.add(DatasetRecord(dataset_id=ds.id, data=row))
    ds.record_count = len(rows)
    ds.field_count = len(fields)


def ensure_admin(db: Session):
    username = os.getenv("VALVE_ADMIN_USERNAME", "admin")
    display_name = os.getenv("VALVE_ADMIN_DISPLAY_NAME", "管理员")
    password = os.getenv("VALVE_ADMIN_PASSWORD", "Admin@123456")
    user = db.scalar(select(User).where(User.username == username))
    if user:
        return
    password_hash, password_salt = hash_password(password)
    db.add(User(
        username=username,
        display_name=display_name,
        role="admin",
        password_hash=password_hash,
        password_salt=password_salt,
        enabled=True,
    ))
    db.commit()


def seed(db: Session):
    ensure_admin(db)
    existing = db.scalar(select(KnowledgeBase.id).limit(1))
    if not existing:
        for name, code, typ, desc, accent in LIBRARIES:
            db.add(KnowledgeBase(name=name, code=code, type=typ, description=desc, accent=accent))
        db.commit()

    dictionary = db.scalar(select(KnowledgeBase).where(KnowledgeBase.code == "dictionary"))
    if not dictionary:
        return
    has_dataset = db.scalar(select(Dataset.id).where(Dataset.knowledge_base_id == dictionary.id).limit(1))
    if has_dataset:
        return

    diameter_fields = [
        ("NPS", "公称口径", "text", ""),
        ("NPS_VALUE", "NPS数值", "number", "in"),
        ("DN", "DN", "text", ""),
        ("INCH_DISPLAY", "英寸显示", "text", ""),
        ("MM_REFERENCE", "毫米参考", "number", "mm"),
        ("REMARK", "备注", "text", ""),
    ]
    diameters = [
        ("NPS2", 2, "DN50", '2"', 50, "常用固定球阀口径"),
        ("NPS2.5", 2.5, "DN65", '2.5"', 65, "可选口径"),
        ("NPS3", 3, "DN80", '3"', 80, "常用固定球阀口径"),
        ("NPS4", 4, "DN100", '4"', 100, "常用固定球阀口径"),
        ("NPS5", 5, "DN125", '5"', 125, "可选口径"),
        ("NPS6", 6, "DN150", '6"', 150, "常用固定球阀口径"),
        ("NPS8", 8, "DN200", '8"', 200, "常用固定球阀口径"),
        ("NPS10", 10, "DN250", '10"', 250, "常用固定球阀口径"),
        ("NPS12", 12, "DN300", '12"', 300, "常用固定球阀口径"),
        ("NPS14", 14, "DN350", '14"', 350, "常用固定球阀口径"),
        ("NPS16", 16, "DN400", '16"', 400, "常用固定球阀口径"),
        ("NPS18", 18, "DN450", '18"', 450, "常用固定球阀口径"),
        ("NPS20", 20, "DN500", '20"', 500, "常用固定球阀口径"),
        ("NPS22", 22, "DN550", '22"', 550, "常用固定球阀口径"),
        ("NPS24", 24, "DN600", '24"', 600, "常用固定球阀口径"),
    ]
    create_dataset(
        db,
        dictionary,
        "口径基础表",
        diameter_fields,
        [dict(zip([f[0] for f in diameter_fields], row)) for row in diameters],
    )

    pressure_fields = [
        ("PRESSURE_CLASS", "压力等级", "text", ""),
        ("CLASS_VALUE", "等级数值", "number", ""),
        ("COMMON_NAME", "常用写法", "text", ""),
        ("FIXED_BALL_APPLICABLE", "固定球阀适用性", "text", ""),
        ("RELATED_STANDARDS", "主要关联标准", "text", ""),
        ("DATA_STATUS", "数据状态", "text", ""),
        ("REMARK", "备注", "text", ""),
    ]
    pressure_rows = [
        ("CL150", 150, "150LB", "适用", "API 6D、ASME B16.34、ASME B16.5", "待授权录入", "压力温度额定值需按材料和温度查表"),
        ("CL300", 300, "300LB", "适用", "API 6D、ASME B16.34、ASME B16.5", "待授权录入", "压力温度额定值需按材料和温度查表"),
        ("CL600", 600, "600LB", "适用", "API 6D、ASME B16.34、ASME B16.5", "待授权录入", "压力温度额定值需按材料和温度查表"),
        ("CL900", 900, "900LB", "适用", "API 6D、ASME B16.34、ASME B16.5", "待授权录入", "压力温度额定值需按材料和温度查表"),
        ("CL1500", 1500, "1500LB", "适用", "API 6D、ASME B16.34、ASME B16.5", "待授权录入", "压力温度额定值需按材料和温度查表"),
        ("CL2500", 2500, "2500LB", "适用", "API 6D、ASME B16.34、ASME B16.5", "待授权录入", "高压固定球阀需重点校核阀杆和密封比压"),
    ]
    create_dataset(
        db,
        dictionary,
        "压力等级表",
        pressure_fields,
        [dict(zip([f[0] for f in pressure_fields], row)) for row in pressure_rows],
    )
    db.commit()

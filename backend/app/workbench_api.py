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
from .standard_registry import STANDARD_LINKS, STANDARD_REGISTRY
from .api6d_standard_data import API6D_TOP_MOUNTED_BALL_STRUCTURE

router = APIRouter(prefix="/api/workbench", tags=["workbench"])
RESULT_KB_CODE = "design_result"
RESULT_KB_NAME = "设计成果库"
RESULT_FIELDS = [("SECTION", "分类", "text"), ("PARAMETER", "参数", "text"), ("VALUE", "取值", "text"), ("UNIT", "单位", "text"), ("SOURCE", "来源", "text"), ("STATUS", "状态", "text")]
INPUT_LABELS = [("valve_structure", "阀门结构", "-"), ("nps", "公称口径", "-"), ("pressure_class", "压力等级", "-"), ("bore_type", "通径形式", "-"), ("end_connection", "端部连接", "-"), ("body_material", "阀体材料", "-"), ("ball_material_group", "球体材料组", "-"), ("seat_material", "阀座材料", "-"), ("design_pressure", "设计压力", "MPa"), ("design_temperature", "设计温度", "℃"), ("leakage_level", "泄漏等级", "-"), ("medium", "介质", "-")]


def ensure_result_library(db: Session) -> KnowledgeBase:
    kb = db.scalar(select(KnowledgeBase).where(KnowledgeBase.code == RESULT_KB_CODE))
    if kb: return kb
    kb = KnowledgeBase(name=RESULT_KB_NAME, code=RESULT_KB_CODE, type="result", description="保存参数工作台每一次生成的输入快照、几何参数、装配参数、来源与状态。", accent="blue", enabled=True)
    db.add(kb); db.flush(); return kb


def normalize_value(value):
    if value is None: return "-"
    text = str(value).strip(); return text if text else "-"


def safe_name_piece(value) -> str:
    text = normalize_value(value); text = re.sub(r'[\\/:*?"<>|]+', "-", text); text = re.sub(r"\s+", " ", text).strip(" .-")
    return (text or "未填写")[:48]


def result_row(section: str, parameter: str, value, unit: str = "-", source: str = "-", status: str = "已保存") -> dict:
    return {"SECTION": section, "PARAMETER": parameter, "VALUE": normalize_value(value), "UNIT": normalize_value(unit), "SOURCE": normalize_value(source), "STATUS": normalize_value(status)}


@router.post("/save")
def save_workbench_result(body: WorkbenchSaveRequest, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if not body.geometry_results and not body.assembly_results: raise HTTPException(status_code=400, detail="请先生成综合参数后再保存")
    kb = ensure_result_library(db); snapshot = body.input_snapshot or {}; now = datetime.now()
    nps = normalize_value(snapshot.get("nps")); pressure = normalize_value(snapshot.get("pressure_class")); leakage = normalize_value(snapshot.get("leakage_level"))
    timestamp = now.strftime("%Y%m%d-%H%M%S"); suffix = uuid.uuid4().hex[:4].upper()
    dataset_name = safe_name_piece(body.name) if body.name and body.name.strip() else f"固定球阀-{safe_name_piece(nps)}-{safe_name_piece(pressure)}-{safe_name_piece(leakage)}-{timestamp}-{suffix}"
    dataset = Dataset(knowledge_base_id=kb.id, name=dataset_name[:180], category="参数生成记录", standard_no=f"{nps} / {pressure} / {leakage}", source_file_name=f"参数生成工作台 · {user.display_name}", sheet_name=None, record_count=0, field_count=len(RESULT_FIELDS))
    db.add(dataset); db.flush()
    for order_no, (code, field_name, data_type) in enumerate(RESULT_FIELDS, start=1):
        db.add(DatasetField(dataset_id=dataset.id, source_name=field_name, field_code=code, field_name=field_name, data_type=data_type, unit=None, order_no=order_no, searchable=True, filterable=code in {"SECTION", "PARAMETER", "SOURCE", "STATUS"}))
    rows = [result_row("保存信息", "保存人", user.display_name, "-", "系统", "已保存"), result_row("保存信息", "保存时间", now.strftime("%Y-%m-%d %H:%M:%S"), "-", "系统", "已保存")]
    rows += [result_row("输入条件", label, snapshot.get(key), unit, "用户输入", "已保存") for key, label, unit in INPUT_LABELS]
    rows += [result_row("零件几何参数", item.name, item.value, item.unit or "-", item.source or "-", item.status or "待确认") for item in body.geometry_results]
    rows += [result_row("装配/接口参数", item.name, item.value, item.unit or "-", item.source or "-", item.status or "待确认") for item in body.assembly_results]
    db.bulk_save_objects([DatasetRecord(dataset_id=dataset.id, data=row) for row in rows]); dataset.record_count=len(rows); kb.updated_at=now; db.commit(); db.refresh(dataset)
    return {"ok":True,"knowledge_base_id":kb.id,"knowledge_base_name":kb.name,"dataset_id":dataset.id,"dataset_name":dataset.name,"record_count":dataset.record_count,"saved_at":now.strftime("%Y-%m-%d %H:%M:%S")}


def _result_rows(db: Session, dataset_id: int):
    rows = db.scalars(select(DatasetRecord).where(DatasetRecord.dataset_id == dataset_id).order_by(DatasetRecord.id.asc())).all(); return [r.data or {} for r in rows]


def _group_result(rows: list[dict]) -> dict:
    grouped={"保存信息":[],"输入条件":[],"零件几何参数":[],"装配/接口参数":[]}
    for row in rows:
        section=row.get("SECTION","其他"); grouped.setdefault(section,[]).append({"name":row.get("PARAMETER","-"),"value":row.get("VALUE","-"),"unit":row.get("UNIT","-"),"source":row.get("SOURCE","-"),"status":row.get("STATUS","-")})
    snapshot={x["name"]:x["value"] for x in grouped.get("输入条件",[])}; saved=grouped.get("保存信息",[]); saved_at=next((x["value"] for x in saved if x["name"]=="保存时间"),None)
    return {"snapshot":snapshot,"saved_at":saved_at,"geometry_results":grouped.get("零件几何参数",[]),"assembly_results":grouped.get("装配/接口参数",[]),"save_info":saved}


@router.get("/results")
def list_workbench_results(keyword: str="", nps: str="", pressure_class: str="", leakage_level: str="", sort: str="newest", db: Session=Depends(get_db)):
    kb=db.scalar(select(KnowledgeBase).where(KnowledgeBase.code==RESULT_KB_CODE))
    if not kb:return {"total":0,"rows":[]}
    datasets=db.scalars(select(Dataset).where(Dataset.knowledge_base_id==kb.id).order_by(Dataset.updated_at.desc())).all(); rows=[]
    for dataset in datasets:
        grouped=_group_result(_result_rows(db,dataset.id)); snapshot=grouped["snapshot"]; name=dataset.name or ""
        if keyword and keyword.lower() not in name.lower():continue
        if nps and nps.lower() not in str(snapshot.get("公称口径","")).lower():continue
        if pressure_class and pressure_class.lower() not in str(snapshot.get("压力等级","")).lower():continue
        if leakage_level and leakage_level.lower() not in str(snapshot.get("泄漏等级","")).lower():continue
        all_results=grouped["geometry_results"]+grouped["assembly_results"]; pending=sum(1 for x in all_results if not x["value"] or x["value"]=="-" or re.search(r"待|缺失|错误",f'{x["value"]} {x["status"]}'))
        rows.append({"id":dataset.id,"name":dataset.name,"nps":snapshot.get("公称口径","-"),"pressure_class":snapshot.get("压力等级","-"),"leakage_level":snapshot.get("泄漏等级","-"),"medium":snapshot.get("介质","-"),"design_pressure":snapshot.get("设计压力","-"),"design_temperature":snapshot.get("设计温度","-"),"saved_at":grouped["saved_at"] or dataset.updated_at.strftime("%Y-%m-%d %H:%M:%S"),"record_count":dataset.record_count,"geometry_count":len(grouped["geometry_results"]),"assembly_count":len(grouped["assembly_results"]),"pending_count":pending})
    if sort=="oldest":rows.sort(key=lambda x:x["saved_at"])
    elif sort=="nps":rows.sort(key=lambda x:x["nps"])
    elif sort=="pressure":rows.sort(key=lambda x:x["pressure_class"])
    return {"total":len(rows),"rows":rows}


@router.get("/results/{dataset_id}")
def workbench_result_detail(dataset_id:int,db:Session=Depends(get_db)):
    kb=db.scalar(select(KnowledgeBase).where(KnowledgeBase.code==RESULT_KB_CODE)); dataset=db.get(Dataset,dataset_id)
    if not kb or not dataset or dataset.knowledge_base_id!=kb.id:raise HTTPException(404,"设计成果不存在")
    grouped=_group_result(_result_rows(db,dataset_id)); return {"id":dataset.id,"name":dataset.name,"record_count":dataset.record_count,"saved_at":grouped["saved_at"] or dataset.updated_at.strftime("%Y-%m-%d %H:%M:%S"),**grouped}


def _standard_row(item:dict,index:int,link_count:int):return {**item,"id":index+1,"link_count":link_count}


def _api6d_virtual_link() -> dict:
    fields = [
        ("valve_type", "阀门类型", "-", "标准附录中的结构类型，用于区分球阀、闸阀等结构。"),
        ("structure_type", "结构形式", "-", "API 6D 附录B中的球阀结构示例；本组数据对应顶装固定式。"),
        ("bore_type", "通径形式", "-", "表C.2覆盖全径和缩径两类球阀结构长度。"),
        ("pressure_class_group", "压力等级组", "-", "表C.2按Class 150/300与Class 600/900分组。"),
        ("nps", "NPS", "in", "公称管径，作为结构长度查表键。"),
        ("dn", "DN", "mm", "与NPS对应的公称尺寸。"),
        ("face_type", "端面类型", "-", "突面A对应面-面结构长度。"),
        ("A_mm", "结构长度 A", "mm", "突面（面-面）结构长度，直接影响阀门安装空间。"),
        ("B_mm", "结构长度 B", "mm", "焊接端（端-端）结构长度。"),
        ("C_mm", "结构长度 C", "mm", "环接（端-端）结构长度。"),
        ("A_in", "结构长度 A", "in", "标准原始英制值。"),
        ("B_in", "结构长度 B", "in", "标准原始英制值。"),
        ("C_in", "结构长度 C", "in", "标准原始英制值。"),
        ("tolerance_mm", "结构长度公差", "mm", "NPS 12（DN 300）及以上采用±3.0 mm；更小尺寸采用±1.5 mm。"),
        ("source", "来源", "-", "用户提供的API 6D-2021中文版附录C表C.2。"),
    ]
    field_payload = [{"field_code": code, "field_name": name, "unit": unit, "description": desc} for code, name, unit, desc in fields]
    rows=[]
    for idx, item in enumerate(API6D_TOP_MOUNTED_BALL_STRUCTURE, start=1):
        rows.append({"_id": f"api6d-{idx}", **item})
    return {
        "virtual": True,
        "standard_code": "API 6D",
        "part_name": "球阀（顶装固定式）",
        "dataset_name": "API 6D-2021 附录C 表C.2 球阀结构长度",
        "applicability": "球阀 · 顶装固定式 · 全径/缩径 · Class 150/300/600/900",
        "data_status": "已录入（用户提供标准文件）",
        "note": "这里不是只展示“API 6D是什么”，而是把标准对应的零件、规格键和A/B/C实际尺寸直接展开。",
        "dataset_id": None,
        "dataset_exists": True,
        "source_document": "API 6D-2021 中文版 石油和天然气工业管线阀门",
        "fields": field_payload,
        "rows": rows,
    }


@router.get("/standards")
def list_standards(keyword:str="",system:str="",data_status:str="",sort:str="code",db:Session=Depends(get_db)):
    links_by_code={}
    for link in STANDARD_LINKS:links_by_code.setdefault(link["standard_code"],[]).append(link)
    links_by_code["API 6D"] = links_by_code.get("API 6D", []) + [{"virtual": True}]
    rows=[]
    for idx,item in enumerate(STANDARD_REGISTRY):
        if keyword and keyword.lower() not in f'{item["code"]} {item["title"]} {item["target_parts"]} {item["key_fields"]}'.lower():continue
        if system and item["system"]!=system:continue
        if data_status and item["data_status"]!=data_status:continue
        rows.append(_standard_row(item,idx,len(links_by_code.get(item["code"],[]))))
    if sort=="system":rows.sort(key=lambda x:(x["system"],x["code"]))
    elif sort=="status":
        order={"已录入":0,"部分":1,"待核验":2,"待确认":3,"待授权":4,"待导入":5}; rows.sort(key=lambda x:(order.get(x["data_status"],9),x["code"]))
    else:rows.sort(key=lambda x:x["code"])
    return {"total":len(rows),"systems":sorted({x["system"] for x in STANDARD_REGISTRY}),"statuses":sorted({x["data_status"] for x in STANDARD_REGISTRY}),"rows":rows}


@router.get("/standards/{standard_id}")
def standard_detail(standard_id:int,db:Session=Depends(get_db)):
    if standard_id<1 or standard_id>len(STANDARD_REGISTRY):raise HTTPException(404,"标准不存在")
    item=STANDARD_REGISTRY[standard_id-1]
    links=[_api6d_virtual_link()] if item["code"] == "API 6D" else [x for x in STANDARD_LINKS if x["standard_code"]==item["code"]]
    link_payload=[]
    for link in links:
        if link.get("virtual"):
            link_payload.append(link); continue
        dataset=db.scalar(select(Dataset).where(Dataset.name==link["dataset_name"]).order_by(Dataset.updated_at.desc()))
        payload={**link,"dataset_id":dataset.id if dataset else None,"dataset_exists":bool(dataset),"fields":[],"rows":[]}
        if dataset:
            fields=db.scalars(select(DatasetField).where(DatasetField.dataset_id==dataset.id).order_by(DatasetField.order_no)).all(); selected=[f for f in fields if f.field_name in link["field_names"] or f.source_name in link["field_names"]]
            payload["fields"]= [{"field_code":f.field_code,"field_name":f.field_name,"unit":f.unit,"description":getattr(f,"description",None) or f"字段“{f.field_name}”用于该参数表的规格查询、计算或校核。"} for f in selected]
            records=db.scalars(select(DatasetRecord).where(DatasetRecord.dataset_id==dataset.id).order_by(DatasetRecord.id.asc()).limit(80)).all(); codes=[f.field_code for f in selected]; payload["rows"]=[{"_id":r.id,**{code:(r.data or {}).get(code) for code in codes}} for r in records]
        else:
            payload["fields"]= [{"field_code":re.sub(r"[^A-Za-z0-9]+","_",name).strip("_").upper() or f"FIELD_{idx:02d}","field_name":name,"unit":"","description":f"规范字段“{name}”用于{link['part_name']}的规格定义、查询、计算或校核；正式数值需要导入对应标准数据。"} for idx,name in enumerate(link["field_names"],start=1)]
        link_payload.append(payload)
    return {**item,"id":standard_id,"links":link_payload,"linked_dataset_count":sum(1 for x in link_payload if x.get("dataset_exists"))}

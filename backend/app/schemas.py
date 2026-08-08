from typing import Any
from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str
    code: str
    type: str = "parameter"
    description: str | None = None
    accent: str = "blue"


class FieldMapping(BaseModel):
    source_name: str
    field_name: str
    field_code: str
    data_type: str = "text"
    unit: str | None = None
    searchable: bool = True
    filterable: bool = True
    enabled: bool = True


class ImportPreviewRequest(BaseModel):
    sheet_name: str
    # -2 = 自动识别，-1 = 无表头，>=0 = 指定 0-based 表头行
    header_row: int = Field(default=-2, ge=-2)


class ImportCommitRequest(BaseModel):
    knowledge_base_id: int
    dataset_name: str
    category: str | None = None
    standard_no: str | None = None
    sheet_name: str
    # 正式导入只接收已确认结果：-1 = 无表头，>=0 = 指定表头
    header_row: int = Field(ge=-1)
    mappings: list[FieldMapping]


class DatasetQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    search: str | None = None
    filters: dict[str, Any] = {}
    sort_by: str | None = None
    sort_order: str = "asc"


class RecordUpdate(BaseModel):
    data: dict[str, Any]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)

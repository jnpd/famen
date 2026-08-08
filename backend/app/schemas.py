from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


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
    header_mode: Literal["auto", "row", "none"] = "auto"
    header_row: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_header_row(self):
        if self.header_mode == "row" and self.header_row is None:
            raise ValueError("手动指定表头时必须填写表头行")
        return self


class ImportCommitRequest(BaseModel):
    knowledge_base_id: int
    dataset_name: str
    category: str | None = None
    standard_no: str | None = None
    sheet_name: str
    header_mode: Literal["auto", "row", "none"] = "row"
    header_row: int | None = Field(default=None, ge=0)
    mappings: list[FieldMapping]

    @model_validator(mode="after")
    def validate_header_row(self):
        if self.header_mode == "row" and self.header_row is None:
            raise ValueError("手动指定表头时必须填写表头行")
        return self


class DatasetQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    search: str | None = None
    filters: dict[str, Any] = {}
    sort_by: str | None = None
    sort_order: str = "asc"


class RecordUpdate(BaseModel):
    data: dict[str, Any]

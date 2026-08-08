from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def now_local():
    return datetime.now()


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    accent: Mapped[str] = mapped_column(String(30), default="blue")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_local)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_local, onupdate=now_local)

    datasets = relationship("Dataset", back_populates="knowledge_base", cascade="all, delete-orphan")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    standard_no: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_file_name: Mapped[str | None] = mapped_column(String(260), nullable=True)
    sheet_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    field_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_local)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_local, onupdate=now_local)

    knowledge_base = relationship("KnowledgeBase", back_populates="datasets")
    fields = relationship("DatasetField", back_populates="dataset", cascade="all, delete-orphan", order_by="DatasetField.order_no")
    records = relationship("DatasetRecord", back_populates="dataset", cascade="all, delete-orphan")


class DatasetField(Base):
    __tablename__ = "dataset_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    source_name: Mapped[str] = mapped_column(String(180), nullable=False)
    field_code: Mapped[str] = mapped_column(String(100), nullable=False)
    field_name: Mapped[str] = mapped_column(String(180), nullable=False)
    data_type: Mapped[str] = mapped_column(String(30), default="text")
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    order_no: Mapped[int] = mapped_column(Integer, default=0)
    searchable: Mapped[bool] = mapped_column(Boolean, default=True)
    filterable: Mapped[bool] = mapped_column(Boolean, default=True)

    dataset = relationship("Dataset", back_populates="fields")


class DatasetRecord(Base):
    __tablename__ = "dataset_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_local)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_local, onupdate=now_local)

    dataset = relationship("Dataset", back_populates="records")


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(260), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="UPLOADED", index=True)
    sheet_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    header_row: Mapped[int] = mapped_column(Integer, default=0)
    preview_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    success_rows: Mapped[int] = mapped_column(Integer, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_local)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_local, onupdate=now_local)

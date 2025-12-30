from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CamelCaseModel(BaseModel):
    """Base model that serializes to camelCase."""
    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class LogType(str, Enum):
    INFO = "info"
    TOOL = "tool"
    TEXT = "text"
    ERROR = "error"
    RESULT = "result"


class ExecutionStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class ExecutionLog(BaseModel):
    timestamp: str
    type: LogType
    content: str


class ExecutionRecord(CamelCaseModel):
    card_id: str = Field(alias="cardId")
    title: Optional[str] = None
    started_at: str = Field(alias="startedAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    status: ExecutionStatus
    logs: list[ExecutionLog] = []
    result: Optional[str] = None


class PlanResult(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    logs: list[ExecutionLog] = []
    spec_path: Optional[str] = None  # Caminho do arquivo de spec gerado


class ExecutePlanRequest(CamelCaseModel):
    card_id: str = Field(alias="cardId")
    title: str
    description: Optional[str] = None
    model: Optional[str] = "opus-4.5"


class HealthResponse(BaseModel):
    status: str
    timestamp: str


class LogsResponse(BaseModel):
    success: bool
    execution: Optional[ExecutionRecord] = None
    error: Optional[str] = None


class ExecutionsResponse(BaseModel):
    success: bool
    executions: list[ExecutionRecord]


class ExecutePlanResponse(CamelCaseModel):
    success: bool
    card_id: str = Field(alias="cardId")
    result: Optional[str] = None
    error: Optional[str] = None
    logs: list[ExecutionLog] = []
    spec_path: Optional[str] = Field(default=None, alias="specPath")


class ExecuteImplementRequest(CamelCaseModel):
    card_id: str = Field(alias="cardId")
    spec_path: str = Field(alias="specPath")
    model: Optional[str] = "opus-4.5"


class ExecuteImplementResponse(CamelCaseModel):
    success: bool
    card_id: str = Field(alias="cardId")
    result: Optional[str] = None
    error: Optional[str] = None
    logs: list[ExecutionLog] = []


class ExecuteTestRequest(CamelCaseModel):
    card_id: str = Field(alias="cardId")
    spec_path: str = Field(alias="specPath")
    model: Optional[str] = "opus-4.5"


class ExecuteTestResponse(CamelCaseModel):
    success: bool
    card_id: str = Field(alias="cardId")
    result: Optional[str] = None
    error: Optional[str] = None
    logs: list[ExecutionLog] = []


class ExecuteReviewRequest(CamelCaseModel):
    card_id: str = Field(alias="cardId")
    spec_path: str = Field(alias="specPath")
    model: Optional[str] = "opus-4.5"


class ExecuteReviewResponse(CamelCaseModel):
    success: bool
    card_id: str = Field(alias="cardId")
    result: Optional[str] = None
    error: Optional[str] = None
    logs: list[ExecutionLog] = []

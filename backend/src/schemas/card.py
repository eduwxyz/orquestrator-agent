"""Card schemas for API requests and responses."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ColumnId = Literal["backlog", "plan", "in-progress", "test", "review", "done", "archived", "cancelado"]
ModelType = Literal["opus-4.5", "sonnet-4.5", "haiku-4.5"]


class ActiveExecution(BaseModel):
    """Schema for active execution info."""
    id: str
    status: str
    command: Optional[str] = None
    startedAt: Optional[str] = Field(None, alias="startedAt")
    completedAt: Optional[str] = Field(None, alias="completedAt")

    class Config:
        populate_by_name = True


class CardImage(BaseModel):
    """Schema for card image."""
    id: str
    filename: str
    path: str
    uploadedAt: str


class CardBase(BaseModel):
    """Base card schema with common fields."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    model_plan: ModelType = "opus-4.5"
    model_implement: ModelType = "opus-4.5"
    model_test: ModelType = "opus-4.5"
    model_review: ModelType = "opus-4.5"
    images: Optional[List[CardImage]] = None


class CardCreate(CardBase):
    """Schema for creating a new card."""

    pass


class CardUpdate(BaseModel):
    """Schema for updating an existing card."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    column_id: Optional[ColumnId] = Field(None, alias="columnId")
    spec_path: Optional[str] = Field(None, alias="specPath")
    images: Optional[List[CardImage]] = None
    archived: Optional[bool] = None

    class Config:
        populate_by_name = True


class CardMove(BaseModel):
    """Schema for moving a card to another column."""

    column_id: ColumnId = Field(..., alias="columnId")

    class Config:
        populate_by_name = True


class CardResponse(BaseModel):
    """Schema for card response."""

    id: str
    title: str
    description: Optional[str] = None
    column_id: ColumnId = Field(..., alias="columnId")
    spec_path: Optional[str] = Field(None, alias="specPath")
    model_plan: str = Field(..., alias="modelPlan")
    model_implement: str = Field(..., alias="modelImplement")
    model_test: str = Field(..., alias="modelTest")
    model_review: str = Field(..., alias="modelReview")
    images: Optional[List[CardImage]] = None
    archived: bool = False
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    activeExecution: Optional[ActiveExecution] = Field(None, alias="activeExecution")

    class Config:
        populate_by_name = True
        from_attributes = True




class CardsListResponse(BaseModel):
    """Schema for list of cards response."""

    success: bool = True
    cards: list[CardResponse]


class CardSingleResponse(BaseModel):
    """Schema for single card response."""

    success: bool = True
    card: CardResponse


class CardDeleteResponse(BaseModel):
    """Schema for delete response."""

    success: bool = True
    message: str = "Card deleted successfully"

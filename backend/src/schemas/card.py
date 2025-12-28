"""Card schemas for API requests and responses."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ColumnId = Literal["backlog", "plan", "in-progress", "test", "review", "done"]


class CardBase(BaseModel):
    """Base card schema with common fields."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class CardCreate(CardBase):
    """Schema for creating a new card."""

    pass


class CardUpdate(BaseModel):
    """Schema for updating an existing card."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    column_id: Optional[ColumnId] = Field(None, alias="columnId")
    spec_path: Optional[str] = Field(None, alias="specPath")
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
    archived: bool = False
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class CardArchive(BaseModel):
    """Schema for archiving/unarchiving a card."""

    archived: bool


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

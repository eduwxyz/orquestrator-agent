"""Card schemas for API requests and responses."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DiffStats(BaseModel):
    """Schema for diff statistics."""
    files_added: List[str] = []
    files_modified: List[str] = []
    files_removed: List[str] = []
    lines_added: int = 0
    lines_removed: int = 0
    total_changes: int = 0
    captured_at: Optional[str] = None
    branch_name: Optional[str] = None


ColumnId = Literal["backlog", "plan", "implement", "test", "review", "done", "archived", "cancelado"]
ModelType = Literal[
    "opus-4.5", "sonnet-4.5", "haiku-4.5",  # Claude models
    "gemini-3-pro", "gemini-3-flash"  # Gemini models
]
MergeStatus = Literal["none", "merging", "resolving", "merged", "failed"]


class ActiveExecution(BaseModel):
    """Schema for active execution info."""
    id: str
    status: str
    command: Optional[str] = None
    startedAt: Optional[str] = Field(None, alias="startedAt")
    completedAt: Optional[str] = Field(None, alias="completedAt")
    workflowStage: Optional[str] = Field(None, alias="workflowStage")
    workflowError: Optional[str] = Field(None, alias="workflowError")

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
    model_plan: ModelType = Field(default="opus-4.5", alias="modelPlan")
    model_implement: ModelType = Field(default="opus-4.5", alias="modelImplement")
    model_test: ModelType = Field(default="opus-4.5", alias="modelTest")
    model_review: ModelType = Field(default="opus-4.5", alias="modelReview")
    images: Optional[List[CardImage]] = None

    class Config:
        populate_by_name = True


class CardCreate(CardBase):
    """Schema for creating a new card."""

    parent_card_id: Optional[str] = Field(None, alias="parentCardId")
    is_fix_card: bool = Field(False, alias="isFixCard")
    test_error_context: Optional[str] = Field(None, alias="testErrorContext")
    base_branch: Optional[str] = Field(None, alias="baseBranch")  # Branch base para o worktree

    class Config:
        populate_by_name = True


class CardUpdate(BaseModel):
    """Schema for updating an existing card."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    column_id: Optional[ColumnId] = Field(None, alias="columnId")
    spec_path: Optional[str] = Field(None, alias="specPath")
    images: Optional[List[CardImage]] = None
    archived: Optional[bool] = None
    # Campos para worktree isolation
    branch_name: Optional[str] = Field(None, alias="branchName")
    worktree_path: Optional[str] = Field(None, alias="worktreePath")
    # Campos para diff visualization
    diff_stats: Optional[DiffStats] = Field(None, alias="diffStats")

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
    parent_card_id: Optional[str] = Field(None, alias="parentCardId")
    is_fix_card: bool = Field(False, alias="isFixCard")
    test_error_context: Optional[str] = Field(None, alias="testErrorContext")
    # Campos para worktree isolation
    branch_name: Optional[str] = Field(None, alias="branchName")
    worktree_path: Optional[str] = Field(None, alias="worktreePath")
    base_branch: Optional[str] = Field(None, alias="baseBranch")
    # Campos para diff visualization
    diff_stats: Optional[DiffStats] = Field(None, alias="diffStats")

    @property
    def is_finalized(self) -> bool:
        """Check if card is in a finalized state."""
        return self.column_id in ['done', 'archived', 'cancelado']

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

"""Tests for Card Repository."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from src.database import Base
from src.models.card import Card
from src.repositories.card_repository import CardRepository
from src.schemas.card import CardCreate
import json


@pytest_asyncio.fixture
async def async_session():
    """Create an async test database session."""
    # Create in-memory SQLite database for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
class TestCardRepository:
    """Test suite for CardRepository."""

    async def test_create_regular_card(self, async_session):
        """Test creating a regular card."""
        repo = CardRepository(async_session)

        card_data = CardCreate(
            title="Test Card",
            description="Test Description",
            model_plan="opus-4.5",
            model_implement="sonnet-4.5",
            model_test="haiku-4.5",
            model_review="opus-4.5"
        )

        card = await repo.create(card_data)
        await async_session.commit()

        assert card.id is not None
        assert card.title == "Test Card"
        assert card.description == "Test Description"
        assert card.column_id == "backlog"
        assert card.is_fix_card == False
        assert card.parent_card_id is None

    async def test_create_fix_card(self, async_session):
        """Test creating a fix card."""
        repo = CardRepository(async_session)

        # Create parent card first
        parent_data = CardCreate(
            title="Parent Card",
            description="Parent Description",
            model_plan="opus-4.5",
            model_implement="opus-4.5",
            model_test="opus-4.5",
            model_review="opus-4.5"
        )

        parent_card = await repo.create(parent_data)
        await async_session.commit()

        # Create fix card
        fix_data = CardCreate(
            title="[FIX] Parent Card",
            description="Fix for test failures",
            model_plan="opus-4.5",
            model_implement="opus-4.5",
            model_test="opus-4.5",
            model_review="opus-4.5",
            parent_card_id=parent_card.id,
            is_fix_card=True,
            test_error_context='{"error_type": "test_failure"}'
        )

        fix_card = await repo.create(fix_data)
        await async_session.commit()

        assert fix_card.parent_card_id == parent_card.id
        assert fix_card.is_fix_card == True
        assert fix_card.test_error_context == '{"error_type": "test_failure"}'

    async def test_get_active_fix_card(self, async_session):
        """Test getting active fix card for a parent card."""
        repo = CardRepository(async_session)

        # Create parent card
        parent_data = CardCreate(
            title="Parent Card",
            description="Parent Description",
            model_plan="opus-4.5",
            model_implement="opus-4.5",
            model_test="opus-4.5",
            model_review="opus-4.5"
        )

        parent_card = await repo.create(parent_data)
        await async_session.commit()

        # No fix card should exist initially
        fix_card = await repo.get_active_fix_card(parent_card.id)
        assert fix_card is None

        # Create active fix card
        fix_data = CardCreate(
            title="[FIX] Parent Card",
            description="Fix for test failures",
            model_plan="opus-4.5",
            model_implement="opus-4.5",
            model_test="opus-4.5",
            model_review="opus-4.5",
            parent_card_id=parent_card.id,
            is_fix_card=True
        )

        created_fix = await repo.create(fix_data)
        await async_session.commit()

        # Should find the active fix card
        active_fix = await repo.get_active_fix_card(parent_card.id)
        assert active_fix is not None
        assert active_fix.id == created_fix.id

    async def test_create_fix_card_with_existing_active(self, async_session):
        """Test that creating a fix card when one exists returns the existing one."""
        repo = CardRepository(async_session)

        # Create parent card
        parent_data = CardCreate(
            title="Parent Card",
            description="Parent Description",
            model_plan="opus-4.5",
            model_implement="opus-4.5",
            model_test="opus-4.5",
            model_review="opus-4.5"
        )

        parent_card = await repo.create(parent_data)
        await async_session.commit()

        # Create first fix card
        error_info1 = {
            "description": "First error",
            "context": '{"error": "first"}'
        }

        fix_card1 = await repo.create_fix_card(parent_card.id, error_info1)
        await async_session.commit()

        # Try to create another fix card
        error_info2 = {
            "description": "Second error",
            "context": '{"error": "second"}'
        }

        fix_card2 = await repo.create_fix_card(parent_card.id, error_info2)

        # Should return the existing fix card
        assert fix_card2.id == fix_card1.id

    async def test_create_fix_card_copies_parent_config(self, async_session):
        """Test that fix card inherits model configuration from parent."""
        repo = CardRepository(async_session)

        # Create parent card with specific model configuration
        parent_data = CardCreate(
            title="Parent Card",
            description="Parent Description",
            model_plan="sonnet-4.5",
            model_implement="haiku-4.5",
            model_test="opus-4.5",
            model_review="sonnet-4.5"
        )

        parent_card = await repo.create(parent_data)
        await async_session.commit()

        # Create fix card
        error_info = {
            "description": "Test failure",
            "context": '{"error_type": "test"}'
        }

        fix_card = await repo.create_fix_card(parent_card.id, error_info)
        await async_session.commit()

        # Fix card should have same model configuration as parent
        assert fix_card.model_plan == parent_card.model_plan
        assert fix_card.model_implement == parent_card.model_implement
        assert fix_card.model_test == parent_card.model_test
        assert fix_card.model_review == parent_card.model_review

    async def test_get_all_cards(self, async_session):
        """Test getting all cards including fix cards."""
        repo = CardRepository(async_session)

        # Create multiple cards
        for i in range(3):
            card_data = CardCreate(
                title=f"Card {i}",
                description=f"Description {i}",
                model_plan="opus-4.5",
                model_implement="opus-4.5",
                model_test="opus-4.5",
                model_review="opus-4.5"
            )
            await repo.create(card_data)

        await async_session.commit()

        # Get all cards
        all_cards = await repo.get_all()

        assert len(all_cards) == 3
        assert all(card.title.startswith("Card") for card in all_cards)

    async def test_update_card_preserves_fix_fields(self, async_session):
        """Test that updating a card preserves fix-related fields."""
        repo = CardRepository(async_session)

        # Create parent card
        parent_data = CardCreate(
            title="Parent Card",
            description="Parent Description",
            model_plan="opus-4.5",
            model_implement="opus-4.5",
            model_test="opus-4.5",
            model_review="opus-4.5"
        )

        parent_card = await repo.create(parent_data)
        await async_session.commit()

        # Create fix card
        fix_data = CardCreate(
            title="[FIX] Parent Card",
            description="Fix for test failures",
            model_plan="opus-4.5",
            model_implement="opus-4.5",
            model_test="opus-4.5",
            model_review="opus-4.5",
            parent_card_id=parent_card.id,
            is_fix_card=True,
            test_error_context='{"error_type": "test_failure"}'
        )

        fix_card = await repo.create(fix_data)
        await async_session.commit()

        # Update the fix card
        from src.schemas.card import CardUpdate
        update_data = CardUpdate(
            title="[FIX] Updated Title",
            description="Updated description"
        )

        updated_card = await repo.update(fix_card.id, update_data)
        await async_session.commit()

        # Fix fields should be preserved
        assert updated_card.parent_card_id == parent_card.id
        assert updated_card.is_fix_card == True
        assert updated_card.test_error_context == '{"error_type": "test_failure"}'
        # Updated fields should change
        assert updated_card.title == "[FIX] Updated Title"
        assert updated_card.description == "Updated description"
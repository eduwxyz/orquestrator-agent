"""Routes for managing card images."""

import uuid
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import async_session_maker
from ..models.card import Card as CardModel

router = APIRouter(prefix="/api/images", tags=["images"])

# Create temp directory for images
TEMP_DIR = Path("/tmp/kanban-images")
TEMP_DIR.mkdir(exist_ok=True)

# Allowed image extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_image(file: UploadFile) -> None:
    """Validate uploaded image file."""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check content type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )


@router.post("/upload")
async def upload_image(
    image: UploadFile = File(...),
    cardId: str = Form(...),
):
    """Upload an image for a card."""
    # Validate image
    validate_image(image)

    async with async_session_maker() as db:
        # Check if card exists
        result = await db.execute(select(CardModel).where(CardModel.id == cardId))
        card = result.scalar_one_or_none()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        # Generate unique filename
        file_ext = Path(image.filename).suffix.lower()
        unique_filename = f"{cardId}_{uuid.uuid4()}{file_ext}"
        file_path = TEMP_DIR / unique_filename

        # Save file
        try:
            # Read file in chunks to handle large files
            with file_path.open("wb") as buffer:
                while chunk := await image.read(8192):  # 8KB chunks
                    # Check total size
                    if buffer.tell() + len(chunk) > MAX_FILE_SIZE:
                        buffer.close()
                        file_path.unlink()  # Remove partial file
                        raise HTTPException(
                            status_code=413,
                            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024}MB"
                        )
                    buffer.write(chunk)
        except HTTPException:
            raise
        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")

        # Create image metadata
        image_data = {
            "id": str(uuid.uuid4()),
            "filename": image.filename,
            "path": str(file_path),
            "uploadedAt": datetime.utcnow().isoformat()
        }

        # Update card with new image
        current_images = card.images or []
        current_images.append(image_data)
        card.images = current_images
        await db.commit()

        return image_data


@router.get("/{image_id}")
async def get_image(image_id: str):
    """Get an image by ID."""
    async with async_session_maker() as db:
        # Find the image in any card
        result = await db.execute(select(CardModel).where(CardModel.images.isnot(None)))
        cards = result.scalars().all()

        image_path = None
        for card in cards:
            if card.images:
                for img in card.images:
                    if img.get("id") == image_id:
                        image_path = img.get("path")
                        break
            if image_path:
                break

        if not image_path:
            raise HTTPException(status_code=404, detail="Image not found")

        # Check if file exists
        file_path = Path(image_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Image file not found")

        # Determine content type
        content_type = "image/jpeg"  # default
        if file_path.suffix.lower() == ".png":
            content_type = "image/png"
        elif file_path.suffix.lower() == ".gif":
            content_type = "image/gif"
        elif file_path.suffix.lower() == ".webp":
            content_type = "image/webp"
        elif file_path.suffix.lower() == ".svg":
            content_type = "image/svg+xml"

        return FileResponse(file_path, media_type=content_type)


@router.delete("/{image_id}")
async def delete_image(image_id: str):
    """Delete an image by ID."""
    async with async_session_maker() as db:
        # Find the card with this image
        result = await db.execute(select(CardModel).where(CardModel.images.isnot(None)))
        cards = result.scalars().all()

        card_found = None
        image_found = None
        for card in cards:
            if card.images:
                for img in card.images:
                    if img.get("id") == image_id:
                        card_found = card
                        image_found = img
                        break
            if card_found:
                break

        if not card_found or not image_found:
            raise HTTPException(status_code=404, detail="Image not found")

        # Delete physical file
        image_path = Path(image_found.get("path"))
        if image_path.exists():
            try:
                image_path.unlink()
            except Exception as e:
                print(f"Failed to delete image file: {e}")

        # Remove from card
        card_found.images = [img for img in card_found.images if img.get("id") != image_id]
        await db.commit()

        return {"success": True, "message": "Image deleted successfully"}


@router.post("/cleanup")
async def cleanup_old_images():
    """Clean up old images from temp directory (older than 7 days)."""
    import time

    now = time.time()
    cutoff = now - (7 * 24 * 60 * 60)  # 7 days ago

    cleaned = 0
    for file_path in TEMP_DIR.glob("*"):
        if file_path.is_file():
            if file_path.stat().st_mtime < cutoff:
                try:
                    file_path.unlink()
                    cleaned += 1
                except Exception as e:
                    print(f"Failed to delete old image {file_path}: {e}")

    return {"success": True, "cleaned": cleaned}
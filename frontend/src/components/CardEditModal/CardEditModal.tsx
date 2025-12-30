import { useState, useEffect, useRef } from 'react';
import { Card, CardImage } from '../../types';
import {
  uploadImage,
  handlePasteImage,
  validateImageFile,
  createImagePreview
} from '../../utils/imageHandler';
import styles from './CardEditModal.module.css';

interface CardEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  card: Card;
  onUpdateCard: (card: Card) => void;
}

export function CardEditModal({ isOpen, onClose, card, onUpdateCard }: CardEditModalProps) {
  const [localCard, setLocalCard] = useState(card);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [previewImages, setPreviewImages] = useState<{ file: File; preview: string }[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Reset state when card changes
  useEffect(() => {
    setLocalCard(card);
    setPreviewImages([]);
    setUploadError(null);
  }, [card]);

  // Handle paste events
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      if (!isOpen) return;

      const imageFile = handlePasteImage(e);
      if (imageFile) {
        handleImageFile(imageFile);
      }
    };

    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  const handleImageFile = async (file: File) => {
    const validation = validateImageFile(file);
    if (!validation.valid) {
      setUploadError(validation.error || 'Invalid file');
      return;
    }

    try {
      const preview = await createImagePreview(file);
      setPreviewImages(prev => [...prev, { file, preview }]);
      setUploadError(null);
    } catch (error) {
      setUploadError('Failed to preview image');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    Array.from(files).forEach(handleImageFile);
  };

  const uploadPendingImages = async () => {
    if (previewImages.length === 0) return;

    setUploading(true);
    setUploadError(null);

    try {
      const uploadedImages: CardImage[] = [];

      for (const { file } of previewImages) {
        const image = await uploadImage(file, card.id);
        uploadedImages.push(image);
      }

      const updatedCard = {
        ...localCard,
        images: [...(localCard.images || []), ...uploadedImages]
      };

      setLocalCard(updatedCard);
      onUpdateCard(updatedCard);
      setPreviewImages([]);
    } catch (error) {
      setUploadError('Failed to upload images');
    } finally {
      setUploading(false);
    }
  };

  const removePreviewImage = (index: number) => {
    setPreviewImages(prev => prev.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    await uploadPendingImages();
    onUpdateCard(localCard);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        ref={modalRef}
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.header}>
          <h2 className={styles.title}>Edit Card</h2>
          <button className={styles.closeButton} onClick={onClose}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M1 1l12 12M13 1L1 13" />
            </svg>
          </button>
        </div>

        <div className={styles.content}>
          <div className={styles.field}>
            <label>Title</label>
            <input
              type="text"
              value={localCard.title}
              onChange={(e) => setLocalCard({ ...localCard, title: e.target.value })}
              className={styles.input}
            />
          </div>

          <div className={styles.field}>
            <label>Description</label>
            <textarea
              value={localCard.description}
              onChange={(e) => setLocalCard({ ...localCard, description: e.target.value })}
              className={styles.textarea}
              rows={3}
            />
          </div>

          <div className={styles.field}>
            <label>Images</label>
            <div className={styles.imageSection}>
              {/* Existing images */}
              {localCard.images && localCard.images.length > 0 && (
                <div className={styles.existingImages}>
                  <h4>Current Images</h4>
                  <div className={styles.imageGrid}>
                    {localCard.images.map(image => (
                      <div key={image.id} className={styles.imageThumb}>
                        <img src={`http://localhost:3001/api/images/${image.id}`} alt={image.filename} />
                        <span className={styles.imageFilename}>{image.filename}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Preview images */}
              {previewImages.length > 0 && (
                <div className={styles.previewImages}>
                  <h4>New Images (not uploaded yet)</h4>
                  <div className={styles.imageGrid}>
                    {previewImages.map((image, index) => (
                      <div key={index} className={styles.imageThumb}>
                        <img src={image.preview} alt={image.file.name} />
                        <span className={styles.imageFilename}>{image.file.name}</span>
                        <button
                          className={styles.removeButton}
                          onClick={() => removePreviewImage(index)}
                          title="Remove image"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Upload controls */}
              <div className={styles.uploadControls}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleFileSelect}
                  className={styles.fileInput}
                  id="image-upload"
                />
                <label htmlFor="image-upload" className={styles.uploadButton}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M2 10v3a1 1 0 001 1h10a1 1 0 001-1v-3M8 2v8M5 5l3-3 3 3" />
                  </svg>
                  Choose Files
                </label>
                <span className={styles.uploadHint}>
                  or paste images (Ctrl/Cmd + V)
                </span>
              </div>

              {uploadError && (
                <div className={styles.error}>{uploadError}</div>
              )}
            </div>
          </div>
        </div>

        <div className={styles.footer}>
          <button
            className={styles.saveButton}
            onClick={handleSave}
            disabled={uploading}
          >
            {uploading ? 'Uploading...' : 'Save Changes'}
          </button>
          <button className={styles.cancelButton} onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
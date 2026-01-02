import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { ModelType, CardDraft } from '../../types';
import {
  validateImageFile,
  handlePasteImage,
  createImagePreview
} from '../../utils/imageHandler';
import { useDraft } from '../../hooks/useDraft';
import styles from './AddCardModal.module.css';

interface AddCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (cardData: {
    title: string;
    description: string;
    modelPlan: ModelType;
    modelImplement: ModelType;
    modelTest: ModelType;
    modelReview: ModelType;
    images: File[];
  }) => Promise<void>;
}

interface ModelCardData {
  value: ModelType;
  label: string;
  tagline: string;
  performance: string;
  icon: string;
  accent: string;
}

const MODEL_CARDS: ModelCardData[] = [
  {
    value: 'opus-4.5',
    label: 'Opus 4.5',
    tagline: 'Maximum intelligence',
    performance: 'Highest Quality',
    icon: '◈',
    accent: 'opus'
  },
  {
    value: 'sonnet-4.5',
    label: 'Sonnet 4.5',
    tagline: 'Balanced performance',
    performance: 'Fast & Smart',
    icon: '◉',
    accent: 'sonnet'
  },
  {
    value: 'haiku-4.5',
    label: 'Haiku 4.5',
    tagline: 'Lightning fast',
    performance: 'Rapid Response',
    icon: '◎',
    accent: 'haiku'
  }
];

const WORKFLOW_STAGES = [
  { key: 'modelPlan', label: 'Plan', icon: '⚡', description: 'Strategy & architecture' },
  { key: 'modelImplement', label: 'Implement', icon: '⚙', description: 'Code & build' },
  { key: 'modelTest', label: 'Test', icon: '✓', description: 'Validate & verify' },
  { key: 'modelReview', label: 'Review', icon: '◐', description: 'Polish & refine' }
];

export function AddCardModal({ isOpen, onClose, onSubmit }: AddCardModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [modelPlan, setModelPlan] = useState<ModelType>('opus-4.5');
  const [modelImplement, setModelImplement] = useState<ModelType>('opus-4.5');
  const [modelTest, setModelTest] = useState<ModelType>('opus-4.5');
  const [modelReview, setModelReview] = useState<ModelType>('opus-4.5');
  const [previewImages, setPreviewImages] = useState<Array<{
    id: string;
    file: File | null;
    preview: string;
  }>>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activeStage, setActiveStage] = useState<string | null>(null);

  const modalRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounter = useRef(0);
  const hasRestoredDraft = useRef(false);

  // Integrar hook de draft
  const {
    hasDraft,
    isDraftDirty,
    showDraftNotification,
    saveDraft,
    restoreDraft,
    discardDraft,
    clearDraft
  } = useDraft({
    enabled: isOpen,
    autoSaveDelay: 1000,
    onRestore: (draft: CardDraft) => {
      setTitle(draft.title);
      setDescription(draft.description);
      setModelPlan(draft.modelPlan);
      setModelImplement(draft.modelImplement);
      setModelTest(draft.modelTest);
      setModelReview(draft.modelReview);

      // Restaurar imagens (converter de DraftImage para preview format)
      const restoredImages = draft.previewImages.map(img => ({
        id: img.id,
        file: null, // File não pode ser serializado, será null
        preview: img.preview
      }));
      setPreviewImages(restoredImages);
      hasRestoredDraft.current = true;
    }
  });

  // Reset state when modal opens (only if not restoring draft)
  useEffect(() => {
    if (isOpen && !hasRestoredDraft.current) {
      // Só resetar se não houver draft para restaurar
      if (!showDraftNotification) {
        setTitle('');
        setDescription('');
        setModelPlan('opus-4.5');
        setModelImplement('opus-4.5');
        setModelTest('opus-4.5');
        setModelReview('opus-4.5');
        setPreviewImages([]);
        setUploadError(null);
        setActiveStage(null);
      }
    }
    if (!isOpen) {
      hasRestoredDraft.current = false;
    }
  }, [isOpen, showDraftNotification]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isSubmitting) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose, isSubmitting]);

  // Handle paste events
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      if (!isOpen) return;
      const file = handlePasteImage(e);
      if (file) {
        handleFileAdd(file);
      }
    };

    if (isOpen) {
      document.addEventListener('paste', handlePaste);
    }

    return () => {
      document.removeEventListener('paste', handlePaste);
    };
  }, [isOpen]);

  // Auto-save draft quando campos mudam
  useEffect(() => {
    if (!isOpen) return;

    const draftData: Partial<CardDraft> = {
      title,
      description,
      modelPlan,
      modelImplement,
      modelTest,
      modelReview,
      previewImages: previewImages.map(img => ({
        id: img.id,
        filename: img.file?.name || 'restored-image',
        preview: img.preview,
        size: img.file?.size || 0
      }))
    };

    saveDraft(draftData);
  }, [title, description, modelPlan, modelImplement, modelTest, modelReview, previewImages, isOpen, saveDraft]);

  const handleFileAdd = async (file: File) => {
    const validation = validateImageFile(file);
    if (!validation.valid) {
      setUploadError(validation.error || 'Invalid file');
      return;
    }

    try {
      const preview = await createImagePreview(file);
      const newImage = {
        id: crypto.randomUUID(),
        file,
        preview
      };
      setPreviewImages(prev => [...prev, newImage]);
      setUploadError(null);
    } catch (error) {
      console.error('Error creating preview:', error);
      setUploadError('Failed to preview image');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.forEach(handleFileAdd);
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    dragCounter.current = 0;

    const files = Array.from(e.dataTransfer.files);
    files.forEach(handleFileAdd);
  };

  const removePreview = (id: string) => {
    setPreviewImages(prev => prev.filter(img => img.id !== id));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        title: title.trim(),
        description: description.trim(),
        modelPlan,
        modelImplement,
        modelTest,
        modelReview,
        images: previewImages.filter(p => p.file !== null).map(p => p.file as File)
      });
      clearDraft(); // Limpar draft após sucesso
      onClose();
    } catch (error) {
      console.error('Error creating card:', error);
      setUploadError('Failed to create card');
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateModel = (stage: string, value: ModelType) => {
    switch (stage) {
      case 'modelPlan':
        setModelPlan(value);
        break;
      case 'modelImplement':
        setModelImplement(value);
        break;
      case 'modelTest':
        setModelTest(value);
        break;
      case 'modelReview':
        setModelReview(value);
        break;
    }
  };

  const getModelValue = (stage: string): ModelType => {
    switch (stage) {
      case 'modelPlan':
        return modelPlan;
      case 'modelImplement':
        return modelImplement;
      case 'modelTest':
        return modelTest;
      case 'modelReview':
        return modelReview;
      default:
        return 'opus-4.5';
    }
  };

  if (!isOpen) return null;

  const portalRoot = document.getElementById('modal-root');
  if (!portalRoot) {
    console.error('Modal root not found');
    return null;
  }

  return createPortal(
    <div className={styles.overlay} onClick={onClose}>
      <div
        ref={modalRef}
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {/* Decorative elements */}
        <div className={styles.modalGlow} />
        <div className={styles.modalNoise} />

        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerContent}>
            <div className={styles.titleGroup}>
              <span className={styles.titleIcon}>✦</span>
              <h2 className={styles.title}>Create New Card</h2>
              {isDraftDirty && (
                <div className={styles.autoSaveIndicator}>
                  <span className={styles.autoSaveIcon}>•</span>
                  <span className={styles.autoSaveText}>Saving...</span>
                </div>
              )}
            </div>
            <p className={styles.subtitle}>Transform your idea into actionable work</p>
          </div>
          <button
            className={`${styles.closeButton} ${hasDraft ? styles.closeButtonWithDraft : ''}`}
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Close modal"
          >
            <span className={styles.closeIcon}>✕</span>
          </button>
        </div>

        {/* Draft Notification */}
        {showDraftNotification && (
          <div className={styles.draftNotification}>
            <div className={styles.draftMessage}>
              <span className={styles.draftIcon}>💾</span>
              <span>A draft was found. Would you like to restore it?</span>
            </div>
            <div className={styles.draftActions}>
              <button
                type="button"
                onClick={restoreDraft}
                className={styles.draftRestoreBtn}
              >
                Restore
              </button>
              <button
                type="button"
                onClick={() => {
                  discardDraft();
                }}
                className={styles.draftDiscardBtn}
              >
                Discard
              </button>
            </div>
          </div>
        )}

        <form className={styles.form} onSubmit={handleSubmit}>
          {/* Title Input */}
          <div className={styles.formSection}>
            <div className={styles.inputGroup}>
              <label className={styles.inputLabel}>
                <span className={styles.labelText}>Title</span>
                <span className={styles.labelRequired}>*</span>
              </label>
              <input
                type="text"
                className={styles.titleInput}
                placeholder="Enter a compelling title..."
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                autoFocus
                disabled={isSubmitting}
                required
              />
              <div className={styles.inputGlow} />
            </div>
          </div>

          {/* Description */}
          <div className={styles.formSection}>
            <div className={styles.inputGroup}>
              <label className={styles.inputLabel}>
                <span className={styles.labelText}>Description</span>
                <span className={styles.labelOptional}>Optional</span>
              </label>
              <textarea
                className={styles.descriptionInput}
                placeholder="Describe the task, requirements, or context..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                disabled={isSubmitting}
              />
              <div className={styles.inputGlow} />
            </div>
          </div>

          {/* Model Selection */}
          <div className={styles.formSection}>
            <div className={styles.sectionHeader}>
              <h3 className={styles.sectionTitle}>AI Model Configuration</h3>
              <p className={styles.sectionDescription}>Choose models for each workflow stage</p>
            </div>

            <div className={styles.workflowStages}>
              {WORKFLOW_STAGES.map((stage) => (
                <div
                  key={stage.key}
                  className={`${styles.workflowStage} ${activeStage === stage.key ? styles.activeStage : ''}`}
                >
                  <div className={styles.stageHeader}>
                    <span className={styles.stageIcon}>{stage.icon}</span>
                    <div className={styles.stageInfo}>
                      <h4 className={styles.stageName}>{stage.label}</h4>
                      <p className={styles.stageDescription}>{stage.description}</p>
                    </div>
                  </div>

                  <div className={styles.modelCards}>
                    {MODEL_CARDS.map((model) => (
                      <button
                        key={model.value}
                        type="button"
                        className={`${styles.modelCard} ${styles[model.accent]} ${getModelValue(stage.key) === model.value ? styles.selected : ''}`}
                        onClick={() => {
                          updateModel(stage.key, model.value);
                          setActiveStage(stage.key);
                        }}
                        disabled={isSubmitting}
                      >
                        <span className={styles.modelIcon}>{model.icon}</span>
                        <span className={styles.modelName}>{model.label}</span>
                        <span className={styles.modelTagline}>{model.tagline}</span>
                        <span className={styles.modelPerformance}>{model.performance}</span>
                        <div className={styles.modelGlow} />
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Image Upload */}
          <div className={styles.formSection}>
            <div className={styles.sectionHeader}>
              <h3 className={styles.sectionTitle}>Attachments</h3>
              <p className={styles.sectionDescription}>Add images or screenshots</p>
            </div>

            <div
              className={`${styles.uploadArea} ${isDragging ? styles.dragging : ''}`}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*"
                onChange={handleFileSelect}
                disabled={isSubmitting}
                className={styles.hiddenInput}
              />

              <div className={styles.uploadContent}>
                <div className={styles.uploadIcon}>
                  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                    <path d="M24 32V16M24 16L18 22M24 16L30 22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M40 28V36C40 38.2091 38.2091 40 36 40H12C9.79086 40 8 38.2091 8 36V28" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </div>
                <p className={styles.uploadText}>
                  Drop images here or <span className={styles.uploadLink}>browse</span>
                </p>
                <p className={styles.uploadHint}>PNG, JPG, GIF up to 10MB • Paste with ⌘V</p>
              </div>
              <div className={styles.uploadBorder} />
            </div>

            {uploadError && (
              <div className={styles.errorMessage}>
                <span className={styles.errorIcon}>⚠</span>
                {uploadError}
              </div>
            )}

            {previewImages.length > 0 && (
              <div className={styles.previewGrid}>
                {previewImages.map((img) => (
                  <div key={img.id} className={styles.previewItem}>
                    <img src={img.preview} alt={img.file?.name || 'Restored image'} />
                    <div className={styles.previewOverlay}>
                      <span className={styles.previewName}>{img.file?.name || 'Restored image'}</span>
                      <button
                        type="button"
                        className={styles.previewRemove}
                        onClick={(e) => {
                          e.stopPropagation();
                          removePreview(img.id);
                        }}
                        disabled={isSubmitting}
                      >
                        <span>✕</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.cancelButton}
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={styles.submitButton}
              disabled={!title.trim() || isSubmitting}
            >
              <span className={styles.submitText}>
                {isSubmitting ? 'Creating...' : 'Create Card'}
              </span>
              <span className={styles.submitIcon}>→</span>
            </button>
          </div>
        </form>
      </div>
    </div>,
    portalRoot
  );
}
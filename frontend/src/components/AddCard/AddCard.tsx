import { useState } from 'react';
import { ColumnId, ModelType } from '../../types';
import {
  uploadImage,
  validateImageFile,
  handlePasteImage,
  createImagePreview
} from '../../utils/imageHandler';
import * as cardsApi from '../../api/cards';
import styles from './AddCard.module.css';

interface AddCardProps {
  columnId: ColumnId;
  onAdd: (title: string, description: string, columnId: ColumnId) => void; // Mantido por compatibilidade
}

export function AddCard({ }: AddCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [modelPlan, setModelPlan] = useState<ModelType>('opus-4.5');
  const [modelImplement, setModelImplement] = useState<ModelType>('opus-4.5');
  const [modelTest, setModelTest] = useState<ModelType>('opus-4.5');
  const [modelReview, setModelReview] = useState<ModelType>('opus-4.5');
  const [previewImages, setPreviewImages] = useState<Array<{
    id: string;
    file: File;
    preview: string;
  }>>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const MODEL_OPTIONS: { value: ModelType; label: string }[] = [
    { value: 'opus-4.5', label: 'Opus 4.5' },
    { value: 'sonnet-4.5', label: 'Sonnet 4.5' },
    { value: 'haiku-4.5', label: 'Haiku 4.5' },
  ];

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);

    for (const file of files) {
      const validation = validateImageFile(file);
      if (!validation.valid) {
        setUploadError(validation.error || 'Invalid file');
        continue;
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
      }
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const file = handlePasteImage(e.nativeEvent);
    if (file) {
      handleFileSelect({ target: { files: [file] } } as any);
    }
  };

  const removePreview = (id: string) => {
    setPreviewImages(prev => prev.filter(img => img.id !== id));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setIsLoading(true);
    setUploadError(null);

    try {
      // Criar o card primeiro
      const newCard = await cardsApi.createCard(
        title.trim(),
        description.trim(),
        modelPlan,
        modelImplement,
        modelTest,
        modelReview
      );

      // Se houver imagens, fazer upload
      if (previewImages.length > 0) {
        setUploading(true);
        const uploadedImages = [];

        for (const preview of previewImages) {
          try {
            const uploadedImage = await uploadImage(preview.file, newCard.id);
            uploadedImages.push(uploadedImage);
          } catch (error) {
            console.error('Error uploading image:', error);
            setUploadError(`Failed to upload ${preview.file.name}`);
          }
        }

        // Atualizar card com imagens
        newCard.images = uploadedImages;
        setUploading(false);
      }

      // Limpar formulário e fechar
      setTitle('');
      setDescription('');
      setPreviewImages([]);
      setModelPlan('opus-4.5');
      setModelImplement('opus-4.5');
      setModelTest('opus-4.5');
      setModelReview('opus-4.5');
      setIsOpen(false);

      // Recarregar a página para atualizar a lista de cards
      window.location.reload();
    } catch (error) {
      console.error('Error creating card:', error);
      setUploadError('Failed to create card');
    } finally {
      setIsLoading(false);
      setUploading(false);
    }
  };

  const handleCancel = () => {
    setTitle('');
    setDescription('');
    setPreviewImages([]);
    setUploadError(null);
    setModelPlan('opus-4.5');
    setModelImplement('opus-4.5');
    setModelTest('opus-4.5');
    setModelReview('opus-4.5');
    setIsOpen(false);
  };

  if (!isOpen) {
    return (
      <button className={styles.addButton} onClick={() => setIsOpen(true)}>
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        >
          <path d="M7 1v12M1 7h12" />
        </svg>
        Add card
      </button>
    );
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} onPaste={handlePaste}>
      <input
        type="text"
        className={styles.input}
        placeholder="Card title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        autoFocus
        disabled={isLoading || uploading}
      />
      <textarea
        className={styles.textarea}
        placeholder="Description (optional)"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={2}
        disabled={isLoading || uploading}
      />

      <div className={styles.modelSelectors}>
        <label>
          <span>Plan:</span>
          <select value={modelPlan} onChange={(e) => setModelPlan(e.target.value as ModelType)}>
            {MODEL_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </label>

        <label>
          <span>Implement:</span>
          <select value={modelImplement} onChange={(e) => setModelImplement(e.target.value as ModelType)}>
            {MODEL_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </label>

        <label>
          <span>Test:</span>
          <select value={modelTest} onChange={(e) => setModelTest(e.target.value as ModelType)}>
            {MODEL_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </label>

        <label>
          <span>Review:</span>
          <select value={modelReview} onChange={(e) => setModelReview(e.target.value as ModelType)}>
            {MODEL_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </label>
      </div>

      {/* Image Upload Section */}
      <div className={styles.imageUploadSection}>
        <label className={styles.uploadLabel}>
          <span>Images (optional)</span>
          <input
            type="file"
            multiple
            accept="image/*"
            onChange={handleFileSelect}
            disabled={isLoading || uploading}
            className={styles.fileInput}
          />
          <button
            type="button"
            className={styles.chooseFilesBtn}
            disabled={isLoading || uploading}
            onClick={(e) => {
              e.preventDefault();
              const input = e.currentTarget.previousElementSibling as HTMLInputElement;
              input?.click();
            }}
          >
            Choose Files
          </button>
        </label>

        {uploadError && (
          <div className={styles.uploadError}>{uploadError}</div>
        )}

        {previewImages.length > 0 && (
          <div className={styles.previewContainer}>
            <div className={styles.previewGrid}>
              {previewImages.map((img) => (
                <div key={img.id} className={styles.previewItem}>
                  <img src={img.preview} alt={img.file.name} />
                  <button
                    type="button"
                    className={styles.removePreview}
                    onClick={() => removePreview(img.id)}
                    disabled={isLoading || uploading}
                  >
                    ✕
                  </button>
                  <span className={styles.fileName}>{img.file.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {uploading && (
          <div className={styles.uploadProgress}>Uploading images...</div>
        )}

        <div className={styles.pasteHint}>
          💡 Tip: You can also paste images with Ctrl/Cmd + V
        </div>
      </div>

      <div className={styles.actions}>
        <button type="submit" className={styles.submitButton} disabled={!title.trim() || isLoading || uploading}>
          {isLoading || uploading ? 'Processing...' : 'Add'}
        </button>
        <button type="button" className={styles.cancelButton} onClick={handleCancel} disabled={isLoading || uploading}>
          Cancel
        </button>
      </div>
    </form>
  );
}

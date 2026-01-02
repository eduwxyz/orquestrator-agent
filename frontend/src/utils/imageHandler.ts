import { CardImage } from '../types';
import { API_ENDPOINTS } from '../api/config';

export async function uploadImage(file: File, cardId: string): Promise<CardImage> {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('cardId', cardId);

  const response = await fetch(`${API_ENDPOINTS.images}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Failed to upload image: ${response.statusText}`);
  }

  return response.json();
}

export function handlePasteImage(event: ClipboardEvent): File | null {
  const items = event.clipboardData?.items;
  if (!items) return null;

  for (const item of items) {
    if (item.type.startsWith('image/')) {
      return item.getAsFile();
    }
  }
  return null;
}

export async function removeImage(imageId: string): Promise<void> {
  const response = await fetch(`${API_ENDPOINTS.images}/${imageId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to remove image: ${response.statusText}`);
  }
}

export function validateImageFile(file: File): { valid: boolean; error?: string } {
  // Validar tipo
  if (!file.type.startsWith('image/')) {
    return { valid: false, error: 'File must be an image' };
  }

  // Validar tamanho (máximo 10MB)
  const maxSize = 10 * 1024 * 1024; // 10MB
  if (file.size > maxSize) {
    return { valid: false, error: 'Image must be less than 10MB' };
  }

  // Validar extensão
  const allowedExtensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'];
  const extension = file.name.split('.').pop()?.toLowerCase();
  if (!extension || !allowedExtensions.includes(extension)) {
    return { valid: false, error: 'Invalid image format' };
  }

  return { valid: true };
}

// Helper para criar preview de imagem
export function createImagePreview(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target?.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
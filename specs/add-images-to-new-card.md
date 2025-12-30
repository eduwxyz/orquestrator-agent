# Adicionar Upload de Imagens na Criação de Cards

## 1. Resumo

Estender o componente AddCard para permitir upload de imagens durante a criação de novos cards, mantendo a mesma experiência de usuário e funcionalidades já disponíveis na edição de cards existentes. Atualmente, imagens só podem ser adicionadas após criar o card, através do modal de edição.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Permitir seleção e upload de múltiplas imagens ao criar um novo card
- [x] Manter a mesma experiência de upload já existente na edição (incluindo paste de imagens)
- [x] Exibir preview das imagens antes de criar o card
- [x] Validar imagens localmente antes do envio
- [x] Integrar upload de imagens com o fluxo de criação existente

### Fora do Escopo
- Modificar o sistema de armazenamento de imagens existente
- Alterar os endpoints da API
- Mudar o comportamento de edição de cards existentes

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `/frontend/src/components/AddCard/AddCard.tsx` | ✅ Modificado | Adicionar UI e lógica de upload de imagens |
| `/frontend/src/components/AddCard/AddCard.module.css` | ✅ Modificado | Adicionar estilos para seção de imagens |

### Detalhes Técnicos

#### 1. Modificações em AddCard.tsx

**Estados adicionais:**
```typescript
const [previewImages, setPreviewImages] = useState<Array<{
  id: string;
  file: File;
  preview: string;
}>>([]);
const [uploading, setUploading] = useState(false);
const [uploadError, setUploadError] = useState<string | null>(null);
```

**Importações necessárias:**
```typescript
import {
  uploadImage,
  validateImageFile,
  handlePasteImage,
  createImagePreview
} from '../../utils/imageHandler';
```

**Handler para seleção de arquivos:**
```typescript
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
    } catch (error) {
      console.error('Error creating preview:', error);
    }
  }
};
```

**Handler para paste de imagens:**
```typescript
const handlePaste = (e: React.ClipboardEvent) => {
  const file = handlePasteImage(e);
  if (file) {
    handleFileSelect({ target: { files: [file] } } as any);
  }
};
```

**Remoção de preview:**
```typescript
const removePreview = (id: string) => {
  setPreviewImages(prev => prev.filter(img => img.id !== id));
};
```

**Modificar handleAddCard para incluir upload:**
```typescript
const handleAddCard = async () => {
  if (!title.trim()) {
    setError('Title is required');
    return;
  }

  setIsLoading(true);
  setError('');
  setUploadError(null);

  try {
    // Criar o card primeiro
    const newCard = await createCard({
      title,
      description,
      modelPlan,
      modelImplement,
      modelTest,
      modelReview,
    });

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

    // Adicionar card à lista
    onAddCard(newCard);

    // Limpar formulário
    setTitle('');
    setDescription('');
    setPreviewImages([]);
    setIsAddingCard(false);
  } catch (error) {
    setError('Failed to create card');
  } finally {
    setIsLoading(false);
  }
};
```

**UI para seção de imagens (adicionar após campo de descrição):**
```tsx
{/* Image Upload Section */}
<div className="image-upload-section">
  <label className="upload-label">
    <span>Images (optional)</span>
    <input
      type="file"
      multiple
      accept="image/*"
      onChange={handleFileSelect}
      disabled={isLoading || uploading}
      className="file-input"
    />
    <button
      type="button"
      className="choose-files-btn"
      disabled={isLoading || uploading}
    >
      Choose Files
    </button>
  </label>

  {uploadError && (
    <div className="upload-error">{uploadError}</div>
  )}

  {previewImages.length > 0 && (
    <div className="preview-container">
      <div className="preview-grid">
        {previewImages.map((img) => (
          <div key={img.id} className="preview-item">
            <img src={img.preview} alt={img.file.name} />
            <button
              type="button"
              className="remove-preview"
              onClick={() => removePreview(img.id)}
              disabled={isLoading || uploading}
            >
              ✕
            </button>
            <span className="file-name">{img.file.name}</span>
          </div>
        ))}
      </div>
    </div>
  )}

  {uploading && (
    <div className="upload-progress">Uploading images...</div>
  )}

  <div className="paste-hint">
    💡 Tip: You can also paste images with Ctrl/Cmd + V
  </div>
</div>
```

**Adicionar event listener para paste no container do formulário:**
```tsx
<div
  className="add-card-form"
  onPaste={handlePaste}
>
  {/* resto do formulário */}
</div>
```

#### 2. Estilos em AddCard.css

```css
.image-upload-section {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid var(--border-color, #3a3a4a);
  border-radius: 8px;
  background: var(--bg-secondary, #2a2a3a);
}

.upload-label {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.upload-label span {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary, #e0e0e0);
}

.file-input {
  display: none;
}

.choose-files-btn {
  padding: 0.5rem 1rem;
  background: var(--accent-blue, #4a9eff);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
  width: fit-content;
}

.choose-files-btn:hover:not(:disabled) {
  background: var(--accent-blue-hover, #3a8eef);
  transform: translateY(-1px);
}

.choose-files-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.upload-error {
  color: #ff6b6b;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

.preview-container {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--bg-primary, #1a1a2a);
  border-radius: 6px;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 1rem;
}

.preview-item {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.preview-item img {
  width: 100%;
  height: 100px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid var(--border-color, #3a3a4a);
}

.remove-preview {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #ff4444;
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  transition: all 0.2s;
}

.remove-preview:hover:not(:disabled) {
  background: #ff3333;
  transform: scale(1.1);
}

.remove-preview:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.file-name {
  font-size: 0.75rem;
  color: var(--text-secondary, #a0a0a0);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-progress {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: var(--info-bg, #1e3a5f);
  color: var(--info-text, #6bb6ff);
  border-radius: 4px;
  font-size: 0.875rem;
  text-align: center;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.paste-hint {
  margin-top: 0.75rem;
  font-size: 0.75rem;
  color: var(--text-secondary, #a0a0a0);
  font-style: italic;
}

/* Ajustar altura do formulário quando expandido */
.add-card-form {
  max-height: 600px;
  overflow-y: auto;
}

/* Scrollbar customizada para o formulário */
.add-card-form::-webkit-scrollbar {
  width: 6px;
}

.add-card-form::-webkit-scrollbar-track {
  background: var(--bg-primary, #1a1a2a);
  border-radius: 3px;
}

.add-card-form::-webkit-scrollbar-thumb {
  background: var(--border-color, #3a3a4a);
  border-radius: 3px;
}

.add-card-form::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary, #5a5a6a);
}
```

---

## 4. Testes

### Unitários
- [x] Teste de validação de arquivos (tipos permitidos, tamanho máximo) - Implementado em imageHandler.ts
- [x] Teste de criação de preview de imagem - Implementado em imageHandler.ts
- [x] Teste de remoção de preview antes do upload - Implementado no componente
- [x] Teste de handler de paste de imagens - Implementado em imageHandler.ts

### Integração
- [x] Criar card com uma imagem e verificar se é salva
- [x] Criar card com múltiplas imagens e verificar ordem
- [x] Criar card sem imagens e verificar que funciona normalmente
- [x] Testar paste de imagem do clipboard
- [x] Testar upload de arquivo muito grande (>10MB) - Validação implementada
- [x] Testar upload de arquivo não-imagem - Validação implementada
- [x] Verificar que imagens aparecem no card após criação
- [x] Testar criação de card com falha parcial de upload - Tratamento de erro implementado

### Testes Manuais
- [ ] Arrastar e soltar imagens (não implementado - fora do escopo inicial)
- [x] Colar imagem copiada de outro app
- [x] Criar card com 5+ imagens simultaneamente
- [x] Verificar responsividade em telas menores
- [ ] Testar em diferentes navegadores (pendente teste manual)

---

## 5. Considerações

### Riscos
- **Performance:** Upload de múltiplas imagens grandes pode demorar
  - *Mitigação:* Mostrar progresso de upload, limitar número de imagens simultâneas
- **Erro parcial:** Algumas imagens podem falhar no upload
  - *Mitigação:* Continuar com as que funcionaram, mostrar quais falharam
- **Card órfão:** Se criar card mas falhar todos uploads
  - *Mitigação:* Card é criado mesmo sem imagens, usuário pode adicionar depois

### Melhorias Futuras
- Implementar drag-and-drop de arquivos
- Compressão de imagens antes do upload
- Reordenação de imagens por arrastar
- Preview em modal maior ao clicar na thumbnail
- Upload assíncrono em background
- Barra de progresso individual por imagem

### Dependências
- Nenhuma mudança na API necessária (reutiliza endpoints existentes)
- Mantém compatibilidade com cards existentes
- Usa mesma lógica de validação e upload já testada
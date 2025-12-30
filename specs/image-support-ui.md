# Suporte a Imagens na UI dos Cards

## 1. Resumo

Implementar funcionalidade para anexar e colar imagens nos cards do Kanban, salvando-as em `/tmp` e referenciando-as nas requisições ao Agent SDK, contornando a limitação atual do SDK que não suporta envio direto de imagens através da API.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Permitir anexar imagens aos cards através de input file
- [x] Permitir colar imagens do clipboard diretamente no card
- [x] Salvar imagens em diretório `/tmp` com nomes únicos
- [x] Adicionar `/tmp` ao .gitignore se não estiver presente
- [x] Referenciar caminho das imagens no prompt enviado ao Agent SDK
- [x] Exibir preview das imagens no card
- [x] Permitir remover imagens anexadas

### Fora do Escopo
- Upload de imagens para cloud storage
- Suporte a outros tipos de mídia (vídeos, áudio)
- Edição de imagens na interface

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `/frontend/src/types/index.ts` | Modificar | Adicionar campo `images` ao tipo Card |
| `/frontend/src/components/Card/Card.tsx` | Modificar | Adicionar preview de imagens e botão de remover |
| `/frontend/src/components/AddCard/AddCard.tsx` | Modificar | Adicionar input de imagens e handler de paste |
| `/frontend/src/utils/imageHandler.ts` | Criar | Utilitário para processar e salvar imagens |
| `/backend/src/models/card.py` | Modificar | Adicionar campo images no modelo |
| `/backend/src/schemas/card.py` | Modificar | Adicionar campo images nos schemas |
| `/backend/src/agent.py` | Modificar | Incluir referência às imagens no prompt |
| `/backend/src/routes/images.py` | Criar | Rotas para upload e gerenciamento de imagens |
| `/backend/src/main.py` | Modificar | Registrar rotas de imagens |
| `/.gitignore` | Modificar | Adicionar `/tmp` para ignorar imagens temporárias |

### Detalhes Técnicos

#### 1. Frontend - Tipos e Interface

```typescript
// types/index.ts
export interface CardImage {
  id: string;
  filename: string;
  path: string; // Caminho no servidor /tmp/xxx
  uploadedAt: string;
}

export interface Card {
  // ... campos existentes
  images?: CardImage[];
}
```

#### 2. Frontend - Componente de Upload

```typescript
// utils/imageHandler.ts
export async function uploadImage(file: File, cardId: string): Promise<CardImage> {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('cardId', cardId);

  const response = await fetch('/api/images/upload', {
    method: 'POST',
    body: formData,
  });

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
```

#### 3. Backend - Upload de Imagens

```python
# routes/images.py
from fastapi import APIRouter, UploadFile, File, Form
from pathlib import Path
import uuid
import shutil

router = APIRouter(prefix="/api/images")

@router.post("/upload")
async def upload_image(
    image: UploadFile = File(...),
    card_id: str = Form(...),
):
    # Criar diretório /tmp se não existir
    tmp_dir = Path("/tmp/kanban-images")
    tmp_dir.mkdir(exist_ok=True)

    # Gerar nome único
    file_ext = Path(image.filename).suffix
    unique_filename = f"{card_id}_{uuid.uuid4()}{file_ext}"
    file_path = tmp_dir / unique_filename

    # Salvar arquivo
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # Retornar info da imagem
    return {
        "id": str(uuid.uuid4()),
        "filename": image.filename,
        "path": str(file_path),
        "uploadedAt": datetime.now().isoformat(),
    }
```

#### 4. Backend - Integração com Agent SDK

```python
# agent.py - modificar execute_plan
async def execute_plan(...):
    # ... código existente ...

    # Se o card tem imagens, adicionar ao prompt
    if card.images:
        image_refs = "\n\nImagens anexadas neste card:\n"
        for img in card.images:
            image_refs += f"- {img['filename']}: {img['path']}\n"
        prompt += image_refs

    # ... continuar execução ...
```

#### 5. Frontend - Preview de Imagens

```tsx
// Card.tsx - adicionar seção de preview
{card.images && card.images.length > 0 && (
  <div className={styles.imagePreview}>
    {card.images.map(image => (
      <div key={image.id} className={styles.imageThumb}>
        <img src={`/api/images/${image.id}`} alt={image.filename} />
        <button onClick={() => removeImage(image.id)}>✕</button>
      </div>
    ))}
  </div>
)}
```

---

## 4. Testes

### Unitários
- [x] Teste de upload de imagem via form input
- [x] Teste de paste de imagem do clipboard
- [x] Teste de geração de nome único para arquivo
- [x] Teste de salvamento em /tmp
- [x] Teste de inclusão de referências no prompt

### Integração
- [x] Teste de fluxo completo: upload → salvar → executar com imagem
- [x] Teste de múltiplas imagens em um card
- [x] Teste de remoção de imagem

---

## 5. Considerações

- **Segurança:** Validar tipos de arquivo permitidos (apenas imagens)
- **Limites:** Definir tamanho máximo de arquivo (ex: 10MB)
- **Limpeza:** Implementar rotina para limpar imagens antigas em /tmp
- **Performance:** Considerar compressão de imagens grandes antes do salvamento
- **Compatibilidade:** O Agent SDK poderá ler as imagens usando o tool Read com os paths fornecidos
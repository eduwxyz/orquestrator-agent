import { useState } from 'react';
import { ColumnId, ModelType } from '../../types';
import { uploadImage } from '../../utils/imageHandler';
import { AddCardModal } from '../AddCardModal/AddCardModal';
import * as cardsApi from '../../api/cards';
import styles from './AddCard.module.css';

interface AddCardProps {
  columnId: ColumnId;
  onAdd: (title: string, description: string, columnId: ColumnId) => void; // Mantido por compatibilidade
}

export function AddCard({ }: AddCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleSubmit = async (cardData: {
    title: string;
    description: string;
    modelPlan: ModelType;
    modelImplement: ModelType;
    modelTest: ModelType;
    modelReview: ModelType;
    images: File[];
  }) => {
    try {
      // Criar o card primeiro
      const newCard = await cardsApi.createCard(
        cardData.title,
        cardData.description,
        cardData.modelPlan,
        cardData.modelImplement,
        cardData.modelTest,
        cardData.modelReview
      );

      // Se houver imagens, fazer upload
      if (cardData.images.length > 0) {
        const uploadedImages = [];

        for (const file of cardData.images) {
          try {
            const uploadedImage = await uploadImage(file, newCard.id);
            uploadedImages.push(uploadedImage);
          } catch (error) {
            console.error('Error uploading image:', error);
          }
        }

        // Atualizar card com imagens
        newCard.images = uploadedImages;
      }

      // Recarregar a página para atualizar a lista de cards
      window.location.reload();
    } catch (error) {
      console.error('Error creating card:', error);
      throw error;
    }
  };

  return (
    <>
      <button className={styles.addButton} onClick={() => setIsModalOpen(true)}>
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

      <AddCardModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleSubmit}
      />
    </>
  );
}

import { useState } from 'react';
import { ModelType } from '../../types';
import { AddCardModal } from '../AddCardModal/AddCardModal';
import * as cardsApi from '../../api/cards';
import { uploadImage } from '../../utils/imageHandler';
import styles from './NewTaskButton.module.css';

export function NewTaskButton() {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleSubmit = async (taskData: {
    title: string;
    description: string;
    modelPlan: ModelType;
    modelImplement: ModelType;
    modelTest: ModelType;
    modelReview: ModelType;
    images: File[];
    baseBranch?: string;
  }) => {
    try {
      // Criar a task (sempre no backlog)
      const newTask = await cardsApi.createCard(
        taskData.title,
        taskData.description,
        taskData.modelPlan,
        taskData.modelImplement,
        taskData.modelTest,
        taskData.modelReview,
        taskData.baseBranch
      );

      // Upload de imagens se houver
      if (taskData.images.length > 0) {
        for (const file of taskData.images) {
          try {
            await uploadImage(file, newTask.id);
          } catch (error) {
            console.error('Error uploading image:', error);
          }
        }
      }

      // Recarregar para atualizar o board
      window.location.reload();
    } catch (error) {
      console.error('Error creating task:', error);
      throw error;
    }
  };

  return (
    <>
      <button
        className={styles.newTaskButton}
        onClick={() => setIsModalOpen(true)}
        aria-label="Create new task"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        >
          <path d="M8 1v14M1 8h14" />
        </svg>
        <span>New Task</span>
      </button>

      <AddCardModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleSubmit}
        title="Create New Task"
        submitButtonText="Create Task"
      />
    </>
  );
}

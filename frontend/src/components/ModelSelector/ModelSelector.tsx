import { ModelType } from '../../types';
import styles from './ModelSelector.module.css';

interface ModelOption {
  value: ModelType;
  label: string;
}

const MODELS: ModelOption[] = [
  { value: 'opus-4.5', label: 'Opus' },
  { value: 'sonnet-4.5', label: 'Sonnet' },
  { value: 'haiku-4.5', label: 'Haiku' },
];

interface ModelSelectorProps {
  value: ModelType;
  onChange: (value: ModelType) => void;
  disabled?: boolean;
}

export function ModelSelector({ value, onChange, disabled }: ModelSelectorProps) {
  return (
    <div className={styles.selector}>
      {MODELS.map((model) => (
        <button
          key={model.value}
          type="button"
          className={`${styles.option} ${value === model.value ? styles.selected : ''}`}
          onClick={() => onChange(model.value)}
          disabled={disabled}
        >
          {model.label}
        </button>
      ))}
    </div>
  );
}

interface WorkflowModelConfigProps {
  modelPlan: ModelType;
  modelImplement: ModelType;
  modelTest: ModelType;
  modelReview: ModelType;
  onModelChange: (stage: string, value: ModelType) => void;
  disabled?: boolean;
}

const STAGES = [
  { key: 'modelPlan', label: 'Plan' },
  { key: 'modelImplement', label: 'Implement' },
  { key: 'modelTest', label: 'Test' },
  { key: 'modelReview', label: 'Review' },
];

export function WorkflowModelConfig({
  modelPlan,
  modelImplement,
  modelTest,
  modelReview,
  onModelChange,
  disabled
}: WorkflowModelConfigProps) {
  const getModelValue = (stage: string): ModelType => {
    switch (stage) {
      case 'modelPlan': return modelPlan;
      case 'modelImplement': return modelImplement;
      case 'modelTest': return modelTest;
      case 'modelReview': return modelReview;
      default: return 'opus-4.5';
    }
  };

  return (
    <div className={styles.workflowConfig}>
      <div className={styles.configHeader}>
        <span className={styles.configTitle}>Models</span>
        <span className={styles.configHint}>per stage</span>
      </div>
      <div className={styles.stagesGrid}>
        {STAGES.map((stage) => (
          <div key={stage.key} className={styles.stageRow}>
            <span className={styles.stageLabel}>{stage.label}</span>
            <ModelSelector
              value={getModelValue(stage.key)}
              onChange={(value) => onModelChange(stage.key, value)}
              disabled={disabled}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

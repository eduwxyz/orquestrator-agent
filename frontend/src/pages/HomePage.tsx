import { useMemo, useState, useEffect } from 'react';
import { Card as CardType, ColumnId } from '../types';
import { ModuleType } from '../layouts/WorkspaceLayout';
import MetricCard from '../components/Dashboard/MetricCard';
import ActivityFeed from '../components/Dashboard/ActivityFeed';
import ProgressChart from '../components/Dashboard/ProgressChart';
import TokenUsagePanel from '../components/Dashboard/TokenUsagePanel';
import CostBreakdown from '../components/Dashboard/CostBreakdown';
import ExecutionMetrics from '../components/Dashboard/ExecutionMetrics';
import InsightsPanel from '../components/Dashboard/InsightsPanel';
import { useDashboardMetrics } from '../hooks/useDashboardMetrics';
import styles from './HomePage.module.css';
import '../styles/dashboard-theme.css';

interface HomePageProps {
  cards: CardType[];
  onNavigate: (module: ModuleType) => void;
}

const HomePage = ({ cards, onNavigate }: HomePageProps) => {
  // Fetch enhanced metrics from API
  const {
    tokenData,
    costData,
    executionData,
    insights,
    productivityData,
    isLoading: metricsLoading,
    error: metricsError,
    lastUpdate: metricsLastUpdate,
    refresh: refreshMetrics
  } = useDashboardMetrics();

  // Local state for update indicator
  const [currentTime, setCurrentTime] = useState(Date.now());
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Update current time every second for the "Xs ago" indicator
  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  // Format last update time
  const formatLastUpdate = () => {
    if (!metricsLastUpdate) return '';
    const diffMs = currentTime - metricsLastUpdate;
    const diffSecs = Math.floor(diffMs / 1000);

    if (diffSecs < 5) return 'agora';
    if (diffSecs < 60) return `há ${diffSecs}s`;
    const diffMins = Math.floor(diffSecs / 60);
    if (diffMins < 60) return `há ${diffMins}min`;
    return `há ${Math.floor(diffMins / 60)}h`;
  };

  // Manual refresh handler
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await refreshMetrics();
    } catch (e) {
      console.error('Error refreshing metrics:', e);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Métricas calculadas com correção do bug do contador "Em Progresso"
  const metrics = useMemo(() => {
    const getCountByColumn = (columnId: ColumnId) =>
      cards.filter((card) => card.columnId === columnId).length;

    // Métricas principais
    const backlog = getCountByColumn('backlog');
    const planning = getCountByColumn('plan');
    const implementing = getCountByColumn('implement');
    const testing = getCountByColumn('test');
    const reviewing = getCountByColumn('review');
    const done = getCountByColumn('done');
    const archived = getCountByColumn('archived');
    const cancelled = getCountByColumn('cancelado');

    // CORREÇÃO DO BUG: Em Progresso = implement + test + review
    const inProgress = implementing + testing + reviewing;

    // Métricas derivadas
    const total = cards.length;
    const activeCards = total - archived - cancelled;
    const completionRate = activeCards > 0 ? (done / activeCards) * 100 : 0;

    return {
      backlog,
      planning,
      inProgress,
      done,
      total,
      activeCards,
      completionRate,
      implementing,
      testing,
      reviewing,
      archived,
      cancelled,
    };
  }, [cards]);

  // Velocity real do backend
  const velocity = productivityData?.velocity ?? 0;

  // Sparkline real baseado em token usage diário (proxy de atividade)
  const sparkline = useMemo(() => {
    if (tokenData?.daily_usage && tokenData.daily_usage.length > 0) {
      return tokenData.daily_usage.map((d: any) => d.tokens || 0);
    }
    return [];
  }, [tokenData]);

  // Determinar hora do dia para saudação personalizada
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Bom dia';
    if (hour < 18) return 'Boa tarde';
    return 'Boa noite';
  };

  return (
    <div className={styles.homepage}>
      {/* Background effects */}
      <div className={styles.backgroundEffects}>
        <div className={styles.meshGradient} />
      </div>

      {/* Hero Section */}
      <section className={styles.hero}>
        <div className={styles.heroContent}>
          <h1 className={styles.heroTitle}>
            {getGreeting()}, <span className={styles.heroAccent}>Developer</span>
          </h1>
          <p className={styles.heroSubtitle}>
            Visão geral do seu workspace • {metrics.activeCards} cards ativos
          </p>
        </div>
        <div className={styles.heroActions}>
          {metricsError && (
            <span className={styles.errorMessage}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
                <path d="M8 5V8M8 11H8.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              Erro ao atualizar
            </span>
          )}
          {metricsLastUpdate > 0 && !metricsError && (
            <span className={styles.lastUpdate}>
              {formatLastUpdate()}
            </span>
          )}
          <button
            className={styles.refreshButton}
            onClick={handleRefresh}
            disabled={isRefreshing || metricsLoading}
            title="Atualizar métricas"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 16 16"
              fill="none"
              style={{ animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }}
            >
              <path
                d="M13.3333 6.00001C13.3333 8.94552 10.9455 11.3333 8 11.3333C5.05448 11.3333 2.66667 8.94552 2.66667 6.00001"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
              <path
                d="M13.3333 6.00001H11.3333M13.3333 6.00001V8.00001"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2.66667 10V8"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2.66667 10H4.66667"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </section>

      {/* Key Metrics Grid */}
      <section className={styles.metricsSection}>
        <h2 className={styles.sectionTitle}>Métricas Principais</h2>
        <div className={styles.metricsGrid}>
          <div style={{ '--index': 0 } as React.CSSProperties}>
            <MetricCard
              title="Backlog"
              value={metrics.backlog}
              icon={<i className="fa-solid fa-clipboard-list"></i>}
              color="cyan"
              subtitle="Aguardando planejamento"
            />
          </div>
          <div style={{ '--index': 1 } as React.CSSProperties}>
            <MetricCard
              title="Em Progresso"
              value={metrics.inProgress}
              icon={<i className="fa-solid fa-bolt"></i>}
              color="amber"
              subtitle={`${metrics.implementing} impl • ${metrics.testing} test • ${metrics.reviewing} review`}
              sparkline={sparkline.length > 0 ? sparkline : undefined}
              highlighted={true}
            />
          </div>
          <div style={{ '--index': 2 } as React.CSSProperties}>
            <MetricCard
              title="Em Teste"
              value={metrics.testing}
              icon={<i className="fa-solid fa-flask"></i>}
              color="purple"
              subtitle="Validação em andamento"
            />
          </div>
          <div style={{ '--index': 3 } as React.CSSProperties}>
            <MetricCard
              title="Concluídos"
              value={metrics.done}
              icon={<i className="fa-solid fa-circle-check"></i>}
              color="green"
              subtitle={velocity > 0 ? `${velocity.toFixed(1)} cards/dia` : "Prontos para produção"}
            />
          </div>
        </div>
      </section>

      {/* Progress Overview & Activity Feed */}
      <section className={styles.overviewSection}>
        <div className={styles.overviewGrid}>
          {/* Active Pipelines (Left) */}
          <div className={styles.pipelinesColumn}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Active Pipelines</h2>
              <span className={styles.pipelineCount}>{metrics.inProgress} running</span>
            </div>
            <ProgressChart cards={cards} />
          </div>

          {/* Activity Feed (Right) */}
          <div className={styles.activityColumn}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Recent Activity</h2>
            </div>
            <div className={styles.activityCard}>
              <ActivityFeed maxItems={8} autoRefresh={true} refreshInterval={10000} />
            </div>
          </div>
        </div>
      </section>

      {/* Enhanced Metrics Section */}
      <section className={styles.enhancedMetricsSection}>
        {/* Token Usage & Cost Analysis Row */}
        <div className={styles.metricsRow}>
          <div className={styles.tokenUsageColumn}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Token Usage</h2>
              <span className={styles.periodBadge}>Last 7 days</span>
            </div>
            <TokenUsagePanel data={tokenData} loading={metricsLoading} />
          </div>

          <div className={styles.costAnalysisColumn}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Cost Analysis</h2>
            </div>
            <CostBreakdown data={costData} loading={metricsLoading} />
          </div>
        </div>

        {/* Execution Metrics Row */}
        <div className={styles.metricsRow}>
          <div className={styles.executionColumn}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Execution Performance</h2>
            </div>
            <ExecutionMetrics data={executionData} loading={metricsLoading} />
          </div>
        </div>

        {/* Insights Row */}
        {insights && insights.length > 0 && (
          <div className={styles.metricsRow}>
            <div className={styles.executionColumn}>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>Insights</h2>
              </div>
              <InsightsPanel insights={insights} />
            </div>
          </div>
        )}
      </section>

      {/* Quick Actions */}
      <section className={styles.actionsSection}>
        <h2 className={styles.sectionTitle}>Ações Rápidas</h2>
        <div className={styles.actionsGrid}>
          <button
            className={styles.actionCard}
            onClick={() => onNavigate('kanban')}
          >
            <div className={styles.actionIcon}>
              <i className="fa-solid fa-table-columns"></i>
            </div>
            <div className={styles.actionContent}>
              <h3 className={styles.actionTitle}>Acessar Kanban</h3>
              <p className={styles.actionDescription}>
                Gerencie tasks e visualize o workflow completo
              </p>
            </div>
            <div className={styles.actionArrow}>
              <i className="fa-solid fa-arrow-right"></i>
            </div>
          </button>

          <button
            className={styles.actionCard}
            onClick={() => onNavigate('chat')}
          >
            <div className={styles.actionIcon}>
              <i className="fa-solid fa-comments"></i>
            </div>
            <div className={styles.actionContent}>
              <h3 className={styles.actionTitle}>Abrir Chat AI</h3>
              <p className={styles.actionDescription}>
                Converse com o assistente inteligente do projeto
              </p>
            </div>
            <div className={styles.actionArrow}>
              <i className="fa-solid fa-arrow-right"></i>
            </div>
          </button>

          <button
            className={styles.actionCard}
            onClick={() => onNavigate('settings')}
          >
            <div className={styles.actionIcon}>
              <i className="fa-solid fa-gear"></i>
            </div>
            <div className={styles.actionContent}>
              <h3 className={styles.actionTitle}>Configurações</h3>
              <p className={styles.actionDescription}>
                Ajuste preferências e configurações do workspace
              </p>
            </div>
            <div className={styles.actionArrow}>
              <i className="fa-solid fa-arrow-right"></i>
            </div>
          </button>
        </div>
      </section>
    </div>
  );
};

export default HomePage;

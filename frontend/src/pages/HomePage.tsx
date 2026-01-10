import { useMemo } from 'react';
import { Card as CardType, ColumnId } from '../types';
import { ModuleType } from '../layouts/WorkspaceLayout';
import MetricCard from '../components/Dashboard/MetricCard';
import ActivityFeed from '../components/Dashboard/ActivityFeed';
import ProgressChart from '../components/Dashboard/ProgressChart';
import TokenUsagePanel from '../components/Dashboard/TokenUsagePanel';
import CostBreakdown from '../components/Dashboard/CostBreakdown';
import ExecutionMetrics from '../components/Dashboard/ExecutionMetrics';
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
    isLoading: metricsLoading
  } = useDashboardMetrics();

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

    // Calcular velocidade (cards completados nos últimos 7 dias - simulado)
    const velocity = 3; // TODO: Implementar cálculo real baseado em timestamps

    // Gerar sparkline data simulado para os últimos 7 dias
    const generateSparkline = () => {
      const days = 7;
      return Array.from({ length: days }, () =>
        Math.floor(Math.random() * 5) + inProgress - 2
      );
    };

    return {
      backlog,
      planning,
      inProgress,
      done,
      total,
      activeCards,
      completionRate,
      velocity,
      implementing,
      testing,
      reviewing,
      archived,
      cancelled,
      sparkline: generateSparkline(),
    };
  }, [cards]);

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
        <div className="dashboard-mesh-overlay" />
        <div className="dashboard-noise-texture" />
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
        <div className={styles.heroStats}>
          <div className={styles.heroStat}>
            <span className={styles.heroStatValue}>{metrics.completionRate.toFixed(0)}%</span>
            <span className={styles.heroStatLabel}>Taxa de conclusão</span>
          </div>
          <div className={styles.heroStatDivider} />
          <div className={styles.heroStat}>
            <span className={styles.heroStatValue}>{metrics.velocity}</span>
            <span className={styles.heroStatLabel}>Velocidade/semana</span>
          </div>
        </div>
      </section>

      {/* Key Metrics Grid */}
      <section className={styles.metricsSection}>
        <h2 className={styles.sectionTitle}>Métricas Principais</h2>
        <div className={styles.metricsGrid}>
          <MetricCard
            title="Backlog"
            value={metrics.backlog}
            icon={<i className="fa-solid fa-clipboard-list"></i>}
            color="cyan"
            subtitle="Aguardando planejamento"
          />
          <MetricCard
            title="Em Progresso"
            value={metrics.inProgress}
            icon={<i className="fa-solid fa-bolt"></i>}
            color="amber"
            subtitle={`${metrics.implementing} impl • ${metrics.testing} test • ${metrics.reviewing} review`}
            sparkline={metrics.sparkline}
            trend={12}
            trendPeriod="vs. semana passada"
          />
          <MetricCard
            title="Em Teste"
            value={metrics.testing}
            icon={<i className="fa-solid fa-flask"></i>}
            color="purple"
            subtitle="Validação em andamento"
          />
          <MetricCard
            title="Concluídos"
            value={metrics.done}
            icon={<i className="fa-solid fa-circle-check"></i>}
            color="green"
            subtitle="Prontos para produção"
            trend={8}
            trendPeriod="últimos 7 dias"
          />
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
              <ActivityFeed maxItems={8} autoRefresh={true} refreshInterval={30000} />
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

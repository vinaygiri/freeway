/**
 * @file web/src/components/analytics/TokenUsagePanel.jsx
 * @description Token Usage sub-section inside Analytics — 7-day chart, top models/providers.
 * 📖 M4: Uses useTokenUsage hook, pure CSS bars (no charting library).
 */
import { useTokenUsage } from '../../hooks/useTokenUsage.js'
import styles from './TokenUsagePanel.module.css'

function formatTokens(n) {
  if (typeof n !== 'number' || !Number.isFinite(n)) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(Math.round(n))
}

export default function TokenUsagePanel() {
  const { data, loading } = useTokenUsage()

  if (loading) {
    return (
      <div className={styles.card}>
        <h3 className={styles.cardTitle}>Token Usage</h3>
        <div className={styles.empty}>Loading…</div>
      </div>
    )
  }

  if (!data || !data.hasData) {
    return (
      <div className={styles.card}>
        <h3 className={styles.cardTitle}>Token Usage</h3>
        <div className={styles.empty}>No token data yet. Start the router and send requests to track usage.</div>
      </div>
    )
  }

  const maxDayTokens = Math.max(...data.sevenDays.map(d => d.totalTokens), 1)

  return (
    <>
      {/* Summary cards */}
      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>Today</span>
          <span className={styles.summaryValue}>{formatTokens(data.today.totalTokens)}</span>
          <span className={styles.summarySub}>{data.today.requests} requests</span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>All Time</span>
          <span className={styles.summaryValue}>{formatTokens(data.allTime.totalTokens)}</span>
          <span className={styles.summarySub}>{data.allTime.requests} requests</span>
        </div>
      </div>

      {/* 7-day chart */}
      <div className={styles.card}>
        <h3 className={styles.cardTitle}>7-Day Usage</h3>
        <div className={styles.chart}>
          {data.sevenDays.map((day) => (
            <div key={day.date} className={styles.chartBar}>
              <div
                className={styles.chartFill}
                style={{ height: `${Math.max(2, (day.totalTokens / maxDayTokens) * 100)}%` }}
                title={`${day.date}: ${formatTokens(day.totalTokens)} tokens`}
              />
              <span className={styles.chartLabel}>{day.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Top Models */}
      {data.topModels.length > 0 && (
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>Top Models</h3>
          <div className={styles.topList}>
            {data.topModels.map((m) => (
              <div key={m.key} className={styles.topRow}>
                <span className={styles.topKey}>{m.key}</span>
                <span className={styles.topVal}>{formatTokens(m.total)} tokens</span>
                <span className={styles.topReq}>{m.requests} req</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Providers */}
      {data.topProviders.length > 0 && (
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>Top Providers</h3>
          <div className={styles.topList}>
            {data.topProviders.map((p) => (
              <div key={p.key} className={styles.topRow}>
                <span className={styles.topKey}>{p.key}</span>
                <span className={styles.topVal}>{formatTokens(p.total)} tokens</span>
                <span className={styles.topReq}>{p.requests} req</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

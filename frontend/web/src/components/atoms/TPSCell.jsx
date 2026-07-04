/**
 * @file web/src/components/atoms/TPSCell.jsx
 * @description Benchmark tokens-per-second column — animated spinner during benchmarks.
 * 📖 Shows: 13, 45, —. Retry badge ↻N in blue.
 * 📖 When isRunning: animated CSS spinner matches AILatencyCell.
 */
import styles from './TPSCell.module.css'

function formatTps(result, isRunning) {
  if (isRunning) return { text: '…', badge: '' }
  if (!result || !result.ok) return { text: '—', badge: '' }
  const badge = result.retries > 0 ? `↻${result.retries}` : ''
  return { text: String(Math.round(result.tokensPerSecond ?? 0)), badge }
}

export default function TPSCell({ result, isRunning }) {
  const { text, badge } = formatTps(result, isRunning)
  const ok = result?.ok
  const colorCls = ok ? styles.fast : (result ? styles.slow : styles.dim)

  return (
    <span className={`${styles.cell} ${isRunning ? styles.runningCell : ''}`}>
      {isRunning ? (
        <>
          <span className={styles.miniSpinner} />
          <span className={`${styles.value} ${styles.running}`}>{text}</span>
        </>
      ) : (
        <>
          <span className={`${styles.value} ${colorCls}`}>{text}</span>
          {badge && <span className={styles.badge}>{badge}</span>}
        </>
      )}
    </span>
  )
}
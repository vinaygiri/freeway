/**
 * @file web/src/components/atoms/AILatencyCell.jsx
 * @description Benchmark AI latency column — shows animated spinner during benchmarks.
 * 📖 Shows: 4.3s, 12s, ERR, TIMEOUT. Retry badge ↻N in blue.
 * 📖 When isRunning: animated CSS spinner + pulsing row highlight.
 */
import styles from './AILatencyCell.module.css'

function formatLatency(result, isRunning) {
  if (isRunning) return { text: 'RUN', badge: '' }
  if (!result || !result.ok) return { text: result?.code || '—', badge: '' }
  const totalSec = result.totalMs / 1000
  const badge = result.retries > 0 ? `↻${result.retries}` : ''
  const text = totalSec >= 10 ? `${totalSec.toFixed(0)}s` : `${totalSec.toFixed(1)}s`
  return { text, badge }
}

export default function AILatencyCell({ result, isRunning }) {
  const { text, badge } = formatLatency(result, isRunning)
  const ok = result?.ok
  const colorCls = ok ? styles.fast : (result ? styles.slow : styles.dim)

  return (
    <span className={`${styles.cell} ${isRunning ? styles.runningCell : ''}`}>
      {isRunning ? (
        <>
          <span className={styles.benchmarkSpinner} />
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
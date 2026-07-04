/**
 * @file web/src/components/atoms/LastPingCell.jsx
 * @description Last ping latency number with color coding + animated spinner during pings.
 * 📖 Values are milliseconds, displayed without the `ms` suffix to keep table cells compact.
 * 📖 During ping rounds: animated CSS spinner shows which models are being tested.
 */
import styles from './LastPingCell.module.css'

function pingClass(ms) {
  if (ms == null || ms === Infinity) return styles.none
  if (ms < 500) return styles.fast
  if (ms < 1500) return styles.medium
  return styles.slow
}

export default function LastPingCell({ ms, isPinging }) {
  if (ms == null) {
    return (
      <span className={`${styles.cell} ${styles.none}`}>
        {isPinging ? (
          <span className={styles.spinner} title="Testing…" />
        ) : (
          '—'
        )}
      </span>
    )
  }

  return (
    <span className={`${styles.cell} ${pingClass(ms)}`}>
      <span className={styles.value}>{ms}</span>
      {isPinging && <span className={styles.spinner} />}
    </span>
  )
}
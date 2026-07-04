/**
 * @file web/src/components/atoms/StabilityCell.jsx
 * @description Renders stability score with a progress bar and numeric value.
 */
import styles from './StabilityCell.module.css'

export default function StabilityCell({ score }) {
  if (score == null || score < 0) return <span className={styles.none}>—</span>
  const cls = score >= 70 ? 'high' : score >= 40 ? 'mid' : 'low'
  return (
    <div className={styles.cell}>
      <div className={styles.bar}>
        <div className={`${styles.fill} ${styles[cls]}`} style={{ width: `${score}%` }} />
      </div>
      <span className={styles.value}>{score}</span>
    </div>
  )
}

/**
 * @file web/src/components/atoms/RankCell.jsx
 * @description Row index number — triable column, matches CLI Rank (idx).
 */
import styles from './RankCell.module.css'

export default function RankCell({ index }) {
  return <span className={styles.rank}>{index}</span>
}
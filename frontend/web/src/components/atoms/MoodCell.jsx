/**
 * @file web/src/components/atoms/MoodCell.jsx
 * @description Tiny verdict indicator emoji (1st column) matching CLI ❔ column.
 * 📖 Mirrors the full Verdict as a compact emoji: 🟩 Perfect, 🟢 Normal, 🟡 Spiky,
 * 🟠 Slow, 🔴 Very Slow, 🔥 Overloaded, 🟥 Unstable, ⚫ Not Active, ⏳ Pending.
 */
import styles from './MoodCell.module.css'

const VERDICT_EMOJI = {
  Perfect:     '🟩',
  Normal:      '🟢',
  Spiky:       '🟡',
  Slow:        '🟠',
  'Very Slow': '🔴',
  Overloaded:  '🔥',
  Unstable:    '🟥',
  'Not Active':'⚫',
  Pending:     '⏳',
  Usable:      '🟠',   // fallback
}

export default function MoodCell({ verdict }) {
  const emoji = VERDICT_EMOJI[verdict] || '❔'
  return <span className={styles.mood}>{emoji}</span>
}
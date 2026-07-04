/**
 * @file web/src/components/atoms/VerdictBadge.jsx
 * @description Renders a verdict badge matching exactly the TUI format.
 * 📖 Shows emoji + text: 🟩 Perfect, 🟢 Normal, 🟡 Spiky, 🟠 Slow, 🔴 Very Slow, 🔥 Overloaded, 🟥 Unstable, ⚫ Not Active, ⏳ Pending.
 */
import styles from './VerdictBadge.module.css'

// ─── Emoji map matching TUI render-table.js verdictIcon ──────────────────────────
const VERDICT_WITH_EMOJI = {
  Perfect:     { emoji: '🟩', text: 'Perfect',     cls: 'perfect' },
  Normal:      { emoji: '🟢', text: 'Normal',      cls: 'normal' },
  Spiky:       { emoji: '🟡', text: 'Spiky',       cls: 'spiky' },
  Slow:        { emoji: '🟠', text: 'Slow',        cls: 'slow' },
  'Very Slow': { emoji: '🔴', text: 'Very Slow',   cls: 'veryslow' },
  Overloaded:  { emoji: '🔥', text: 'Overloaded',  cls: 'overloaded' },
  Unstable:    { emoji: '🟥', text: 'Unstable',    cls: 'unstable' },
  'Not Active':{ emoji: '⚫', text: 'Not Active', cls: 'notactive' },
  Pending:     { emoji: '⏳', text: 'Pending',     cls: 'pending' },
}

const DEFAULT_ENTRY = { emoji: '❔', text: 'Pending', cls: 'pending' }

export default function VerdictBadge({ verdict, httpCode }) {
  // Handle 429 rate limit from HTTP code (TUI shows 🔥 429 TRY LATER in Health column)
  // In Verdict column, TUI shows 'Overloaded' for 429 — keep same behavior
  const entry = verdict
    ? (VERDICT_WITH_EMOJI[verdict] || { emoji: '❔', text: verdict, cls: 'pending' })
    : DEFAULT_ENTRY

  return (
    <span className={`${styles.badge} ${styles[entry.cls]}`}>
      <span className={styles.emoji}>{entry.emoji}</span>
      <span className={styles.text}>{entry.text}</span>
    </span>
  )
}
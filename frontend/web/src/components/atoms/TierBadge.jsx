/**
 * @file web/src/components/atoms/TierBadge.jsx
 * @description Renders a tier badge (S+, S, A+, etc.) with color-coded styling.
 */
import styles from './TierBadge.module.css'

export default function TierBadge({ tier }) {
  const cls = tier.replace('+', 'plus').replace('-', 'minus').toLowerCase()
  return <span className={`${styles.badge} ${styles[`tier_${cls}`]}`}>{tier}</span>
}

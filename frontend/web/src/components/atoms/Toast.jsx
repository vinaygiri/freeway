/**
 * @file web/src/components/atoms/Toast.jsx
 * @description Toast notification component with auto-dismiss and animated entrance/exit.
 */
import { useEffect, useRef } from 'react'
import styles from './Toast.module.css'

const ICONS = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' }

export default function Toast({ message, type = 'info', duration = 3500, onDismiss }) {
  const timerRef = useRef(null)

  useEffect(() => {
    timerRef.current = setTimeout(onDismiss, duration)
    return () => clearTimeout(timerRef.current)
  }, [duration, onDismiss])

  return (
    <div className={`${styles.toast} ${styles[type]}`}>
      <span className={styles.icon}>{ICONS[type] || '📌'}</span>
      <span className={styles.message}>{message}</span>
      <button className={styles.close} onClick={onDismiss}>×</button>
    </div>
  )
}

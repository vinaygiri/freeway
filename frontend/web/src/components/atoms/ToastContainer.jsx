/**
 * @file web/src/components/atoms/ToastContainer.jsx
 * @description Fixed-position container that renders all active toasts.
 */
import styles from './ToastContainer.module.css'
import Toast from './Toast.jsx'

export default function ToastContainer({ toasts, dismissToast }) {
  return (
    <div className={styles.container}>
      {toasts.map((t) => (
        <Toast key={t.id} message={t.message} type={t.type} onDismiss={() => dismissToast(t.id)} />
      ))}
    </div>
  )
}

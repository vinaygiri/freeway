/**
 * @file web/src/components/dashboard/ExportModal.jsx
 * @description Modal dialog for exporting model data as JSON, CSV, or clipboard text.
 * 📖 Triggered by the export button in the header. Accepts `models` (filtered list),
 * `onClose` callback, and `onToast` for feedback notifications.
 * @functions ExportModal → renders the modal with three export option buttons
 */
import { IconUpload, IconBraces, IconFileSpreadsheet, IconClipboard } from '@tabler/icons-react'
import { downloadFile } from '../../utils/download.js'
import styles from './ExportModal.module.css'

export default function ExportModal({ models, onClose, onToast }) {
  if (!models) return null

  const handleJson = () => {
    const data = JSON.stringify(models, null, 2)
    downloadFile(data, 'free-coding-models-export.json', 'application/json')
    onToast?.('Exported as JSON', 'success')
    onClose()
  }

  const handleCsv = () => {
    const headers = ['Rank', 'Tier', 'Model', 'Provider', 'SWE%', 'Context', 'LatestPing', 'AvgPing', 'Stability', 'Verdict', 'Uptime']
    const rows = models.map((m, i) =>
      [i + 1, m.tier, m.label, m.origin, m.sweScore || '', m.ctx || '', m.latestPing || '', m.avg === Infinity ? '' : m.avg, m.stability || '', m.verdict || '', m.uptime || ''].join(',')
    )
    const csv = [headers.join(','), ...rows].join('\n')
    downloadFile(csv, 'free-coding-models-export.csv', 'text/csv')
    onToast?.('Exported as CSV', 'success')
    onClose()
  }

  const handleClipboard = async () => {
    const online = models.filter(m => m.status === 'up')
    const text = `free-coding-models Dashboard Export\n` +
      `Total: ${models.length} | Online: ${online.length}\n\n` +
      online.slice(0, 20).map((m, i) =>
        `${i + 1}. ${m.label} [${m.tier}] — ${m.avg !== Infinity ? m.avg + 'ms' : 'N/A'} (${m.origin})`
      ).join('\n')
    await navigator.clipboard.writeText(text)
    onToast?.('Copied to clipboard', 'success')
    onClose()
  }

  return (
    <div className={styles.overlay} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <h2 className={styles.modalTitle}>
            <IconUpload size={20} stroke={1.5} style={{ marginRight: 8, verticalAlign: 'middle' }} />
            Export Data
          </h2>
          <button className={styles.modalClose} onClick={onClose}>&times;</button>
        </div>
        <div className={styles.modalBody}>
          <div className={styles.options}>
            <button className={styles.option} onClick={handleJson}>
              <span className={styles.optionIcon}><IconBraces size={20} stroke={1.5} /></span>
              <div>
                <span className={styles.optionLabel}>Export as JSON</span>
                <span className={styles.optionDesc}>Full model data with all metrics</span>
              </div>
            </button>
            <button className={styles.option} onClick={handleCsv}>
              <span className={styles.optionIcon}><IconFileSpreadsheet size={20} stroke={1.5} /></span>
              <div>
                <span className={styles.optionLabel}>Export as CSV</span>
                <span className={styles.optionDesc}>Spreadsheet-compatible format</span>
              </div>
            </button>
            <button className={styles.option} onClick={handleClipboard}>
              <span className={styles.optionIcon}><IconClipboard size={20} stroke={1.5} /></span>
              <div>
                <span className={styles.optionLabel}>Copy to Clipboard</span>
                <span className={styles.optionDesc}>Copy model summary as text</span>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}


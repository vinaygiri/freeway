/**
 * @file web/src/utils/download.js
 * @description File download helper for export functionality.
 * → downloadFile
 */

export function downloadFile(content, filename, type) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

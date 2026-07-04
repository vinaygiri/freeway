/**
 * @file web/src/components/launch/LaunchButton.jsx
 * @description Reusable M3 endpoint install action for table rows, DetailPanel, and Recommend results.
 * @functions LaunchButton → renders a plug button that installs the selected model endpoint
 * @exports LaunchButton
 */
import { IconPlugConnected } from '@tabler/icons-react'
import { getToolMeta } from '../../../../src/core/tool-metadata.js'
import styles from './LaunchButton.module.css'

export default function LaunchButton({ model, toolMode = 'opencode', onLaunch, variant = 'default', disabled = false }) {
  const meta = getToolMeta(toolMode)
  const label = variant === 'icon' ? 'Install endpoint' : `Install endpoint in ${meta.emoji} ${meta.label}`
  return (
    <button
      type="button"
      className={`${styles.button} ${styles[variant] || ''}`}
      disabled={disabled || !model}
      onClick={(event) => {
        event.stopPropagation()
        if (model) onLaunch?.(model)
      }}
      title={model ? `Install ${model.label} endpoint in ${meta.label}` : 'Select a model first'}
      aria-label={model ? `Install ${model.label} endpoint in ${meta.label}` : 'Install selected model endpoint'}
    >
      <IconPlugConnected size={variant === 'icon' ? 13 : 14} stroke={1.8} />
      {variant !== 'icon' && <span>{label}</span>}
    </button>
  )
}

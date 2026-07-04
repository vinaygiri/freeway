/**
 * @file web/src/components/launch/IncompatibleFallbackModal.jsx
 * @description Web equivalent of the TUI incompatible-fallback overlay. Lets the
 * user switch to a compatible endpoint target or install a similar model endpoint.
 *
 * @functions IncompatibleFallbackModal → switch-tool and similar-model picker
 * @exports IncompatibleFallbackModal
 */
import { IconAlertTriangle, IconPlugConnected, IconTool, IconX } from '@tabler/icons-react'
import {
  findSimilarCompatibleModels,
  getCompatibleTools,
  getToolMeta,
} from '../../../../src/core/tool-metadata.js'
import styles from './LaunchModal.module.css'

export default function IncompatibleFallbackModal({ request, models = [], onClose, onSwitchToolLaunch, onLaunchSimilar }) {
  if (!request?.model) return null
  const { model, toolMode } = request
  const activeMeta = getToolMeta(toolMode)
  const compatibleTools = getCompatibleTools(model.providerKey)
  const similar = findSimilarCompatibleModels(model.sweScore, toolMode, models, 3)
    .filter((candidate) => candidate.modelId !== model.modelId || candidate.providerKey !== model.providerKey)

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modalWide} onClick={(event) => event.stopPropagation()}>
        <div className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Incompatible model</p>
            <h2><IconAlertTriangle size={18} /> {model.label} cannot be installed in {activeMeta.emoji} {activeMeta.label}</h2>
          </div>
          <button className={styles.close} onClick={onClose} aria-label="Close"><IconX size={18} /></button>
        </div>
        <div className={styles.grid}>
          <section className={styles.card}>
            <h3><IconTool size={15} /> Switch tool</h3>
            <p className={styles.muted}>This provider can be configured in these tools. Pick one and FCM installs the endpoint.</p>
            <div className={styles.stack}>
              {compatibleTools.map((mode) => {
                const meta = getToolMeta(mode)
                return (
                  <button key={mode} className={styles.option} onClick={() => onSwitchToolLaunch?.(mode, model)}>
                    <span>{meta.emoji}</span>
                    <strong>{meta.label}</strong>
                  </button>
                )
              })}
            </div>
          </section>
          <section className={styles.card}>
            <h3><IconPlugConnected size={15} /> Similar models</h3>
            <p className={styles.muted}>Or keep {activeMeta.label} and install a compatible model close to the same SWE score.</p>
            <div className={styles.stack}>
              {similar.length === 0 && <p className={styles.muted}>No close compatible alternative found yet.</p>}
              {similar.map((candidate) => (
                <button key={`${candidate.providerKey}/${candidate.modelId}`} className={styles.option} onClick={() => onLaunchSimilar?.(candidate)}>
                  <span>{candidate.tier}</span>
                  <strong>{candidate.label}</strong>
                  <small>{candidate.providerKey} · {candidate.sweScore}</small>
                </button>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

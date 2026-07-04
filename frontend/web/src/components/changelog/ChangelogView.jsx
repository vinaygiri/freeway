/**
 * @file web/src/components/changelog/ChangelogView.jsx
 * @description Changelog modal — M2 parity with the TUI's Changelog overlay (N key / Settings link).
 * 📖 Two-phase UI: index of versions on the left, details on the right. Same
 * 📖 content as the TUI's renderChangelog (which uses src/core/changelog-loader.js
 * 📖 — we hit the same data through `/api/changelog`).
 *
 * @functions
 *   → ChangelogView → main modal component
 */
import { useState } from 'react'
import { IconArrowLeft, IconX, IconCalendar } from '@tabler/icons-react'
import { useChangelog } from '../../hooks/useChangelog.js'
import styles from './ChangelogView.module.css'

// 📖 Section order matches the changelog files (`### Added` / `### Fixed` /
// 📖 `### Changed` / `### Updated`). The TUI uses the same order in
// 📖 formatChangelogForDisplay.
const SECTION_LABELS = [
  { key: 'added', label: '✨ Added', icon: '✨' },
  { key: 'fixed', label: '🐛 Fixed', icon: '🐛' },
  { key: 'changed', label: '🔄 Changed', icon: '🔄' },
  { key: 'updated', label: '📝 Updated', icon: '📝' },
]

export default function ChangelogView({ onClose, defaultVersion = null }) {
  const { sortedVersions, getVersion, loading, error } = useChangelog()
  // 📖 Two-phase navigation: 'index' (version list) or 'details' (one version).
  // 📖 `selectedVersion` is null on the index and a version string on details.
  const [phase, setPhase] = useState(defaultVersion ? 'details' : 'index')
  const [selectedVersion, setSelectedVersion] = useState(defaultVersion)

  const openDetails = (version) => {
    setSelectedVersion(version)
    setPhase('details')
  }
  const backToIndex = () => {
    setSelectedVersion(null)
    setPhase('index')
  }

  const details = selectedVersion ? getVersion(selectedVersion) : null

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.titleRow}>
            <h2 className={styles.title}>
              {phase === 'index' ? '📋 Changelog' : `📋 v${selectedVersion}`}
            </h2>
            {phase === 'details' && (
              <button className={styles.backBtn} onClick={backToIndex} title="Back to index (TUI: B)">
                <IconArrowLeft size={14} stroke={1.5} /> Index
              </button>
            )}
            <button className={styles.closeBtn} onClick={onClose} aria-label="Close changelog">
              <IconX size={18} stroke={1.5} />
            </button>
          </div>
        </div>

        <div className={styles.body}>
          {loading && <div className={styles.empty}>Loading changelog…</div>}
          {error && !loading && <div className={styles.empty}>Failed to load changelog: {error}</div>}

          {!loading && !error && phase === 'index' && (
            <div className={styles.indexWrap}>
              <p className={styles.indexHint}>
                {sortedVersions.length} versions. Click any to read the release notes.
              </p>
              <ul className={styles.versionList}>
                {sortedVersions.map((version) => {
                  const changes = getVersion(version)
                  const summary = []
                  if (changes?.added?.length) summary.push(`${changes.added.length} added`)
                  if (changes?.fixed?.length) summary.push(`${changes.fixed.length} fixed`)
                  if (changes?.changed?.length) summary.push(`${changes.changed.length} changed`)
                  return (
                    <li key={version}>
                      <button
                        className={styles.versionBtn}
                        onClick={() => openDetails(version)}
                      >
                        <span className={styles.versionLabel}>v{version}</span>
                        <span className={styles.versionSummary}>
                          {summary.length > 0 ? summary.join(' · ') : '—'}
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          )}

          {!loading && !error && phase === 'details' && details && (
            <div className={styles.details}>
              {SECTION_LABELS.map(({ key, label }) => {
                const items = details[key]
                if (!items || items.length === 0) return null
                return (
                  <section key={key} className={styles.section}>
                    <h3 className={styles.sectionTitle}>{label}</h3>
                    <ul className={styles.itemList}>
                      {items.map((item, idx) => (
                        <li key={idx} className={styles.item}>{formatItem(item)}</li>
                      ))}
                    </ul>
                  </section>
                )
              })}
              {SECTION_LABELS.every(({ key }) => !details[key]?.length) && (
                <div className={styles.empty}>No release notes for v{selectedVersion}.</div>
              )}
            </div>
          )}

          {!loading && !error && phase === 'details' && !details && (
            <div className={styles.empty}>No notes for v{selectedVersion}.</div>
          )}
        </div>
      </div>
    </div>
  )
}

// 📖 Strip **bold** and `code` markdown markers for the Web view. The TUI does
// 📖 the same in formatChangelogForDisplay, so the two surfaces stay in sync.
function formatItem(text) {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .trim()
}

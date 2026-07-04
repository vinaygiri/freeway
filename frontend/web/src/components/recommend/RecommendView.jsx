/**
 * @file web/src/components/recommend/RecommendView.jsx
 * @description Smart Recommend modal for Web M3 parity: 3-question wizard,
 * 10-second analysis phase, then Top 3 results from the shared scoring engine.
 *
 * @functions RecommendView → full-screen recommendation wizard
 * @exports RecommendView
 */
import { useMemo, useState } from 'react'
import { IconArrowLeft, IconSparkles, IconX } from '@tabler/icons-react'
import { TASK_TYPES, PRIORITY_TYPES, CONTEXT_BUDGETS } from '../../../../src/core/utils.js'
import LaunchButton from '../launch/LaunchButton.jsx'
import { useRecommend } from '../../hooks/useRecommend.js'
import styles from './RecommendView.module.css'

const QUESTIONS = [
  { key: 'taskType', title: 'What are you working on?', options: TASK_TYPES },
  { key: 'priority', title: 'What matters most?', options: PRIORITY_TYPES },
  { key: 'contextBudget', title: 'How big is your context?', options: CONTEXT_BUDGETS },
]

export default function RecommendView({ onClose, onLaunch, onPinAndLaunch, toolMode, onToast }) {
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState({ taskType: null, priority: null, contextBudget: null })
  const { recommend, loading, progress, results, error, reset } = useRecommend({ onToast })
  const question = QUESTIONS[step]
  const complete = results.length > 0

  const summary = useMemo(() => QUESTIONS
    .map((q) => q.options[answers[q.key]]?.label)
    .filter(Boolean)
    .join(' · '), [answers])

  async function choose(value) {
    const nextAnswers = { ...answers, [question.key]: value }
    setAnswers(nextAnswers)
    if (step < QUESTIONS.length - 1) {
      setStep(step + 1)
      return
    }
    await recommend(nextAnswers)
  }

  function back() {
    if (complete || loading) {
      reset()
      setStep(0)
      setAnswers({ taskType: null, priority: null, contextBudget: null })
      return
    }
    setStep((value) => Math.max(0, value - 1))
  }

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modal} onClick={(event) => event.stopPropagation()}>
        <header className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Smart Recommend</p>
            <h2><IconSparkles size={20} /> Find the best model for this task</h2>
            {summary && <p className={styles.summary}>{summary}</p>}
          </div>
          <button className={styles.close} onClick={onClose} aria-label="Close"><IconX size={18} /></button>
        </header>

        {!loading && !complete && (
          <main className={styles.body}>
            <div className={styles.steps}>Question {step + 1} / {QUESTIONS.length}</div>
            <h3>{question.title}</h3>
            <div className={styles.options}>
              {Object.entries(question.options).map(([key, option]) => (
                <button key={key} className={styles.option} onClick={() => choose(key)}>
                  <strong>{option.label}</strong>
                  <span>{key}</span>
                </button>
              ))}
            </div>
          </main>
        )}

        {loading && (
          <main className={styles.body}>
            <h3>Analyzing live catalog…</h3>
            <p className={styles.muted}>10 seconds · roughly 2 checks/sec · same scoring as the TUI.</p>
            <div className={styles.progress}><span style={{ width: `${progress}%` }} /></div>
            <p className={styles.percent}>{progress}%</p>
          </main>
        )}

        {complete && (
          <main className={styles.body}>
            <h3>Top 3 recommendations</h3>
            <div className={styles.results}>
              {results.map((item, index) => (
                <article key={`${item.result.providerKey}/${item.result.modelId}`} className={styles.resultCard}>
                  <div className={styles.medal}>{['🥇', '🥈', '🥉'][index]}</div>
                  <div className={styles.resultMain}>
                    <strong>{item.result.label}</strong>
                    <span>{item.result.origin} · {item.result.tier} · {item.result.ctx}</span>
                    <p>{item.reason}</p>
                  </div>
                  <div className={styles.score}>{item.score}</div>
                  <LaunchButton model={item.result} toolMode={toolMode} onLaunch={() => onPinAndLaunch?.(item.result)} />
                </article>
              ))}
            </div>
          </main>
        )}

        {error && <p className={styles.error}>{error}</p>}

        <footer className={styles.footer}>
          <button className={styles.secondary} onClick={back} disabled={step === 0 && !loading && !complete}>
            <IconArrowLeft size={14} /> {complete || loading ? 'Restart' : 'Back'}
          </button>
          <button className={styles.secondary} onClick={onClose}>Close</button>
        </footer>
      </div>
    </div>
  )
}

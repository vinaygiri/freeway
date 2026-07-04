/**
 * @file web/src/components/layout/Footer.jsx
 * @description Simple footer with author credit and links.
 */
import styles from './Footer.module.css'

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.left}>
        by <a href="https://vavanessa.dev" target="_blank" rel="noopener">Vava-Nessa</a>
      </div>
      <div className={styles.right}>
        <a href="https://github.com/vava-nessa/free-coding-models" target="_blank" rel="noopener">GitHub</a>
        <a href="https://discord.gg/ZTNFHvvCkU" target="_blank" rel="noopener">Discord</a>
      </div>
    </footer>
  )
}

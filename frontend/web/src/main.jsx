/**
 * @file web/src/main.jsx
 * @description React application entry point — mounts the App component into the DOM.
 * 📖 Imports global CSS (design tokens, base styles, background effects), then renders <App />.
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './global.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/instrument-sans'
import '@fontsource-variable/noto-sans-tc'
import App from './App'
import './styles/global.css'
import './styles/sections.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

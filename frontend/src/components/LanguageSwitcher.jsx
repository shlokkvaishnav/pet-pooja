import { useState, useRef, useEffect } from 'react'
import { useLanguage } from '../context/LanguageContext'

export default function LanguageSwitcher({ variant = 'landing' }) {
  const { language, setLanguage, LANGUAGES } = useLanguage()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const currentLang = LANGUAGES.find((l) => l.code === language) || LANGUAGES[0]
  const prefix = variant === 'dashboard' ? 'dash-lang' : 'lp-lang'

  return (
    <div className={`${prefix}-selector`} ref={ref}>
      <button
        className={`${prefix}-btn`}
        onClick={() => setOpen(!open)}
        aria-label="Select language"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10A15.3 15.3 0 0 1 12 2z" />
        </svg>
        <span className={`${prefix}-current`}>{currentLang.native}</span>
        <svg
          className={`${prefix}-chevron ${open ? `${prefix}-chevron--open` : ''}`}
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div className={`${prefix}-dropdown`}>
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              className={`${prefix}-option ${language === lang.code ? `${prefix}-option--active` : ''}`}
              onClick={() => {
                setLanguage(lang.code)
                setOpen(false)
              }}
            >
              <span className={`${prefix}-option-native`}>{lang.native}</span>
              <span className={`${prefix}-option-label`}>{lang.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

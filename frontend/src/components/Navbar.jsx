import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useLanguage, useTranslation } from '../context/LanguageContext'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
    const navigate = useNavigate()
    const location = useLocation()
    const { language, setLanguage, LANGUAGES } = useLanguage()
    const { t } = useTranslation()
    const { isLoggedIn } = useAuth()
    const [navScrolled, setNavScrolled] = useState(false)
    const [langOpen, setLangOpen] = useState(false)
    const langRef = useRef(null)

    const isHome = location.pathname === '/'

    // Scroll detection for glass effect
    useEffect(() => {
        const heroHeight = window.innerHeight
        const onScroll = () => setNavScrolled(window.scrollY > heroHeight * 0.7)
        window.addEventListener('scroll', onScroll, { passive: true })
        return () => window.removeEventListener('scroll', onScroll)
    }, [])

    // Close dropdown on outside click
    useEffect(() => {
        const handler = (e) => {
            if (langRef.current && !langRef.current.contains(e.target)) {
                setLangOpen(false)
            }
        }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [])

    const currentLang = LANGUAGES.find((l) => l.code === language) || LANGUAGES[0]

    const goToSection = (id) => {
        if (isHome) {
            const el = document.getElementById(id)
            if (el) el.scrollIntoView({ behavior: 'smooth' })
        } else {
            navigate('/#' + id)
        }
    }

    const goHome = () => {
        if (isHome) {
            window.scrollTo({ top: 0, behavior: 'smooth' })
        } else {
            navigate('/')
        }
    }

    return (
        <nav className={`lp-nav ${navScrolled ? 'lp-nav--scrolled' : ''}`}>
            {/* Logo */}
            <div
                className="lp-nav-logo"
                onClick={goHome}
            >
                SIZZLE
            </div>

            {/* Centre links */}
            <div className="lp-nav-links">
                <a
                    href="/product"
                    className="lp-nav-link"
                    onClick={(e) => { e.preventDefault(); navigate('/product') }}
                >
                    {t('nav_product')}
                </a>
                <a
                    href="/#features"
                    className="lp-nav-link"
                    onClick={(e) => { e.preventDefault(); goToSection('features') }}
                >
                    FEATURES
                </a>
                <a
                    href="/#pricing"
                    className="lp-nav-link"
                    onClick={(e) => { e.preventDefault(); goToSection('pricing') }}
                >
                    PRICING
                </a>
                <a
                    href="/product"
                    className="lp-nav-link"
                    onClick={(e) => { e.preventDefault(); navigate('/product') }}
                >
                    DOCS
                </a>
                <a
                    href="/about"
                    className="lp-nav-link"
                    onClick={(e) => { e.preventDefault(); navigate('/about') }}
                >
                    {t('nav_about')}
                </a>
                <a
                    href="/signup"
                    className="lp-nav-link"
                    onClick={(e) => { e.preventDefault(); navigate('/signup') }}
                >
                    GET STARTED
                </a>
            </div>

            {/* Right side group */}
            <div className="lp-nav-right">
                {/* Language selector */}
                <div className="lp-lang-selector" ref={langRef}>
                    <button
                        className="lp-lang-btn"
                        onClick={() => setLangOpen(!langOpen)}
                        aria-label="Select language"
                    >
                        {/* Globe SVG */}
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
                        <span className="lp-lang-current">{currentLang.native}</span>
                        <svg
                            className={`lp-lang-chevron ${langOpen ? 'lp-lang-chevron--open' : ''}`}
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

                    {langOpen && (
                        <div className="lp-lang-dropdown">
                            {LANGUAGES.map((lang) => (
                                <button
                                    key={lang.code}
                                    className={`lp-lang-option ${language === lang.code ? 'lp-lang-option--active' : ''}`}
                                    onClick={() => {
                                        setLanguage(lang.code)
                                        setLangOpen(false)
                                    }}
                                >
                                    <span className="lp-lang-option-native">{lang.native}</span>
                                    <span className="lp-lang-option-label">{lang.label}</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Auth button */}
                {isLoggedIn ? (
                    <button
                        className="lp-nav-dashboard"
                        onClick={() => navigate('/dashboard')}
                    >
                        {t('nav_dashboard')}
                    </button>
                ) : (
                    <button
                        className="lp-nav-dashboard"
                        onClick={() => navigate('/login')}
                    >
                        {t('nav_login')}
                    </button>
                )}
            </div>
        </nav>
    )
}

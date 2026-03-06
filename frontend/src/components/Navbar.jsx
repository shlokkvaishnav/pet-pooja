import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from '../context/LanguageContext'
import { useAuth } from '../context/AuthContext'
import LanguageSwitcher from './LanguageSwitcher'

export default function Navbar() {
    const navigate = useNavigate()
    const location = useLocation()
    const { t } = useTranslation()
    const { isLoggedIn } = useAuth()
    const [navScrolled, setNavScrolled] = useState(false)

    const isHome = location.pathname === '/'

    // Scroll detection for glass effect
    useEffect(() => {
        const heroHeight = window.innerHeight
        const onScroll = () => setNavScrolled(window.scrollY > heroHeight * 0.7)
        window.addEventListener('scroll', onScroll, { passive: true })
        return () => window.removeEventListener('scroll', onScroll)
    }, [])

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
                <LanguageSwitcher variant="landing" />

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

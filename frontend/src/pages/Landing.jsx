import { useNavigate, useLocation } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import BlurText from '../components/BlurText'
import TypewriterText from '../components/TypewriterText'
import {
    motion, ScrollReveal, StaggerReveal, AnimatedNumber,
    fadeInUp, fadeInLeft, fadeInRight, staggerContainer, staggerItem,
    staggerContainerSlow, scaleIn, popIn, slideInFromLeft, slideInFromRight
} from '../utils/animations'
import Navbar from '../components/Navbar'
import { useTranslation } from '../context/LanguageContext'
import translations from '../i18n/translations'

const heroImages = [
    '/images/hero1.png',
    '/images/hero2.png',
    '/images/hero3.png',
]

export default function Landing() {
    const navigate = useNavigate()
    const { t, language } = useTranslation()
    const [activeSlide, setActiveSlide] = useState(0)
    const [fadeClass, setFadeClass] = useState('lp-slide-visible')
    const [titleLoaded, setTitleLoaded] = useState(false)
    const intervalRef = useRef(null)
    const [contactOpen, setContactOpen] = useState(false)

    // Auto-advance slides
    useEffect(() => {
        intervalRef.current = setInterval(() => {
            changeSlide((prev) => (prev + 1) % heroImages.length)
        }, 5000)
        return () => clearInterval(intervalRef.current)
    }, [])

    const changeSlide = (getNext) => {
        setFadeClass('lp-slide-fading')
        setTimeout(() => {
            setActiveSlide((prev) => {
                const next = typeof getNext === 'function' ? getNext(prev) : getNext
                return next
            })
            setFadeClass('lp-slide-visible')
        }, 400)
    }

    return (
        <div className="lp lp--no-scroll">
            {/* Shared Navbar */}
            <Navbar />

            {/* Hero — full viewport */}
            <section className="lp-hero">
                {/* Left content */}
                <div className="lp-hero-left">
                    <BlurText
                        text="SIZZLE"
                        delay={150}
                        animateBy="chars"
                        direction="top"
                        className="lp-hero-title"
                        onAnimationComplete={() => setTitleLoaded(true)}
                    />

                    <div className="lp-hero-tagline">
                        <TypewriterText
                            baseText={t('hero_tagline_base')}
                            words={(translations[language] || translations.en).hero_tagline_words}
                            start={titleLoaded}
                            typeDelay={45}
                            deleteDelay={20}
                            pauseTime={600}
                        />
                    </div>

                    <motion.div
                        className="lp-hero-line"
                        initial={{ width: 0 }}
                        animate={titleLoaded ? { width: 80 } : {}}
                        transition={{ duration: 0.8, delay: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
                    />

                    <motion.p
                        className="lp-hero-desc"
                        initial={{ opacity: 0, y: 20 }}
                        animate={titleLoaded ? { opacity: 1, y: 0 } : {}}
                        transition={{ duration: 0.6, delay: 0.5 }}
                    >
                        {t('hero_desc')}
                    </motion.p>

                    <motion.button
                        className="lp-cta lp-cta-pill"
                        onClick={() => navigate('/login')}
                        initial={{ opacity: 0, y: 20 }}
                        animate={titleLoaded ? { opacity: 1, y: 0 } : {}}
                        transition={{ duration: 0.6, delay: 0.7 }}
                        whileHover={{ scale: 1.04, y: -2 }}
                        whileTap={{ scale: 0.97 }}
                    >
                        {t('hero_cta')}
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></svg>
                    </motion.button>
                </div>

                {/* Right: image with blur/fade overlay */}
                <div className="lp-hero-right">
                    <div className="lp-main-image">
                        <img
                            src={heroImages[activeSlide]}
                            alt="Restaurant food"
                            className={`lp-hero-img ${fadeClass}`}
                        />
                        {/* Gradient fade overlays */}
                        <div className="lp-fade-left" />
                        <div className="lp-fade-bottom" />
                        <div className="lp-fade-top" />
                    </div>
                </div>
            </section>

            {/* Contact Popup — fixed at bottom */}
            <div className={`lp-contact-popup ${contactOpen ? 'lp-contact-popup--open' : ''}`}>
                <button
                    className="lp-contact-popup-toggle"
                    onClick={() => setContactOpen(!contactOpen)}
                >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                        <polyline points="22,6 12,13 2,6" />
                    </svg>
                    <span>{contactOpen ? 'Close' : 'Contact Us'}</span>
                    <svg
                        width="12"
                        height="12"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className={`lp-contact-popup-chevron ${contactOpen ? 'lp-contact-popup-chevron--open' : ''}`}
                    >
                        <polyline points="18 15 12 9 6 15" />
                    </svg>
                </button>
                {contactOpen && (
                    <div className="lp-contact-popup-body">
                        <div className="lp-contact-popup-row">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                                <polyline points="22,6 12,13 2,6" />
                            </svg>
                            <span>hello@sizzle.ai</span>
                        </div>
                        <div className="lp-contact-popup-row">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
                            </svg>
                            <span>+91 98765 43210</span>
                        </div>
                        <div className="lp-contact-popup-row">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                                <circle cx="12" cy="10" r="3" />
                            </svg>
                            <span>Pune, Maharashtra, India</span>
                        </div>
                        <button className="lp-contact-popup-btn" onClick={() => navigate('/contact')}>
                            Full Contact Page
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></svg>
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}

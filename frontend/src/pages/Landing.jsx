import { useNavigate, useLocation } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import BlurText from '../components/BlurText'
import TypewriterText from '../components/TypewriterText'
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
    const location = useLocation()
    const { t, language } = useTranslation()
    const [activeSlide, setActiveSlide] = useState(0)
    const [fadeClass, setFadeClass] = useState('lp-slide-visible')
    const [titleLoaded, setTitleLoaded] = useState(false)
    const intervalRef = useRef(null)

    // Scroll to hash section when navigating from another page (e.g. /about → /#features)
    useEffect(() => {
        if (location.hash) {
            const id = location.hash.replace('#', '')
            setTimeout(() => {
                const el = document.getElementById(id)
                if (el) el.scrollIntoView({ behavior: 'smooth' })
            }, 100)
        }
    }, [location.hash])
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

    const nextSlide = () => {
        clearInterval(intervalRef.current)
        changeSlide((prev) => (prev + 1) % heroImages.length)
    }

    const prevSlide = () => {
        clearInterval(intervalRef.current)
        changeSlide((prev) => (prev - 1 + heroImages.length) % heroImages.length)
    }

    return (
        <div className="lp">
            {/* Shared Navbar */}
            <Navbar />

            {/* Hero */}
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

                    <div className="lp-hero-line" />

                    <p className="lp-hero-desc">
                        {t('hero_desc')}
                    </p>

                    <button className="lp-cta lp-cta-pill" onClick={() => navigate('/login')}>
                        {t('hero_cta')}
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></svg>
                    </button>
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

            {/* Marquee */}
            <section className="lp-marquee-section">
                <p className="lp-marquee-label">{t('hero_marquee')}</p>
                <div className="lp-marquee-track">
                    <div className="lp-marquee-content">
                        {[
                            'Bombay Brasserie',
                            'The Curry Collective',
                            'Tandoor Royale',
                            'Spice Republic',
                            'Naan & Kabab Co.',
                            'The Saffron Table',
                            'Masala Street',
                            'Charcoal Kitchen',
                            'Zest Dining',
                            'The Mughal Room',
                            'Flames & Grill',
                            'Peshawari House',
                        ].map((name, i) => (
                            <span key={i} className="lp-marquee-item">
                                <span className="lp-marquee-name">{name}</span>
                                <span className="lp-marquee-dot" />
                            </span>
                        ))}
                    </div>
                    {/* Duplicate for seamless loop */}
                    <div className="lp-marquee-content" aria-hidden="true">
                        {[
                            'Bombay Brasserie',
                            'The Curry Collective',
                            'Tandoor Royale',
                            'Spice Republic',
                            'Naan & Kabab Co.',
                            'The Saffron Table',
                            'Masala Street',
                            'Charcoal Kitchen',
                            'Zest Dining',
                            'The Mughal Room',
                            'Flames & Grill',
                            'Peshawari House',
                        ].map((name, i) => (
                            <span key={`dup-${i}`} className="lp-marquee-item">
                                <span className="lp-marquee-name">{name}</span>
                                <span className="lp-marquee-dot" />
                            </span>
                        ))}
                    </div>
                </div>
            </section>

            {/* Features Strip */}
            <section className="lp-features" id="features">
                <div className="lp-features-inner">
                    {[
                        { num: '01', titleKey: 'feature_1_title', descKey: 'feature_1_desc' },
                        { num: '02', titleKey: 'feature_2_title', descKey: 'feature_2_desc' },
                        { num: '03', titleKey: 'feature_3_title', descKey: 'feature_3_desc' },
                        { num: '04', titleKey: 'feature_4_title', descKey: 'feature_4_desc' },
                    ].map((f, i) => (
                        <div key={i} className="lp-feature-item">
                            <span className="lp-feature-num">{f.num}</span>
                            <h3>{t(f.titleKey)}</h3>
                            <p>{t(f.descKey)}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* About */}
            <section className="lp-about" id="about">
                <div className="lp-about-inner">
                    <div className="lp-about-image">
                        <img src="/images/hero2.png" alt="About Sizzle" />
                    </div>
                    <div className="lp-about-content">
                        <span className="lp-section-tag">{t('about_tag')}</span>
                        <h2>{t('about_heading_1')}<br /><span className="lp-accent">{t('about_heading_2')}</span></h2>
                        <p>{t('about_desc')}</p>
                        <div className="lp-stats-row">
                            <div className="lp-stat">
                                <span className="lp-stat-value">2,400+</span>
                                <span className="lp-stat-label">{t('stat_restaurants')}</span>
                            </div>
                            <div className="lp-stat">
                                <span className="lp-stat-value">18%</span>
                                <span className="lp-stat-label">{t('stat_uplift')}</span>
                            </div>
                            <div className="lp-stat">
                                <span className="lp-stat-value">5</span>
                                <span className="lp-stat-label">{t('stat_languages')}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="lp-cta-section">
                <h2>{t('cta_heading')}</h2>
                <p>{t('cta_sub')}</p>
                <button className="lp-cta" onClick={() => navigate('/login')}>
                    {t('cta_btn')}
                </button>
            </section>

            {/* Contact Section */}
            <section className="lp-contact-section" id="contact">
                <div className="lp-contact-inner">
                    <div className="lp-contact-info">
                        <span className="lp-section-tag">{t('contact_tag')}</span>
                        <h2>{t('contact_heading')}</h2>
                        <p>{t('contact_desc')}</p>
                        <div className="lp-contact-details">
                            <div className="lp-contact-item">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                                    <polyline points="22,6 12,13 2,6" />
                                </svg>
                                <span>hello@sizzle.ai</span>
                            </div>
                            <div className="lp-contact-item">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
                                </svg>
                                <span>+91 98765 43210</span>
                            </div>
                            <div className="lp-contact-item">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                                    <circle cx="12" cy="10" r="3" />
                                </svg>
                                <span>Pune, Maharashtra, India</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="lp-footer">
                <div className="lp-footer-inner">
                    <div className="lp-footer-brand">
                        <span className="lp-footer-logo">SIZZLE</span>
                        <p>{t('footer_desc')}</p>
                    </div>
                    <div className="lp-footer-links">
                        <div>
                            <h4>{t('footer_product')}</h4>
                            <a href="#features">Features</a>
                            <a href="#">Pricing</a>
                            <a href="#">API Docs</a>
                        </div>
                        <div>
                            <h4>{t('footer_company')}</h4>
                            <a href="/about">About</a>
                            <a href="#">Careers</a>
                            <a href="#">Blog</a>
                        </div>
                        <div>
                            <h4>{t('footer_support')}</h4>
                            <a href="#">Help Center</a>
                            <a href="#contact">Contact</a>
                            <a href="#">Status</a>
                        </div>
                    </div>
                </div>
                <div className="lp-footer-bottom">
                    &copy; 2026 Sizzle Technologies Pvt. Ltd. All rights reserved.
                </div>
            </footer>
        </div>
    )
}

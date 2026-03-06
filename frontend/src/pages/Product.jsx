import { useNavigate } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import Navbar from '../components/Navbar'
import { useTranslation } from '../context/LanguageContext'

// Hook for scroll-triggered reveal animations
function useScrollReveal() {
    const ref = useRef(null)
    const [isVisible, setIsVisible] = useState(false)

    useEffect(() => {
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setIsVisible(true)
                    observer.unobserve(entry.target)
                }
            },
            { threshold: 0.15 }
        )
        if (ref.current) observer.observe(ref.current)
        return () => observer.disconnect()
    }, [])

    return [ref, isVisible]
}

const features = [
    {
        num: '01',
        titleKey: 'feature_1_title',
        descKey: 'feature_1_desc',
        icon: (
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
        ),
        details: [
            'Real-time contribution margin tracking',
            'Menu health scoring across your entire catalogue',
            'Automatic cost-vs-price analysis per dish',
            'Revenue trend dashboards with AI insights',
        ],
    },
    {
        num: '02',
        titleKey: 'feature_2_title',
        descKey: 'feature_2_desc',
        icon: (
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
        ),
        details: [
            'Supports English, Hindi, Hinglish, Marathi, Kannada & Gujarati',
            'Noise-robust speech recognition for kitchen environments',
            'Auto-generates KOT tickets from voice commands',
            'Works hands-free — no touching screens during rush hours',
        ],
    },
    {
        num: '03',
        titleKey: 'feature_3_title',
        descKey: 'feature_3_desc',
        icon: (
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7" />
                <rect x="14" y="3" width="7" height="7" />
                <rect x="14" y="14" width="7" height="7" />
                <rect x="3" y="14" width="7" height="7" />
            </svg>
        ),
        details: [
            'Classify every dish: Star, Hidden Star, Workhorse, or Dog',
            'Identify high-margin items that deserve more promotion',
            'Spot underperformers dragging down your menu',
            'Data-driven recommendations — not guesswork',
        ],
    },
    {
        num: '04',
        titleKey: 'feature_4_title',
        descKey: 'feature_4_desc',
        icon: (
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <path d="M8 14s1.5 2 4 2 4-2 4-2" />
                <line x1="9" y1="9" x2="9.01" y2="9" />
                <line x1="15" y1="9" x2="15.01" y2="9" />
            </svg>
        ),
        details: [
            'Auto-generated combo bundles from real order patterns',
            'Boost average ticket size by up to 22%',
            'Dynamic pricing suggestions based on demand',
            'Works seamlessly with your existing POS',
        ],
    },
]

export default function Product() {
    const navigate = useNavigate()
    const { t } = useTranslation()

    // Create individual refs for each feature
    const [ref0, vis0] = useScrollReveal()
    const [ref1, vis1] = useScrollReveal()
    const [ref2, vis2] = useScrollReveal()
    const [ref3, vis3] = useScrollReveal()
    const [ctaRef, ctaVis] = useScrollReveal()
    const refs = [ref0, ref1, ref2, ref3]
    const visible = [vis0, vis1, vis2, vis3]

    return (
        <div className="lp">
            <Navbar />

            {/* Product Hero */}
            <section className="pp-hero">
                <div className="pp-hero-inner">
                    <span className="lp-section-tag">THE PLATFORM</span>
                    <h1 className="pp-hero-title">
                        Everything your restaurant<br />
                        <span className="lp-accent">needs to grow.</span>
                    </h1>
                    <p className="pp-hero-desc">
                        Four powerful AI modules working together to boost your revenue,
                        streamline operations, and delight your customers.
                    </p>
                </div>
            </section>

            {/* Feature Sections */}
            {features.map((f, i) => (
                <section
                    key={f.num}
                    className={`pp-feature-section lp-reveal ${visible[i] ? 'lp-reveal--visible' : ''} ${i % 2 === 1 ? 'pp-feature--alt' : ''}`}
                    ref={refs[i]}
                >
                    <div className="pp-feature-inner">
                        <div className="pp-feature-left">
                            <div className="pp-feature-icon-wrap">
                                {f.icon}
                            </div>
                            <span className="pp-feature-num">{f.num}</span>
                            <h2 className="pp-feature-title">{t(f.titleKey)}</h2>
                            <p className="pp-feature-desc">{t(f.descKey)}</p>
                        </div>
                        <div className="pp-feature-right">
                            <ul className="pp-feature-list">
                                {f.details.map((detail, j) => (
                                    <li key={j}>
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                            <polyline points="20 6 9 17 4 12" />
                                        </svg>
                                        <span>{detail}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </section>
            ))}

            {/* CTA */}
            <section
                className={`pp-cta lp-reveal ${ctaVis ? 'lp-reveal--visible' : ''}`}
                ref={ctaRef}
            >
                <h2>Ready to see Sizzle in action?</h2>
                <p>Start your free trial today and transform your restaurant.</p>
                <button className="lp-cta lp-cta-pill" onClick={() => navigate('/login')}>
                    GET STARTED FREE
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></svg>
                </button>
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
                            <a href="/product">Features</a>
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

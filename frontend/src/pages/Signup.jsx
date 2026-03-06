import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import Navbar from '../components/Navbar'
import { useTranslation } from '../context/LanguageContext'

const plans = [
    {
        name: 'Starter',
        price: '₹4,999',
        period: '/month',
        desc: 'Perfect for single-outlet restaurants getting started with AI.',
        features: [
            'Revenue Intelligence Dashboard',
            'Menu Matrix Analysis',
            'Up to 50 menu items',
            'Email support',
        ],
        highlight: false,
    },
    {
        name: 'Growth',
        price: '₹12,999',
        period: '/month',
        desc: 'For growing restaurants needing full AI capabilities.',
        features: [
            'Everything in Starter',
            'Voice Ordering (5 languages)',
            'Smart Combo Engine',
            'Unlimited menu items',
            'Multi-outlet support (up to 5)',
            'Priority support',
        ],
        highlight: true,
    },
    {
        name: 'Enterprise',
        price: 'Custom',
        period: '',
        desc: 'For chains and franchises with custom requirements.',
        features: [
            'Everything in Growth',
            'Unlimited outlets',
            'Custom integrations',
            'Dedicated account manager',
            'On-premise deployment option',
            'SLA guarantee',
        ],
        highlight: false,
    },
]

export default function Signup() {
    const navigate = useNavigate()
    const { t } = useTranslation()

    return (
        <div className="lp">
            <Navbar />

            {/* Hero */}
            <section className="su-hero">
                <div className="su-hero-inner">
                    <span className="lp-section-tag">GET STARTED</span>
                    <h1 className="su-hero-title">
                        Choose the right plan<br />
                        <span className="lp-accent">for your restaurant.</span>
                    </h1>
                    <p className="su-hero-desc">
                        Sizzle is currently available via managed onboarding.
                        Pick a plan below and our team will get you set up.
                    </p>
                </div>
            </section>

            {/* Plans */}
            <section className="su-plans">
                <div className="su-plans-grid">
                    {plans.map((plan, i) => (
                        <motion.div
                            key={plan.name}
                            className={`su-plan-card ${plan.highlight ? 'su-plan-card--highlight' : ''}`}
                            initial={{ opacity: 0, y: 30 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: 0.2 + i * 0.1 }}
                        >
                            {plan.highlight && <span className="su-plan-badge">MOST POPULAR</span>}
                            <h3 className="su-plan-name">{plan.name}</h3>
                            <div className="su-plan-price">
                                <span className="su-plan-amount">{plan.price}</span>
                                {plan.period && <span className="su-plan-period">{plan.period}</span>}
                            </div>
                            <p className="su-plan-desc">{plan.desc}</p>
                            <ul className="su-plan-features">
                                {plan.features.map((f, j) => (
                                    <li key={j}>
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                            <polyline points="20 6 9 17 4 12" />
                                        </svg>
                                        <span>{f}</span>
                                    </li>
                                ))}
                            </ul>
                            <button
                                className={`su-plan-btn ${plan.highlight ? 'su-plan-btn--primary' : ''}`}
                                onClick={() => navigate('/contact')}
                            >
                                Contact for Setup
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></svg>
                            </button>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* Info note */}
            <section className="su-info">
                <div className="su-info-inner">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="16" x2="12" y2="12" />
                        <line x1="12" y1="8" x2="12.01" y2="8" />
                    </svg>
                    <div>
                        <h4>Why managed onboarding?</h4>
                        <p>
                            We personally set up every restaurant to ensure your menu data,
                            voice models, and analytics are calibrated perfectly. Our team handles
                            the entire integration so you can focus on your kitchen.
                        </p>
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
                            <a href="/product">Features</a>
                            <a href="#">Pricing</a>
                        </div>
                        <div>
                            <h4>{t('footer_company')}</h4>
                            <a href="/about">About</a>
                            <a href="/contact">Contact</a>
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

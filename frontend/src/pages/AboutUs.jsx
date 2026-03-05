import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import Navbar from '../components/Navbar'
import { useTranslation } from '../context/LanguageContext'

export default function AboutUs() {
    const navigate = useNavigate()
    const { t } = useTranslation()

    useEffect(() => {
        window.scrollTo(0, 0)
    }, [])

    return (
        <div className="lp">
            <Navbar />

            {/* Hero Banner */}
            <section className="about-hero">
                <div className="about-hero-inner">
                    <span className="lp-section-tag">{t('about_hero_tag')}</span>
                    <h1 className="about-hero-title">
                        {t('about_hero_title_1')}<br />
                        <span className="lp-accent">{t('about_hero_title_2')}</span>
                    </h1>
                    <p className="about-hero-sub">{t('about_hero_sub')}</p>
                </div>
            </section>

            {/* Timeline */}
            <section className="about-section">
                <div className="about-section-inner">
                    {[
                        { year: '2022', titleKey: 'about_2022_title', descKey: 'about_2022_desc' },
                        { year: '2023', titleKey: 'about_2023_title', descKey: 'about_2023_desc' },
                        { year: '2024', titleKey: 'about_2024_title', descKey: 'about_2024_desc' },
                        { year: '2025', titleKey: 'about_2025_title', descKey: 'about_2025_desc' },
                    ].map((item) => (
                        <div key={item.year} className="about-block">
                            <span className="about-year">{item.year}</span>
                            <h2>{t(item.titleKey)}</h2>
                            <p>{t(item.descKey)}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* Core Values */}
            <section className="about-values-section">
                <div className="about-values-inner">
                    <span className="lp-section-tag">{t('about_values_tag')}</span>
                    <h2 className="about-values-title">{t('about_values_title')}</h2>

                    <div className="about-values-grid">
                        <div className="about-value-card">
                            <div className="about-value-icon">
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
                                </svg>
                            </div>
                            <h3>{t('about_value_1_title')}</h3>
                            <p>{t('about_value_1_desc')}</p>
                        </div>
                        <div className="about-value-card">
                            <div className="about-value-icon">
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                    <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" />
                                </svg>
                            </div>
                            <h3>{t('about_value_2_title')}</h3>
                            <p>{t('about_value_2_desc')}</p>
                        </div>
                        <div className="about-value-card">
                            <div className="about-value-icon">
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                    <circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10A15.3 15.3 0 0 1 12 2z" />
                                </svg>
                            </div>
                            <h3>{t('about_value_3_title')}</h3>
                            <p>{t('about_value_3_desc')}</p>
                        </div>
                        <div className="about-value-card">
                            <div className="about-value-icon">
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                                </svg>
                            </div>
                            <h3>{t('about_value_4_title')}</h3>
                            <p>{t('about_value_4_desc')}</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Numbers */}
            <section className="about-numbers-section">
                <div className="about-numbers-inner">
                    <div className="about-number-item">
                        <span className="about-number-value">2,400+</span>
                        <span className="about-number-label">{t('about_num_restaurants')}</span>
                    </div>
                    <div className="about-number-item">
                        <span className="about-number-value">5</span>
                        <span className="about-number-label">{t('about_num_languages')}</span>
                    </div>
                    <div className="about-number-item">
                        <span className="about-number-value">18%</span>
                        <span className="about-number-label">{t('about_num_uplift')}</span>
                    </div>
                    <div className="about-number-item">
                        <span className="about-number-value">4</span>
                        <span className="about-number-label">{t('about_num_cities')}</span>
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="lp-cta-section">
                <h2>{t('about_cta_heading')}</h2>
                <p>{t('about_cta_sub')}</p>
                <button className="lp-cta" onClick={() => navigate('/login')}>
                    {t('cta_btn')}
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
                            <a href="/#features">Features</a>
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
                            <a href="/#contact">Contact</a>
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

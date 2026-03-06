import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import { useTranslation } from '../context/LanguageContext'

export default function Contact() {
    const navigate = useNavigate()
    const { t } = useTranslation()
    const [form, setForm] = useState({ name: '', email: '', message: '' })
    const [submitted, setSubmitted] = useState(false)

    const handleSubmit = (e) => {
        e.preventDefault()
        // In a real app this would send an API request
        setSubmitted(true)
        setTimeout(() => setSubmitted(false), 3000)
        setForm({ name: '', email: '', message: '' })
    }

    return (
        <div className="lp">
            <Navbar />

            <section className="ct-page">
                <div className="ct-inner">
                    {/* Left — info */}
                    <div className="ct-info">
                        <span className="lp-section-tag">{t('contact_tag')}</span>
                        <h1 className="ct-title">{t('contact_heading')}</h1>
                        <p className="ct-desc">{t('contact_desc')}</p>

                        <div className="ct-details">
                            <div className="ct-detail-item">
                                <div className="ct-icon-wrap">
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                                        <polyline points="22,6 12,13 2,6" />
                                    </svg>
                                </div>
                                <div>
                                    <span className="ct-detail-label">Email</span>
                                    <span className="ct-detail-value">hello@sizzle.ai</span>
                                </div>
                            </div>
                            <div className="ct-detail-item">
                                <div className="ct-icon-wrap">
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
                                    </svg>
                                </div>
                                <div>
                                    <span className="ct-detail-label">Phone</span>
                                    <span className="ct-detail-value">+91 98765 43210</span>
                                </div>
                            </div>
                            <div className="ct-detail-item">
                                <div className="ct-icon-wrap">
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                                        <circle cx="12" cy="10" r="3" />
                                    </svg>
                                </div>
                                <div>
                                    <span className="ct-detail-label">Office</span>
                                    <span className="ct-detail-value">Pune, Maharashtra, India</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right — form */}
                    <div className="ct-form-wrap">
                        <form className="ct-form" onSubmit={handleSubmit}>
                            <h3>Send us a message</h3>
                            <div className="ct-field">
                                <label htmlFor="ct-name">Name</label>
                                <input
                                    id="ct-name"
                                    type="text"
                                    placeholder="Your name"
                                    value={form.name}
                                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    required
                                />
                            </div>
                            <div className="ct-field">
                                <label htmlFor="ct-email">Email</label>
                                <input
                                    id="ct-email"
                                    type="email"
                                    placeholder="you@example.com"
                                    value={form.email}
                                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                                    required
                                />
                            </div>
                            <div className="ct-field">
                                <label htmlFor="ct-message">Message</label>
                                <textarea
                                    id="ct-message"
                                    rows="4"
                                    placeholder="How can we help?"
                                    value={form.message}
                                    onChange={(e) => setForm({ ...form, message: e.target.value })}
                                    required
                                />
                            </div>
                            <button type="submit" className="ct-submit">
                                {submitted ? 'Sent!' : 'Send Message'}
                                {!submitted && (
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></svg>
                                )}
                            </button>
                        </form>
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

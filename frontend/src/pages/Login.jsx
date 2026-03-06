import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import LightRays from '../components/LightRays'
import { motion } from 'motion/react'
import { useAuth } from '../context/AuthContext'
import { useTranslation } from '../context/LanguageContext'
import './Login.css'

export default function Login() {
    const navigate = useNavigate()
    const { login } = useAuth()
    const { t } = useTranslation()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState('')

    const handleLogin = async (e) => {
        e.preventDefault()
        if (!email || !password) {
            setError(t('login_error_fields'))
            return
        }
        setError('')
        setLoading(true)

        setTimeout(() => {
            setLoading(false)
            login()
            navigate('/dashboard')
        }, 1200)
    }

    return (
        <div className="login-root">
            <motion.a
                href="#"
                className="login-back-btn"
                onClick={(e) => { e.preventDefault(); navigate('/'); }}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.3 }}
            >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5" /><path d="M12 19l-7-7 7-7" /></svg>
                {t('login_back')}
            </motion.a>

            {/* The interactive LightRays page background */}
            <div style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
                <div style={{ position: 'absolute', inset: 0 }}>
                    <LightRays
                        raysOrigin="left"
                        raysColor="#ffffff"
                        raysSpeed={1}
                        lightSpread={0.5}
                        rayLength={3}
                        followMouse={true}
                        mouseInfluence={0.1}
                        noiseAmount={0}
                        distortion={0}
                        pulsating={false}
                        fadeDistance={1}
                        saturation={1}
                    />
                </div>
                <div style={{ position: 'absolute', inset: 0, opacity: 0.8 }}>
                    <LightRays
                        raysOrigin="right"
                        raysColor="#ffffff"
                        raysSpeed={1}
                        lightSpread={0.5}
                        rayLength={3}
                        followMouse={true}
                        mouseInfluence={0.1}
                        noiseAmount={0}
                        distortion={0}
                        pulsating={false}
                        fadeDistance={1}
                        saturation={1}
                    />
                </div>
            </div>

            <motion.div
                className="login-glass-card"
                initial={{ opacity: 0, y: 40, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
                {/* ─── LEFT SIDE ─── */}
                <div className="login-side-left">
                    <motion.p
                        className="login-left-subtitle"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5, duration: 0.5 }}
                    >
                        {t('login_left_sub')}
                    </motion.p>
                    <motion.h2
                        className="login-left-title"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.7, duration: 0.6 }}
                    >
                        {t('login_left_title_1')}<br />
                        {t('login_left_title_2')}
                    </motion.h2>
                </div>

                {/* ─── RIGHT SIDE ─── */}
                <div className="login-side-right">
                    {/* Header */}
                    <div className="login-header">
                        <div className="login-brand" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
                            <div className="login-logo-circle"></div>
                            <span className="login-logo-text">Sizzle</span>
                        </div>
                        <a href="#" className="login-signup-btn">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
                            </svg>
                            {t('login_signup')}
                        </a>
                    </div>

                    {/* Form Area */}
                    <motion.div
                        className="login-form-area"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4, duration: 0.5 }}
                    >
                        <motion.h1
                            initial={{ opacity: 0, y: 15 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.5, duration: 0.4 }}
                        >
                            {t('login_signin')}
                        </motion.h1>

                        <form onSubmit={handleLogin}>
                            {error && (
                                <motion.div
                                    style={{ color: '#ff6b35', fontSize: '13px', marginBottom: '16px', fontWeight: 600 }}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                >
                                    {error}
                                </motion.div>
                            )}

                            <motion.div
                                className="login-form-group"
                                initial={{ opacity: 0, y: 15 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.6, duration: 0.4 }}
                            >
                                <input
                                    type="text"
                                    className="login-input"
                                    placeholder={t('login_email_placeholder')}
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    autoComplete="username"
                                />
                            </motion.div>

                            <motion.div
                                className="login-form-group"
                                initial={{ opacity: 0, y: 15 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.7, duration: 0.4 }}
                            >
                                <input
                                    type={showPassword ? "text" : "password"}
                                    className="login-input"
                                    placeholder={t('login_password_placeholder')}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    autoComplete="current-password"
                                />
                                <button
                                    type="button"
                                    className="login-input-icon"
                                    onClick={() => setShowPassword(!showPassword)}
                                    aria-label="Toggle password visibility"
                                >
                                    {showPassword ? (
                                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" /><line x1="1" y1="1" x2="23" y2="23" /></svg>
                                    ) : (
                                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>
                                    )}
                                </button>
                            </motion.div>

                            <motion.a
                                href="#"
                                className="login-forgot-link"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 0.8, duration: 0.4 }}
                            >
                                {t('login_forgot')}
                            </motion.a>

                            <motion.button
                                type="submit"
                                className="login-submit-btn"
                                disabled={loading}
                                initial={{ opacity: 0, y: 15 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.9, duration: 0.4 }}
                                whileHover={{ scale: 1.02, y: -2 }}
                                whileTap={{ scale: 0.98 }}
                            >
                                {loading ? t('login_signing_in') : (
                                    <>
                                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 8l4 4-4 4" /><path d="M4 12h14" /></svg>
                                        {t('login_submit')}
                                    </>
                                )}
                            </motion.button>
                        </form>
                    </motion.div>

                    {/* Footer */}
                    <motion.div
                        className="login-footer-row"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 1, duration: 0.5 }}
                    >
                        <div>© 2024-2026 Sizzle Inc.</div>
                        <div className="login-footer-links">
                            <a href="#">Contact Us</a>
                            <a href="#" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                English
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
                            </a>
                        </div>
                    </motion.div>
                </div>
            </motion.div>
        </div>
    )
}

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import LightRays from '../components/LightRays'
import './Login.css'

export default function Login() {
    const navigate = useNavigate()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState('')

    const handleLogin = async (e) => {
        e.preventDefault()
        if (!email || !password) {
            setError('Please fill in all fields.')
            return
        }
        setError('')
        setLoading(true)

        setTimeout(() => {
            setLoading(false)
            navigate('/dashboard')
        }, 1200)
    }

    return (
        <div className="login-root">
            <a href="#" className="login-back-btn" onClick={(e) => { e.preventDefault(); navigate('/'); }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5" /><path d="M12 19l-7-7 7-7" /></svg>
                Back to Home
            </a>

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

            <div className="login-glass-card">
                {/* ─── LEFT SIDE ─── */}
                <div className="login-side-left">
                    <p className="login-left-subtitle">Sizzle AI — Your restaurant copilot.</p>
                    <h2 className="login-left-title">
                        Manage<br />
                        your restaurant
                    </h2>
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
                            Sign Up
                        </a>
                    </div>

                    {/* Form Area */}
                    <div className="login-form-area">
                        <h1>Sign In</h1>

                        <form onSubmit={handleLogin}>
                            {error && (
                                <div style={{ color: '#ff6b35', fontSize: '13px', marginBottom: '16px', fontWeight: 600 }}>{error}</div>
                            )}

                            <div className="login-form-group">
                                <input
                                    type="text"
                                    className="login-input"
                                    placeholder="Email or Username"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    autoComplete="username"
                                />
                            </div>

                            <div className="login-form-group">
                                <input
                                    type={showPassword ? "text" : "password"}
                                    className="login-input"
                                    placeholder="Password"
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
                            </div>

                            <a href="#" className="login-forgot-link">Forgot password?</a>

                            <button
                                type="submit"
                                className="login-submit-btn"
                                disabled={loading}
                            >
                                {loading ? 'Signing in...' : (
                                    <>
                                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 8l4 4-4 4" /><path d="M4 12h14" /></svg>
                                        Sign In
                                    </>
                                )}
                            </button>
                        </form>
                    </div>

                    {/* Footer */}
                    <div className="login-footer-row">
                        <div>© 2024-2026 Sizzle Inc.</div>
                        <div className="login-footer-links">
                            <a href="#">Contact Us</a>
                            <a href="#" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                English
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

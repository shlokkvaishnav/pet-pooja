import { useNavigate } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import BlurText from '../components/BlurText'
import TypewriterText from '../components/TypewriterText'

const heroImages = [
    '/images/hero1.png',
    '/images/hero2.png',
    '/images/hero3.png',
]

export default function Landing() {
    const navigate = useNavigate()
    const [activeSlide, setActiveSlide] = useState(0)
    const [fadeClass, setFadeClass] = useState('lp-slide-visible')
    const [titleLoaded, setTitleLoaded] = useState(false)
    const intervalRef = useRef(null)

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
            {/* Floating Island Nav */}
            <nav className="lp-nav">
                <div className="lp-nav-island">
                    <a href="#" className="lp-nav-link">HOME</a>
                    <a href="#about" className="lp-nav-link">ABOUT US</a>
                    <a href="#" className="lp-nav-link">LOCATION</a>
                    <a href="#" className="lp-nav-link">CONTACT</a>
                    <button className="lp-nav-dashboard" onClick={() => navigate('/login')}>
                        VIEW DASHBOARD
                    </button>
                </div>
            </nav>

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
                            baseText="Your True Revenue Intelligence "
                            words={["Companion", "Assistant", "Copilot"]}
                            start={titleLoaded}
                            typeDelay={45}
                            deleteDelay={20}
                            pauseTime={600}
                        />
                    </div>

                    <div className="lp-hero-line" />

                    <p className="lp-hero-desc">
                        Sizzle is the all-in-one AI-powered platform for modern restaurants.
                        From real-time revenue intelligence to voice-powered ordering in
                        English, Hindi and Hinglish — take control of your kitchen, your
                        menu, and your margins.
                    </p>

                    <button className="lp-cta lp-cta-pill" onClick={() => navigate('/login')}>
                        EXPLORE THE PLATFORM
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
                <p className="lp-marquee-label">TRUSTED BY YOUR FAVOURITE RESTAURANT GIANTS</p>
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
                        { num: '01', title: 'Revenue Intelligence', desc: 'Real-time margin analysis and menu health scoring across your entire catalogue.' },
                        { num: '02', title: 'Voice Ordering', desc: 'AI-powered speech recognition. Take orders in English, Hindi, or Hinglish — hands free.' },
                        { num: '03', title: 'Menu Matrix', desc: 'Classify every dish as Star, Hidden Star, Workhorse or Dog. Act on data, not gut.' },
                        { num: '04', title: 'Smart Combos', desc: 'Auto-generated combo bundles from real order patterns. Boost ticket size effortlessly.' },
                    ].map((f, i) => (
                        <div key={i} className="lp-feature-item">
                            <span className="lp-feature-num">{f.num}</span>
                            <h3>{f.title}</h3>
                            <p>{f.desc}</p>
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
                        <span className="lp-section-tag">ABOUT SIZZLE</span>
                        <h2>Built for restaurants.<br /><span className="lp-accent">Powered by AI.</span></h2>
                        <p>
                            We built Sizzle because restaurant owners deserve better tools. Not another POS system — a true
                            revenue intelligence copilot. From hidden star discovery to automated KOT generation, every feature
                            is designed to increase margins and reduce friction in the kitchen.
                        </p>
                        <div className="lp-stats-row">
                            <div className="lp-stat">
                                <span className="lp-stat-value">2,400+</span>
                                <span className="lp-stat-label">Restaurants</span>
                            </div>
                            <div className="lp-stat">
                                <span className="lp-stat-value">18%</span>
                                <span className="lp-stat-label">Avg Revenue Uplift</span>
                            </div>
                            <div className="lp-stat">
                                <span className="lp-stat-value">3</span>
                                <span className="lp-stat-label">Languages Supported</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="lp-cta-section">
                <h2>Ready to transform your restaurant?</h2>
                <p>Join thousands of restaurant owners already using Sizzle.</p>
                <button className="lp-cta" onClick={() => navigate('/login')}>
                    GET STARTED FREE
                </button>
            </section>

            {/* Footer */}
            <footer className="lp-footer">
                <div className="lp-footer-inner">
                    <div className="lp-footer-brand">
                        <span className="lp-footer-logo">SIZZLE</span>
                        <p>AI-powered restaurant management for the modern kitchen.</p>
                    </div>
                    <div className="lp-footer-links">
                        <div>
                            <h4>Product</h4>
                            <a href="#features">Features</a>
                            <a href="#">Pricing</a>
                            <a href="#">API Docs</a>
                        </div>
                        <div>
                            <h4>Company</h4>
                            <a href="#about">About</a>
                            <a href="#">Careers</a>
                            <a href="#">Blog</a>
                        </div>
                        <div>
                            <h4>Support</h4>
                            <a href="#">Help Center</a>
                            <a href="#">Contact</a>
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

import { useNavigate } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import BlurText from '../components/BlurText'
import TypewriterText from '../components/TypewriterText'
import {
    motion, ScrollReveal, StaggerReveal, AnimatedNumber,
    fadeInUp, fadeInLeft, fadeInRight, staggerContainer, staggerItem,
    staggerContainerSlow, scaleIn, popIn, slideInFromLeft, slideInFromRight
} from '../utils/animations'

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
    const [navScrolled, setNavScrolled] = useState(false)
    const intervalRef = useRef(null)

    // Detect scroll to toggle nav
    useEffect(() => {
        const heroHeight = window.innerHeight
        const onScroll = () => setNavScrolled(window.scrollY > heroHeight * 0.7)
        window.addEventListener('scroll', onScroll, { passive: true })
        return () => window.removeEventListener('scroll', onScroll)
    }, [])

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
            {/* Full-width Nav — transparent in hero, glass after scroll */}
            <nav className={`lp-nav ${navScrolled ? 'lp-nav--scrolled' : ''}`}>
                {/* Logo */}
                <div className="lp-nav-logo" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
                    SIZZLE
                </div>

                {/* Links */}
                <div className="lp-nav-links">
                    <a href="#" className="lp-nav-link">HOME</a>
                    <a href="#about" className="lp-nav-link">ABOUT US</a>
                    <a href="#" className="lp-nav-link">LOCATION</a>
                    <a href="#" className="lp-nav-link">CONTACT</a>
                </div>

                {/* CTA */}
                <button className="lp-nav-dashboard" onClick={() => navigate('/login')}>
                    VIEW DASHBOARD
                </button>
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
                        Sizzle is the all-in-one AI-powered platform for modern restaurants.
                        From real-time revenue intelligence to voice-powered ordering in
                        English, Hindi and Hinglish — take control of your kitchen, your
                        menu, and your margins.
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
                        EXPLORE THE PLATFORM
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
                <StaggerReveal className="lp-features-inner" variants={staggerContainerSlow}>
                    {[
                        { num: '01', title: 'Revenue Intelligence', desc: 'Real-time margin analysis and menu health scoring across your entire catalogue.' },
                        { num: '02', title: 'Voice Ordering', desc: 'AI-powered speech recognition. Take orders in English, Hindi, or Hinglish — hands free.' },
                        { num: '03', title: 'Menu Matrix', desc: 'Classify every dish as Star, Hidden Star, Workhorse or Dog. Act on data, not gut.' },
                        { num: '04', title: 'Smart Combos', desc: 'Auto-generated combo bundles from real order patterns. Boost ticket size effortlessly.' },
                    ].map((f, i) => (
                        <motion.div key={i} className="lp-feature-item" variants={staggerItem}
                            whileHover={{ backgroundColor: 'rgba(22, 22, 22, 1)', transition: { duration: 0.3 } }}
                        >
                            <motion.span
                                className="lp-feature-num"
                                initial={{ opacity: 0, x: -10 }}
                                whileInView={{ opacity: 1, x: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.1 * i, duration: 0.4 }}
                            >
                                {f.num}
                            </motion.span>
                            <h3>{f.title}</h3>
                            <p>{f.desc}</p>
                        </motion.div>
                    ))}
                </StaggerReveal>
            </section>

            {/* About */}
            <section className="lp-about" id="about">
                <div className="lp-about-inner">
                    <ScrollReveal className="lp-about-image" variants={slideInFromLeft}>
                        <img src="/images/hero2.png" alt="About Sizzle" />
                    </ScrollReveal>
                    <ScrollReveal className="lp-about-content" variants={slideInFromRight}>
                        <motion.span className="lp-section-tag"
                            initial={{ opacity: 0, y: 10 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.4 }}
                        >
                            ABOUT SIZZLE
                        </motion.span>
                        <h2>Built for restaurants.<br /><span className="lp-accent">Powered by AI.</span></h2>
                        <p>
                            We built Sizzle because restaurant owners deserve better tools. Not another POS system — a true
                            revenue intelligence copilot. From hidden star discovery to automated KOT generation, every feature
                            is designed to increase margins and reduce friction in the kitchen.
                        </p>
                        <StaggerReveal className="lp-stats-row" variants={staggerContainer}>
                            <motion.div className="lp-stat" variants={staggerItem}>
                                <span className="lp-stat-value"><AnimatedNumber value={2400} prefix="" suffix="+" /></span>
                                <span className="lp-stat-label">Restaurants</span>
                            </motion.div>
                            <motion.div className="lp-stat" variants={staggerItem}>
                                <span className="lp-stat-value"><AnimatedNumber value={18} suffix="%" /></span>
                                <span className="lp-stat-label">Avg Revenue Uplift</span>
                            </motion.div>
                            <motion.div className="lp-stat" variants={staggerItem}>
                                <span className="lp-stat-value"><AnimatedNumber value={3} /></span>
                                <span className="lp-stat-label">Languages Supported</span>
                            </motion.div>
                        </StaggerReveal>
                    </ScrollReveal>
                </div>
            </section>

            {/* CTA */}
            <section className="lp-cta-section">
                <ScrollReveal variants={scaleIn}>
                    <h2>Ready to transform your restaurant?</h2>
                    <p>Join thousands of restaurant owners already using Sizzle.</p>
                    <motion.button
                        className="lp-cta"
                        onClick={() => navigate('/login')}
                        whileHover={{ scale: 1.05, y: -3 }}
                        whileTap={{ scale: 0.97 }}
                    >
                        GET STARTED FREE
                    </motion.button>
                </ScrollReveal>
            </section>

            {/* Footer */}
            <ScrollReveal>
                <footer className="lp-footer">
                    <StaggerReveal className="lp-footer-inner" variants={staggerContainer}>
                        <motion.div className="lp-footer-brand" variants={staggerItem}>
                            <span className="lp-footer-logo">SIZZLE</span>
                            <p>AI-powered restaurant management for the modern kitchen.</p>
                        </motion.div>
                        <motion.div className="lp-footer-links" variants={staggerItem}>
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
                        </motion.div>
                    </StaggerReveal>
                    <div className="lp-footer-bottom">
                        &copy; 2026 Sizzle Technologies Pvt. Ltd. All rights reserved.
                    </div>
                </footer>
            </ScrollReveal>
        </div>
    )
}

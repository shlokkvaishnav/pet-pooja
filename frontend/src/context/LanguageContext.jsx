import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import translations from '../i18n/translations'

const LANGUAGES = [
    { code: 'en', label: 'English', native: 'English' },
    { code: 'hi', label: 'Hindi', native: 'हिन्दी' },
    { code: 'mr', label: 'Marathi', native: 'मराठी' },
    { code: 'kn', label: 'Kannada', native: 'ಕನ್ನಡ' },
    { code: 'gu', label: 'Gujarati', native: 'ગુજરાતી' },
]

const LanguageContext = createContext()

export function LanguageProvider({ children }) {
    const [language, setLanguageState] = useState(() => {
        return localStorage.getItem('sizzle_lang') || 'en'
    })

    const setLanguage = (code) => {
        setLanguageState(code)
        localStorage.setItem('sizzle_lang', code)
    }

    const t = useCallback((key) => {
        const langData = translations[language] || translations.en
        return langData[key] ?? translations.en[key] ?? key
    }, [language])

    return (
        <LanguageContext.Provider value={{ language, setLanguage, LANGUAGES, t }}>
            {children}
        </LanguageContext.Provider>
    )
}

export function useLanguage() {
    const ctx = useContext(LanguageContext)
    if (!ctx) throw new Error('useLanguage must be used within LanguageProvider')
    return ctx
}

export function useTranslation() {
    const { t, language } = useLanguage()
    return { t, language }
}

export default LanguageContext

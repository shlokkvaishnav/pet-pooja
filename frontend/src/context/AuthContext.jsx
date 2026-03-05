import { createContext, useContext, useState } from 'react'

const AuthContext = createContext()

export function AuthProvider({ children }) {
    const [isLoggedIn, setIsLoggedIn] = useState(() => {
        return !!localStorage.getItem('sizzle_auth')
    })

    const login = () => {
        localStorage.setItem('sizzle_auth', 'true')
        setIsLoggedIn(true)
    }

    const logout = () => {
        localStorage.removeItem('sizzle_auth')
        setIsLoggedIn(false)
    }

    return (
        <AuthContext.Provider value={{ isLoggedIn, login, logout }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const ctx = useContext(AuthContext)
    if (!ctx) throw new Error('useAuth must be used within AuthProvider')
    return ctx
}

export default AuthContext

import { createContext, useContext, useState } from 'react'

const AuthContext = createContext()

export function AuthProvider({ children }) {
    const [isLoggedIn, setIsLoggedIn] = useState(() => {
        return !!localStorage.getItem('sizzle_auth')
    })

    const [restaurant, setRestaurant] = useState(() => {
        const saved = localStorage.getItem('sizzle_restaurant')
        if (!saved) return null
        try { return JSON.parse(saved) } catch { return null }
    })

    const login = (restaurantData) => {
        localStorage.setItem('sizzle_auth', 'true')
        localStorage.setItem('sizzle_restaurant', JSON.stringify(restaurantData))
        setRestaurant(restaurantData)
        setIsLoggedIn(true)
    }

    const logout = () => {
        localStorage.removeItem('sizzle_auth')
        localStorage.removeItem('sizzle_restaurant')
        setRestaurant(null)
        setIsLoggedIn(false)
    }

    return (
        <AuthContext.Provider value={{ isLoggedIn, restaurant, login, logout }}>
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

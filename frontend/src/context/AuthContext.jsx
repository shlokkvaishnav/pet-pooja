import { createContext, useContext, useState } from 'react'
import { RESTAURANT_STORAGE_KEY } from '../config'

const AuthContext = createContext()

export function AuthProvider({ children }) {
    const [isLoggedIn, setIsLoggedIn] = useState(() => {
        return !!localStorage.getItem('sizzle_auth')
    })

    const [restaurant, setRestaurant] = useState(() => {
        const saved = localStorage.getItem(RESTAURANT_STORAGE_KEY)
        if (!saved) return null
        try { return JSON.parse(saved) } catch { return null }
    })

    const login = (restaurantData) => {
        localStorage.setItem('sizzle_auth', 'true')
        localStorage.setItem(RESTAURANT_STORAGE_KEY, JSON.stringify(restaurantData))
        setRestaurant(restaurantData)
        setIsLoggedIn(true)
    }

    const logout = () => {
        localStorage.removeItem('sizzle_auth')
        localStorage.removeItem(RESTAURANT_STORAGE_KEY)
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

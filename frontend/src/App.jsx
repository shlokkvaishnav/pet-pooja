import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { LanguageProvider } from './context/LanguageContext'
import { AuthProvider } from './context/AuthContext'
import RequireAuth from './components/RequireAuth'
import DashboardLayout from './layouts/DashboardLayout'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import MenuAnalysis from './pages/MenuAnalysis'
import ComboEngine from './pages/ComboEngine'
import VoiceOrder from './pages/VoiceOrder'
import AboutUs from './pages/AboutUs'
import Product from './pages/Product'
import Contact from './pages/Contact'

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Landing />} />
            <Route path="/about" element={<AboutUs />} />
            <Route path="/product" element={<Product />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/login" element={<Login />} />

            {/* Dashboard routes (after login) */}
            <Route
              path="/dashboard"
              element={(
                <RequireAuth>
                  <DashboardLayout />
                </RequireAuth>
              )}
            >
              <Route index element={<Dashboard />} />
              <Route path="menu-analysis" element={<MenuAnalysis />} />
              <Route path="combos" element={<ComboEngine />} />
              <Route path="voice-order" element={<VoiceOrder />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </LanguageProvider>
  )
}

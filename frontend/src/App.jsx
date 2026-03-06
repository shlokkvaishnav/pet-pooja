import { BrowserRouter, Routes, Route, NavLink, Outlet } from 'react-router-dom'
import { LanguageProvider } from './context/LanguageContext'
import { AuthProvider } from './context/AuthContext'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import MenuAnalysis from './pages/MenuAnalysis'
import ComboEngine from './pages/ComboEngine'
import VoiceOrder from './pages/VoiceOrder'
import AboutUs from './pages/AboutUs'
import Product from './pages/Product'
import Contact from './pages/Contact'

function DashboardLayout() {
  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h2>🔥 Sizzle</h2>
          <p>Restaurant AI Copilot</p>
        </div>
        <ul className="nav-links">
          <li>
            <NavLink to="/dashboard" end>
              <span className="nav-icon">📊</span> Dashboard
            </NavLink>
          </li>
          <li>
            <NavLink to="/dashboard/menu-analysis">
              <span className="nav-icon">🎯</span> Menu Analysis
            </NavLink>
          </li>
          <li>
            <NavLink to="/dashboard/combos">
              <span className="nav-icon">🔗</span> Combo Engine
            </NavLink>
          </li>
          <li>
            <NavLink to="/dashboard/voice-order">
              <span className="nav-icon">🎙️</span> Voice Order
            </NavLink>
          </li>
        </ul>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}

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
            <Route path="/dashboard" element={<DashboardLayout />}>
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

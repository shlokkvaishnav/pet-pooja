import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { LanguageProvider } from './context/LanguageContext'
import { AuthProvider } from './context/AuthContext'
import { SettingsProvider } from './context/SettingsContext'
import ErrorBoundary from './components/ErrorBoundary'

const RequireAuth = lazy(() => import('./components/RequireAuth'))
const DashboardLayout = lazy(() => import('./layouts/DashboardLayout'))
const Landing = lazy(() => import('./pages/Landing'))
const Login = lazy(() => import('./pages/Login'))
const Signup = lazy(() => import('./pages/Signup'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const MenuAnalysis = lazy(() => import('./pages/MenuAnalysis'))
const ComboEngine = lazy(() => import('./pages/ComboEngine'))
const HiddenStars = lazy(() => import('./pages/HiddenStars'))
const VoiceOrder = lazy(() => import('./pages/VoiceOrder'))
const Orders = lazy(() => import('./pages/Orders'))
const Tables = lazy(() => import('./pages/Tables'))
const Inventory = lazy(() => import('./pages/Inventory'))
const Reports = lazy(() => import('./pages/Reports'))
const Settings = lazy(() => import('./pages/Settings'))
const AboutUs = lazy(() => import('./pages/AboutUs'))
const Product = lazy(() => import('./pages/Product'))
const Contact = lazy(() => import('./pages/Contact'))

function NotFound() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 12 }}>
      <div style={{ fontSize: 64, fontWeight: 800, color: 'var(--accent)' }}>404</div>
      <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>Page not found</p>
      <a href="/" style={{ fontSize: 13, color: 'var(--accent)', textDecoration: 'underline' }}>Go Home</a>
    </div>
  )
}

function RouteFallback() {
  return (
    <div className="loading" style={{ minHeight: '40vh' }}>
      <div className="spinner" /> Loading...
    </div>
  )
}

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <SettingsProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <ErrorBoundary>
          <Suspense fallback={<RouteFallback />}>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/about" element={<AboutUs />} />
              <Route path="/product" element={<Product />} />
              <Route path="/contact" element={<Contact />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/login" element={<Login />} />

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
                <Route path="hidden-stars" element={<HiddenStars />} />
                <Route path="combos" element={<ComboEngine />} />
                <Route path="voice-order" element={<VoiceOrder />} />
                <Route path="orders" element={<Orders />} />
                <Route path="tables" element={<Tables />} />
                <Route path="inventory" element={<Inventory />} />
                <Route path="reports" element={<Reports />} />
                <Route path="settings" element={<Settings />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
          </ErrorBoundary>
        </BrowserRouter>
        </SettingsProvider>
      </AuthProvider>
    </LanguageProvider>
  )
}

import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { LanguageProvider } from './context/LanguageContext'
import { AuthProvider } from './context/AuthContext'

const RequireAuth = lazy(() => import('./components/RequireAuth'))
const DashboardLayout = lazy(() => import('./layouts/DashboardLayout'))
const Landing = lazy(() => import('./pages/Landing'))
const Login = lazy(() => import('./pages/Login'))
const Signup = lazy(() => import('./pages/Signup'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const MenuAnalysis = lazy(() => import('./pages/MenuAnalysis'))
const ComboEngine = lazy(() => import('./pages/ComboEngine'))
const VoiceOrder = lazy(() => import('./pages/VoiceOrder'))
const Orders = lazy(() => import('./pages/Orders'))
const Tables = lazy(() => import('./pages/Tables'))
const Inventory = lazy(() => import('./pages/Inventory'))
const Reports = lazy(() => import('./pages/Reports'))
const Settings = lazy(() => import('./pages/Settings'))
const AboutUs = lazy(() => import('./pages/AboutUs'))
const Product = lazy(() => import('./pages/Product'))
const Contact = lazy(() => import('./pages/Contact'))

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
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
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
                <Route path="combos" element={<ComboEngine />} />
                <Route path="voice-order" element={<VoiceOrder />} />
                <Route path="orders" element={<Orders />} />
                <Route path="tables" element={<Tables />} />
                <Route path="inventory" element={<Inventory />} />
                <Route path="reports" element={<Reports />} />
                <Route path="settings" element={<Settings />} />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </LanguageProvider>
  )
}

import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import {
  LayoutDashboard, Target, Link2, ClipboardList,
  LayoutGrid, Archive, BarChart3, Settings, LogOut,
  ChevronsRight, Mic, Sparkles,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTranslation } from '../context/LanguageContext'

const navGroupsDef = [
  {
    labelKey: 'sidebar_intelligence',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, labelKey: 'sidebar_dashboard', end: true },
      { to: '/dashboard/menu-analysis', icon: Target, labelKey: 'sidebar_menu_analysis' },
      { to: '/dashboard/hidden-stars', icon: Sparkles, labelKey: 'sidebar_hidden_stars' },
    ],
  },
  {
    labelKey: 'sidebar_operations',
    items: [
      { to: '/dashboard/combos', icon: Link2, labelKey: 'sidebar_combos' },
      { to: '/dashboard/orders', icon: ClipboardList, labelKey: 'sidebar_orders' },
      { to: '/dashboard/tables', icon: LayoutGrid, labelKey: 'sidebar_tables' },
      { to: '/dashboard/inventory', icon: Archive, labelKey: 'sidebar_inventory' },
      { to: '/dashboard/reports', icon: BarChart3, labelKey: 'sidebar_reports' },
    ],
  },
  {
    labelKey: 'sidebar_system',
    items: [
      { to: '/dashboard/settings', icon: Settings, labelKey: 'sidebar_settings' },
    ],
  },
]

export default function DashboardLayout() {
  const [open, setOpen] = useState(true)
  const navigate = useNavigate()
  const location = useLocation()
  const { logout, restaurant } = useAuth()
  const { t } = useTranslation()
  const onVoiceOrderPage = location.pathname === '/dashboard/voice-order'

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <motion.nav
        className={`sidebar ${open ? '' : 'sidebar--collapsed'}`}
        initial={{ x: -220, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
      >
        {/* Brand */}
        <div className="sidebar-brand">
          <motion.div
            className="sidebar-brand-text"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2 }}
          >
            <div className="sidebar-brand-kicker">Sizzle</div>
          </motion.div>
        </div>

        {/* Nav items */}
        <ul className="nav-links">
          {navGroupsDef.map((group, gi) => (
            <li key={group.labelKey} style={{ listStyle: 'none' }}>
              {open && <div className="nav-group-label">{t(group.labelKey)}</div>}
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {group.items.map((item, i) => {
                  const label = t(item.labelKey)
                  return (
                  <motion.li
                    key={item.to}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.35 + (gi * 2 + i) * 0.06, duration: 0.3 }}
                  >
                    <NavLink
                      to={item.to}
                      end={item.end}
                      className={({ isActive }) => {
                        const states = []
                        if (isActive) states.push('active')
                        if (!open) states.push('nav-link--icon-only')
                        return states.join(' ')
                      }}
                      data-tooltip={!open ? label : undefined}
                      aria-label={!open ? label : undefined}
                    >
                      <span className="nav-icon">
                        <item.icon size={18} />
                      </span>
                      {open && <span className="nav-label">{label}</span>}
                    </NavLink>
                  </motion.li>
                  )
                })}
              </ul>
            </li>
          ))}
        </ul>

        {/* Footer */}
        <div className="sidebar-footer">
          <button
            className={`sidebar-logout ${!open ? 'sidebar-logout--icon' : ''}`}
            onClick={() => { logout(); navigate('/login') }}
            title={!open ? t('sidebar_logout') : undefined}
            aria-label={!open ? t('sidebar_logout') : undefined}
          >
            <LogOut size={16} />
            {open && <span>{t('sidebar_logout')}</span>}
          </button>
        </div>

        {/* Collapse toggle */}
        <button
          className="sidebar-toggle"
          onClick={() => setOpen(!open)}
          title={open ? t('sidebar_collapse_tip') : t('sidebar_expand')}
        >
          <ChevronsRight
            size={16}
            className={`sidebar-toggle-icon ${open ? 'sidebar-toggle-icon--flipped' : ''}`}
          />
          {open && <span className="sidebar-toggle-label">{t('sidebar_collapse')}</span>}
        </button>
      </motion.nav>

      {/* Main Content */}
      <main className={`main-content ${open ? '' : 'main-content--expanded'}`}>
        <div className="main-content-restaurant-bar">
          <span>{restaurant?.restaurant_name || restaurant?.name || 'Restaurant'}</span>
        </div>
        <Outlet />
      </main>

      {!onVoiceOrderPage && (
        <button
          className="dashboard-voice-fab"
          onClick={() => navigate('/dashboard/voice-order')}
          title={t('dash_start_voice_order')}
        >
          <Mic size={18} />
          <span>{t('dash_voice_order')}</span>
        </button>
      )}
    </div>
  )
}

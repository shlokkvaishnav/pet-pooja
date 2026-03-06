import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import {
  LayoutDashboard, Target, Link2, ClipboardList,
  LayoutGrid, Archive, BarChart3, Settings, LogOut,
  ChevronsRight, Mic,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const navGroups = [
  {
    label: 'Intelligence',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', end: true },
      { to: '/dashboard/menu-analysis', icon: Target, label: 'Menu Analysis' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { to: '/dashboard/combos', icon: Link2, label: 'Combo Engine' },
      { to: '/dashboard/orders', icon: ClipboardList, label: 'Orders' },
      { to: '/dashboard/tables', icon: LayoutGrid, label: 'Tables' },
      { to: '/dashboard/inventory', icon: Archive, label: 'Inventory' },
      { to: '/dashboard/reports', icon: BarChart3, label: 'Reports' },
    ],
  },
  {
    label: 'System',
    items: [
      { to: '/dashboard/settings', icon: Settings, label: 'Settings' },
    ],
  },
]

export default function DashboardLayout() {
  const [open, setOpen] = useState(true)
  const navigate = useNavigate()
  const location = useLocation()
  const { logout, restaurant } = useAuth()
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
          <div className="sidebar-brand-row">
            <div className="sidebar-logo">
              <span className="sidebar-logo-letter">
                {(restaurant?.restaurant_name || restaurant?.name || 'R').charAt(0).toUpperCase()}
              </span>
            </div>
            {open && (
              <motion.div
                className="sidebar-brand-text"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.2 }}
              >
                <div className="sidebar-brand-kicker">Sizzle</div>
                <h2>{restaurant?.restaurant_name || restaurant?.name || 'Restaurant'}</h2>
              </motion.div>
            )}
          </div>
        </div>

        {/* Nav items */}
        <ul className="nav-links">
          {navGroups.map((group, gi) => (
            <li key={group.label} style={{ listStyle: 'none' }}>
              {open && <div className="nav-group-label">{group.label}</div>}
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {group.items.map((item, i) => (
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
                      data-tooltip={!open ? item.label : undefined}
                      aria-label={!open ? item.label : undefined}
                    >
                      <span className="nav-icon">
                        <item.icon size={18} />
                      </span>
                      {open && <span className="nav-label">{item.label}</span>}
                    </NavLink>
                  </motion.li>
                ))}
              </ul>
            </li>
          ))}
        </ul>

        {/* Footer */}
        <div className="sidebar-footer">
          <button
            className={`sidebar-logout ${!open ? 'sidebar-logout--icon' : ''}`}
            onClick={() => { logout(); navigate('/login') }}
            title={!open ? 'Logout' : undefined}
            aria-label={!open ? 'Logout' : undefined}
          >
            <LogOut size={16} />
            {open && <span>Logout</span>}
          </button>
        </div>

        {/* Collapse toggle */}
        <button
          className="sidebar-toggle"
          onClick={() => setOpen(!open)}
          title={open ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          <ChevronsRight
            size={16}
            className={`sidebar-toggle-icon ${open ? 'sidebar-toggle-icon--flipped' : ''}`}
          />
          {open && <span className="sidebar-toggle-label">Collapse</span>}
        </button>
      </motion.nav>

      {/* Main Content */}
      <main className={`main-content ${open ? '' : 'main-content--expanded'}`}>
        <Outlet />
      </main>

      {!onVoiceOrderPage && (
        <button
          className="dashboard-voice-fab"
          onClick={() => navigate('/dashboard/voice-order')}
          title="Start Voice Order"
        >
          <Mic size={18} />
          <span>Voice Order</span>
        </button>
      )}
    </div>
  )
}

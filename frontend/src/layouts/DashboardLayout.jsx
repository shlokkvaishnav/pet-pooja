import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import {
  LayoutDashboard, Target, Link2, Mic, ClipboardList,
  LayoutGrid, Archive, BarChart3, Settings, LogOut,
  ChevronsRight, HelpCircle,
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
      { to: '/dashboard/voice-order', icon: Mic, label: 'Voice Order' },
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
  const { logout } = useAuth()

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
              <span className="sidebar-logo-letter">S</span>
            </div>
            {open && (
              <motion.div
                className="sidebar-brand-text"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.2 }}
              >
                <h2>Sizzle</h2>
                <p>Restaurant AI Copilot</p>
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
                    <NavLink to={item.to} end={item.end} title={!open ? item.label : undefined}>
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
          {open && (
            <button
              className="sidebar-logout"
              onClick={() => { logout(); navigate('/login') }}
            >
              <LogOut size={14} />
              Logout
            </button>
          )}
          {!open && (
            <button
              className="sidebar-logout sidebar-logout--icon"
              onClick={() => { logout(); navigate('/login') }}
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          )}
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
    </div>
  )
}

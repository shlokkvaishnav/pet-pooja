import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { ChartBar, Target, LinkSimple, Microphone, SignOut } from '@phosphor-icons/react'
import { useAuth } from '../context/AuthContext'

const navGroups = [
  {
    label: 'Intelligence',
    items: [
      { to: '/dashboard', icon: ChartBar, label: 'Dashboard', end: true },
      { to: '/dashboard/menu-analysis', icon: Target, label: 'Menu Analysis' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { to: '/dashboard/combos', icon: LinkSimple, label: 'Combo Engine' },
      { to: '/dashboard/voice-order', icon: Microphone, label: 'Voice Order' },
    ],
  },
]

export default function DashboardLayout() {
  const navigate = useNavigate()
  const { logout } = useAuth()

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <motion.aside
        className="sidebar"
        initial={{ x: -220, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
      >
        <motion.div
          className="sidebar-brand"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
        >
          <h2>Sizzle</h2>
          <p>Restaurant AI Copilot</p>
        </motion.div>

        <ul className="nav-links">
          {navGroups.map((group, gi) => (
            <li key={group.label} style={{ listStyle: 'none' }}>
              <div className="nav-group-label">{group.label}</div>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {group.items.map((item, i) => (
                  <motion.li
                    key={item.to}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.35 + (gi * 2 + i) * 0.08, duration: 0.35 }}
                  >
                    <NavLink to={item.to} end={item.end}>
                      <span className="nav-icon">
                        <item.icon size={18} weight="regular" />
                      </span>
                      <span>{item.label}</span>
                    </NavLink>
                  </motion.li>
                ))}
              </ul>
            </li>
          ))}
        </ul>

        <div className="sidebar-footer">
          <button
            className="sidebar-logout"
            onClick={() => {
              logout()
              navigate('/login')
            }}
          >
            <SignOut size={16} />
            Logout
          </button>
        </div>
      </motion.aside>

      {/* Main Content */}
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}

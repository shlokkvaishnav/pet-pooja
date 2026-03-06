import { useEffect, useMemo, useState } from 'react'
import {
  BellRing,
  Building2,
  CreditCard,
  Languages,
  MenuSquare,
} from 'lucide-react'
import {
  getOpsSettings,
  updateOpsSettings,
} from '../api/client'
import { useSettings } from '../context/SettingsContext'

const SECTION_ITEMS = [
  { id: 'restaurant_profile', label: 'Restaurant Profile', icon: Building2 },
  { id: 'menu_management', label: 'Menu Management', icon: MenuSquare },
  { id: 'notifications', label: 'Notifications', icon: BellRing },
  { id: 'billing_plan', label: 'Billing & Plan', icon: CreditCard },
  { id: 'voice_ai_config', label: 'Voice AI Config', icon: Languages },
]

function Toggle({ checked, onChange, label }) {
  return (
    <label className="settings-v2-toggle-row">
      <span>{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        className={`settings-v2-toggle ${checked ? 'settings-v2-toggle--on' : ''}`}
        onClick={() => onChange(!checked)}
      >
        <span />
      </button>
    </label>
  )
}

export default function Settings() {
  const { setSettings: setGlobalSettings } = useSettings()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saveState, setSaveState] = useState({ section: '', message: '', type: '' })
  const [savingSection, setSavingSection] = useState('')
  const [activeSection, setActiveSection] = useState('restaurant_profile')

  const [restaurantProfile, setRestaurantProfile] = useState({
    name: '',
    address: '',
    cuisine_type: '',
    logo_url: '',
    operating_hours: '',
    gst_number: '',
    email: '',
    phone: '',
  })
  const [menuManagement, setMenuManagement] = useState({
    default_tax_pct: 5,
    service_charge_pct: 0,
    hide_unavailable_items: true,
  })
  const [notifications, setNotifications] = useState({
    low_stock_alerts: true,
    daily_revenue_digest: true,
    weekly_performance_report: true,
  })
  const [billingPlan, setBillingPlan] = useState({
    plan_name: 'Starter',
    plan_status: 'active',
    usage_month_to_date: 0,
    invoices_available: false,
    payment_method: '',
  })
  const [voiceAiConfig, setVoiceAiConfig] = useState({
    primary_language: 'en',
    upsell_aggressiveness: 'medium',
    order_confirmation_phrase: 'Please confirm your order.',
    call_transfer_enabled: false,
  })

  useEffect(() => {
    setLoading(true)
    setError('')
    getOpsSettings()
      .then((res) => {
        setRestaurantProfile(res.restaurant_profile || {})
        setMenuManagement(res.menu_management || {})
        setNotifications(res.notifications || {})
        setBillingPlan(res.billing_plan || {})
        setVoiceAiConfig(res.voice_ai_config || {})
      })
      .catch((e) => setError(e?.detail || 'Unable to load settings'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!saveState.message) return undefined
    const timer = setTimeout(() => setSaveState({ section: '', message: '', type: '' }), 2500)
    return () => clearTimeout(timer)
  }, [saveState])

  const activeTitle = useMemo(
    () => SECTION_ITEMS.find((section) => section.id === activeSection)?.label || 'Settings',
    [activeSection],
  )

  async function saveSection(section, payload) {
    setSavingSection(section)
    setError('')
    try {
      await updateOpsSettings(payload)
      setSaveState({ section, message: 'Saved', type: 'ok' })
      if (payload.menu_management) {
        setGlobalSettings((prev) => ({ ...prev, menu_management: payload.menu_management }))
      }
    } catch (e) {
      setSaveState({ section, message: 'Save failed', type: 'error' })
      setError(e?.detail || 'Update failed')
    } finally {
      setSavingSection('')
    }
  }

  if (loading) return <div className="loading">Loading settings...</div>

  return (
    <div className="app-page">
      <div className="app-hero">
        <div>
          <div className="app-hero-eyebrow">System</div>
          <h1 className="app-hero-title">Settings</h1>
          <p className="app-hero-sub">
            Manage your restaurant profile, operations, and Voice AI behavior.
          </p>
        </div>
      </div>

      {error && (
        <div className="error-bar">
          <p>{error}</p>
        </div>
      )}

      <div className="settings-v2-shell">
        <aside className="settings-v2-nav">
          {SECTION_ITEMS.map((section) => {
            const Icon = section.icon
            return (
              <button
                key={section.id}
                type="button"
                className={`settings-v2-nav-btn ${activeSection === section.id ? 'settings-v2-nav-btn--active' : ''}`}
                onClick={() => setActiveSection(section.id)}
              >
                <Icon size={16} />
                <span>{section.label}</span>
              </button>
            )
          })}
        </aside>

        <section className="card">
          <div className="card-header settings-v2-header">
            <span>{activeTitle}</span>
            {saveState.section === activeSection && (
              <span className={`settings-v2-save-chip settings-v2-save-chip--${saveState.type}`}>
                {saveState.message}
              </span>
            )}
          </div>
          <div className="card-body settings-v2-body">
            {activeSection === 'restaurant_profile' && (
              <div className="settings-v2-form">
                <div className="settings-v2-grid">
                  <label>
                    Restaurant Name
                    <input
                      className="input"
                      value={restaurantProfile.name || ''}
                      onChange={(e) => setRestaurantProfile((prev) => ({ ...prev, name: e.target.value }))}
                    />
                  </label>
                  <label>
                    Cuisine Type
                    <input
                      className="input"
                      value={restaurantProfile.cuisine_type || ''}
                      onChange={(e) => setRestaurantProfile((prev) => ({ ...prev, cuisine_type: e.target.value }))}
                    />
                  </label>
                  <label>
                    Contact Email
                    <input
                      className="input"
                      value={restaurantProfile.email || ''}
                      onChange={(e) => setRestaurantProfile((prev) => ({ ...prev, email: e.target.value }))}
                    />
                  </label>
                  <label>
                    Contact Phone
                    <input
                      className="input"
                      value={restaurantProfile.phone || ''}
                      onChange={(e) => setRestaurantProfile((prev) => ({ ...prev, phone: e.target.value }))}
                    />
                  </label>
                  <label>
                    Logo URL
                    <input
                      className="input"
                      value={restaurantProfile.logo_url || ''}
                      onChange={(e) => setRestaurantProfile((prev) => ({ ...prev, logo_url: e.target.value }))}
                    />
                  </label>
                  <label>
                    Operating Hours
                    <input
                      className="input"
                      value={restaurantProfile.operating_hours || ''}
                      onChange={(e) => setRestaurantProfile((prev) => ({ ...prev, operating_hours: e.target.value }))}
                    />
                  </label>
                  <label className="settings-v2-col-span-2">
                    Address
                    <textarea
                      className="input settings-v2-textarea"
                      value={restaurantProfile.address || ''}
                      onChange={(e) => setRestaurantProfile((prev) => ({ ...prev, address: e.target.value }))}
                    />
                  </label>
                  <label>
                    GST Number
                    <input
                      className="input"
                      value={restaurantProfile.gst_number || ''}
                      onChange={(e) => setRestaurantProfile((prev) => ({ ...prev, gst_number: e.target.value }))}
                    />
                  </label>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() => saveSection('restaurant_profile', { restaurant_profile: restaurantProfile })}
                  disabled={savingSection === 'restaurant_profile'}
                >
                  Save Profile
                </button>
              </div>
            )}

            {activeSection === 'menu_management' && (
              <div className="settings-v2-form">
                <div className="settings-v2-grid">
                  <label>
                    Default Tax (%)
                    <input
                      className="input"
                      type="number"
                      min="0"
                      step="0.1"
                      value={menuManagement.default_tax_pct ?? 0}
                      onChange={(e) => setMenuManagement((prev) => ({ ...prev, default_tax_pct: Number(e.target.value) }))}
                    />
                  </label>
                  <label>
                    Service Charge (%)
                    <input
                      className="input"
                      type="number"
                      min="0"
                      step="0.1"
                      value={menuManagement.service_charge_pct ?? 0}
                      onChange={(e) => setMenuManagement((prev) => ({ ...prev, service_charge_pct: Number(e.target.value) }))}
                    />
                  </label>
                </div>
                <Toggle
                  label="Hide out-of-stock menu items from guests"
                  checked={!!menuManagement.hide_unavailable_items}
                  onChange={(value) => setMenuManagement((prev) => ({ ...prev, hide_unavailable_items: value }))}
                />
                <button
                  className="btn btn-primary"
                  onClick={() => saveSection('menu_management', { menu_management: menuManagement })}
                  disabled={savingSection === 'menu_management'}
                >
                  Save Menu Settings
                </button>
              </div>
            )}

            {activeSection === 'notifications' && (
              <div className="settings-v2-form">
                <Toggle
                  label="Low stock alerts"
                  checked={!!notifications.low_stock_alerts}
                  onChange={(value) => setNotifications((prev) => ({ ...prev, low_stock_alerts: value }))}
                />
                <Toggle
                  label="Daily revenue digest"
                  checked={!!notifications.daily_revenue_digest}
                  onChange={(value) => setNotifications((prev) => ({ ...prev, daily_revenue_digest: value }))}
                />
                <Toggle
                  label="Weekly performance report"
                  checked={!!notifications.weekly_performance_report}
                  onChange={(value) => setNotifications((prev) => ({ ...prev, weekly_performance_report: value }))}
                />
                <button
                  className="btn btn-primary"
                  onClick={() => saveSection('notifications', { notifications })}
                  disabled={savingSection === 'notifications'}
                >
                  Save Notifications
                </button>
              </div>
            )}

            {activeSection === 'billing_plan' && (
              <div className="settings-v2-form">
                <div className="app-grid-3">
                  <div className="settings-v2-stat">
                    <div>Current Plan</div>
                    <strong>{billingPlan.plan_name || 'Starter'}</strong>
                  </div>
                  <div className="settings-v2-stat">
                    <div>Plan Status</div>
                    <strong className="settings-v2-cap">{billingPlan.plan_status || 'active'}</strong>
                  </div>
                  <div className="settings-v2-stat">
                    <div>Usage (MTD)</div>
                    <strong>{billingPlan.usage_month_to_date ?? 0}</strong>
                  </div>
                </div>
                <div className="settings-v2-grid">
                  <label>
                    Payment Method
                    <input
                      className="input"
                      placeholder="UPI / Card ending 4242"
                      value={billingPlan.payment_method || ''}
                      onChange={(e) => setBillingPlan((prev) => ({ ...prev, payment_method: e.target.value }))}
                    />
                  </label>
                </div>
                <div className="settings-v2-inline">
                  <span>
                    Invoices: {billingPlan.invoices_available ? 'Available' : 'Unavailable'}
                  </span>
                  <button className="btn btn-secondary">Upgrade Plan</button>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() => saveSection('billing_plan', { billing_plan: billingPlan })}
                  disabled={savingSection === 'billing_plan'}
                >
                  Save Billing Settings
                </button>
              </div>
            )}

            {activeSection === 'voice_ai_config' && (
              <div className="settings-v2-form">
                <div className="settings-v2-grid">
                  <label>
                    Primary Language
                    <select
                      className="input"
                      value={voiceAiConfig.primary_language || 'en'}
                      onChange={(e) => setVoiceAiConfig((prev) => ({ ...prev, primary_language: e.target.value }))}
                    >
                      <option value="en">English</option>
                      <option value="hi">Hindi</option>
                      <option value="hi-en">Hinglish</option>
                    </select>
                  </label>
                  <label>
                    Upsell Aggressiveness
                    <select
                      className="input"
                      value={voiceAiConfig.upsell_aggressiveness || 'medium'}
                      onChange={(e) => setVoiceAiConfig((prev) => ({ ...prev, upsell_aggressiveness: e.target.value }))}
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </label>
                  <label className="settings-v2-col-span-2">
                    Order Confirmation Phrase
                    <input
                      className="input"
                      value={voiceAiConfig.order_confirmation_phrase || ''}
                      onChange={(e) => setVoiceAiConfig((prev) => ({ ...prev, order_confirmation_phrase: e.target.value }))}
                    />
                  </label>
                </div>
                <Toggle
                  label="Enable live call transfer to staff"
                  checked={!!voiceAiConfig.call_transfer_enabled}
                  onChange={(value) => setVoiceAiConfig((prev) => ({ ...prev, call_transfer_enabled: value }))}
                />
                <button
                  className="btn btn-primary"
                  onClick={() => saveSection('voice_ai_config', { voice_ai_config: voiceAiConfig })}
                  disabled={savingSection === 'voice_ai_config'}
                >
                  Save Voice AI Settings
                </button>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

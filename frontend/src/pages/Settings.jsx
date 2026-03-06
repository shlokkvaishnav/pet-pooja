import { useEffect, useMemo, useState } from 'react'
import {
  BellRing,
  Building2,
  CreditCard,
  KeyRound,
  Languages,
  Link2,
  MenuSquare,
  ShieldCheck,
  Users,
} from 'lucide-react'
import {
  createSettingsStaff,
  getOpsSettings,
  updateOpsSettings,
  updateSettingsStaff,
} from '../api/client'

const SECTION_ITEMS = [
  { id: 'restaurant_profile', label: 'Restaurant Profile', icon: Building2 },
  { id: 'menu_management', label: 'Menu Management', icon: MenuSquare },
  { id: 'staff_roles', label: 'Staff & Roles', icon: Users },
  { id: 'notifications', label: 'Notifications', icon: BellRing },
  { id: 'integrations', label: 'Integrations', icon: Link2 },
  { id: 'billing_plan', label: 'Billing & Plan', icon: CreditCard },
  { id: 'security', label: 'Security', icon: ShieldCheck },
  { id: 'voice_ai_config', label: 'Voice AI Config', icon: Languages },
]

const ROLE_OPTIONS = [
  { value: 'manager', label: 'Admin / Manager' },
  { value: 'waiter', label: 'Waiter' },
  { value: 'chef', label: 'Kitchen' },
  { value: 'cashier', label: 'Cashier' },
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

function MaskedKey({ index }) {
  return (
    <div className="settings-v2-key-row">
      <KeyRound size={14} />
      <span>{`sk_live_****_${String(index + 1).padStart(2, '0')}`}</span>
    </div>
  )
}

export default function Settings() {
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
    category_ordering_mode: 'manual',
  })
  const [staffRoles, setStaffRoles] = useState([])
  const [notifications, setNotifications] = useState({
    low_stock_alerts: true,
    daily_revenue_digest: true,
    weekly_performance_report: true,
  })
  const [integrations, setIntegrations] = useState({
    petpooja_connected: false,
    posist_connected: false,
    zomato_connected: false,
    swiggy_connected: false,
    payment_gateway: 'not_connected',
  })
  const [billingPlan, setBillingPlan] = useState({
    plan_name: 'Starter',
    plan_status: 'active',
    usage_month_to_date: 0,
    invoices_available: false,
    payment_method: '',
  })
  const [security, setSecurity] = useState({
    two_factor_enabled: false,
    active_sessions: 1,
    api_keys_configured: 0,
  })
  const [voiceAiConfig, setVoiceAiConfig] = useState({
    primary_language: 'en',
    upsell_aggressiveness: 'medium',
    order_confirmation_phrase: 'Please confirm your order.',
    call_transfer_enabled: false,
  })
  const [newStaff, setNewStaff] = useState({
    name: '',
    role: 'waiter',
    pin: '',
    phone: '',
  })

  useEffect(() => {
    setLoading(true)
    setError('')
    getOpsSettings()
      .then((res) => {
        setRestaurantProfile(res.restaurant_profile || {})
        setMenuManagement(res.menu_management || {})
        setStaffRoles(res.staff_roles || [])
        setNotifications(res.notifications || {})
        setIntegrations(res.integrations || {})
        setBillingPlan(res.billing_plan || {})
        setSecurity(res.security || {})
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
    } catch (e) {
      setSaveState({ section, message: 'Save failed', type: 'error' })
      setError(e?.detail || 'Update failed')
    } finally {
      setSavingSection('')
    }
  }

  async function handleCreateStaff(e) {
    e.preventDefault()
    if (!newStaff.name || !newStaff.pin) {
      setError('Staff name and PIN are required')
      return
    }
    setError('')
    try {
      const created = await createSettingsStaff({
        name: newStaff.name.trim(),
        role: newStaff.role,
        pin: newStaff.pin,
        phone: newStaff.phone || null,
      })
      setStaffRoles((prev) => [...prev, created])
      setNewStaff({ name: '', role: 'waiter', pin: '', phone: '' })
      setSaveState({ section: 'staff_roles', message: 'Staff member added', type: 'ok' })
    } catch (e2) {
      setError(e2?.detail || 'Unable to add staff member')
    }
  }

  async function saveStaffMember(staff) {
    setError('')
    try {
      await updateSettingsStaff(staff.staff_id, {
        role: staff.role,
        is_active: !!staff.is_active,
        phone: staff.phone || null,
      })
      setSaveState({ section: 'staff_roles', message: `${staff.name} updated`, type: 'ok' })
    } catch (e) {
      setError(e?.detail || 'Unable to update staff member')
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
            Manage your restaurant profile, operations, staff permissions, security, and Voice AI behavior.
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
                  <label>
                    Category Ordering
                    <select
                      className="input"
                      value={menuManagement.category_ordering_mode || 'manual'}
                      onChange={(e) => setMenuManagement((prev) => ({ ...prev, category_ordering_mode: e.target.value }))}
                    >
                      <option value="manual">Manual ordering</option>
                      <option value="smart">Smart ordering</option>
                    </select>
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

            {activeSection === 'staff_roles' && (
              <div className="settings-v2-form">
                <div className="settings-v2-section-subtitle">Staff Members</div>
                <div className="settings-v2-staff-list">
                  {staffRoles.map((staff) => (
                    <div key={staff.staff_id} className="settings-v2-staff-row">
                      <div className="settings-v2-staff-name">
                        <strong>{staff.name}</strong>
                        <span>{staff.is_active ? 'Active' : 'Inactive'}</span>
                      </div>
                      <select
                        className="input"
                        value={staff.role}
                        onChange={(e) => {
                          const role = e.target.value
                          setStaffRoles((prev) => prev.map((s) => (s.staff_id === staff.staff_id ? { ...s, role } : s)))
                        }}
                      >
                        {ROLE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                      <input
                        className="input"
                        placeholder="Phone"
                        value={staff.phone || ''}
                        onChange={(e) => {
                          const phone = e.target.value
                          setStaffRoles((prev) => prev.map((s) => (s.staff_id === staff.staff_id ? { ...s, phone } : s)))
                        }}
                      />
                      <button
                        className={`btn ${staff.is_active ? 'btn-ghost' : 'btn-secondary'}`}
                        onClick={() => setStaffRoles((prev) => prev.map((s) => (
                          s.staff_id === staff.staff_id ? { ...s, is_active: !s.is_active } : s
                        )))}
                      >
                        {staff.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                      <button className="btn btn-primary" onClick={() => saveStaffMember(staff)}>Save</button>
                    </div>
                  ))}
                </div>

                <div className="settings-v2-section-subtitle">Add Staff Member</div>
                <form className="settings-v2-grid" onSubmit={handleCreateStaff}>
                  <label>
                    Full Name
                    <input
                      className="input"
                      value={newStaff.name}
                      onChange={(e) => setNewStaff((prev) => ({ ...prev, name: e.target.value }))}
                    />
                  </label>
                  <label>
                    Role
                    <select
                      className="input"
                      value={newStaff.role}
                      onChange={(e) => setNewStaff((prev) => ({ ...prev, role: e.target.value }))}
                    >
                      {ROLE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Login PIN (4-6 digits)
                    <input
                      className="input"
                      maxLength={6}
                      value={newStaff.pin}
                      onChange={(e) => setNewStaff((prev) => ({ ...prev, pin: e.target.value.replace(/\D/g, '') }))}
                    />
                  </label>
                  <label>
                    Phone
                    <input
                      className="input"
                      value={newStaff.phone}
                      onChange={(e) => setNewStaff((prev) => ({ ...prev, phone: e.target.value }))}
                    />
                  </label>
                  <button className="btn btn-primary settings-v2-col-span-2" type="submit">Add Staff</button>
                </form>
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

            {activeSection === 'integrations' && (
              <div className="settings-v2-form">
                <div className="settings-v2-grid">
                  <Toggle
                    label="Petpooja POS"
                    checked={!!integrations.petpooja_connected}
                    onChange={(value) => setIntegrations((prev) => ({ ...prev, petpooja_connected: value }))}
                  />
                  <Toggle
                    label="Posist POS"
                    checked={!!integrations.posist_connected}
                    onChange={(value) => setIntegrations((prev) => ({ ...prev, posist_connected: value }))}
                  />
                  <Toggle
                    label="Zomato"
                    checked={!!integrations.zomato_connected}
                    onChange={(value) => setIntegrations((prev) => ({ ...prev, zomato_connected: value }))}
                  />
                  <Toggle
                    label="Swiggy"
                    checked={!!integrations.swiggy_connected}
                    onChange={(value) => setIntegrations((prev) => ({ ...prev, swiggy_connected: value }))}
                  />
                  <label className="settings-v2-col-span-2">
                    Payment Gateway
                    <select
                      className="input"
                      value={integrations.payment_gateway || 'not_connected'}
                      onChange={(e) => setIntegrations((prev) => ({ ...prev, payment_gateway: e.target.value }))}
                    >
                      <option value="not_connected">Not connected</option>
                      <option value="razorpay">Razorpay</option>
                      <option value="cashfree">Cashfree</option>
                      <option value="stripe">Stripe</option>
                    </select>
                  </label>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() => saveSection('integrations', { integrations })}
                  disabled={savingSection === 'integrations'}
                >
                  Save Integrations
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

            {activeSection === 'security' && (
              <div className="settings-v2-form">
                <Toggle
                  label="Two-factor authentication (2FA)"
                  checked={!!security.two_factor_enabled}
                  onChange={(value) => setSecurity((prev) => ({ ...prev, two_factor_enabled: value }))}
                />
                <div className="settings-v2-inline">
                  <span>Active sessions</span>
                  <strong>{security.active_sessions ?? 0}</strong>
                </div>
                <div>
                  <div className="settings-v2-section-subtitle">API Keys</div>
                  <div className="settings-v2-key-list">
                    {Array.from({ length: Math.max(0, Number(security.api_keys_configured) || 0) }).map((_, index) => (
                      <MaskedKey key={index} index={index} />
                    ))}
                    {(security.api_keys_configured || 0) === 0 && (
                      <div className="muted">No API keys configured</div>
                    )}
                  </div>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() => saveSection('security', { security })}
                  disabled={savingSection === 'security'}
                >
                  Save Security Settings
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

      <div className="card">
        <div className="card-header">Permissions Blueprint</div>
        <div className="card-body">
          <table className="data-table">
            <thead>
              <tr>
                <th>Role</th>
                <th>Access Scope</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Admin</strong></td>
                <td>Full access across settings, billing, integrations, and security.</td>
              </tr>
              <tr>
                <td><strong>Manager</strong></td>
                <td>Operational settings, staff updates, reports, and notifications.</td>
              </tr>
              <tr>
                <td><strong>Waiter</strong></td>
                <td>Order and table workflows only, no billing/security controls.</td>
              </tr>
              <tr>
                <td><strong>Kitchen</strong></td>
                <td>Kitchen queue visibility and prep workflow only.</td>
              </tr>
            </tbody>
          </table>
          <div className="muted" style={{ marginTop: 10 }}>
            Developer diagnostics are intentionally excluded from this page and must stay in restricted admin routes.
          </div>
          <div className="muted">
            Note: current backend staff roles map Kitchen to Chef and Admin to Manager permissions.
          </div>
        </div>
      </div>
    </div>
  )
}

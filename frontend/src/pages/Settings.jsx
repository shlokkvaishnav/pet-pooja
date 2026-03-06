import { useEffect, useState } from 'react'
import { getOpsSettings } from '../api/client'

export default function Settings() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getOpsSettings()
      .then(setData)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading">Loading settings...</div>
  if (!data) return <div className="loading">Failed to load settings.</div>

  return (
    <div className="app-page">
      <div className="app-hero">
        <div>
          <div className="app-hero-eyebrow">System</div>
          <h1 className="app-hero-title">Settings</h1>
          <p className="app-hero-sub">Read-only runtime configuration snapshot.</p>
        </div>
      </div>

      <div className="app-grid-2">
        <div className="app-card">
          <div className="app-card-label">Authentication</div>
          <div className="app-card-value">{data.auth_enabled ? 'Enabled' : 'Disabled'}</div>
          <div className="app-card-sub">AUTH_ENABLED</div>
        </div>
        <div className="app-card">
          <div className="app-card-label">Database</div>
          <div className="app-card-value">{data.database.engine}</div>
          <div className="app-card-sub">{data.database.url}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Rate Limits</div>
        <div className="card-body">
          <div className="settings-grid">
            <div className="settings-item">
              <div className="settings-label">Voice RPM</div>
              <div className="settings-value">{data.rate_limits.voice_rpm}</div>
            </div>
            <div className="settings-item">
              <div className="settings-label">Revenue RPM</div>
              <div className="settings-value">{data.rate_limits.revenue_rpm}</div>
            </div>
            <div className="settings-item">
              <div className="settings-label">Default RPM</div>
              <div className="settings-value">{data.rate_limits.default_rpm}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">CORS Origins</div>
        <div className="card-body">
          <div className="muted">{data.cors_origins || 'Not set'}</div>
        </div>
      </div>
    </div>
  )
}


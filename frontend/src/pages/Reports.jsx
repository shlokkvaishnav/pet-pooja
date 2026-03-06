import { useEffect, useState } from 'react'
import { exportReportsCsv, getOpsReportsFiltered } from '../api/client'
import { formatRupees } from '../utils/format'
import { motion } from 'motion/react'
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar,
} from 'recharts'

const TOOLTIP_STYLE = {
  backgroundColor: 'var(--bg-surface)',
  borderColor: 'var(--border-subtle)',
  color: 'var(--text-primary)',
  fontSize: 12,
  fontFamily: 'var(--font-body)',
}

export default function Reports() {
  const [data, setData] = useState([])
  const [topItems, setTopItems] = useState([])
  const [topCategories, setTopCategories] = useState([])
  const [days, setDays] = useState(14)
  const [exportKind, setExportKind] = useState('daily')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getOpsReportsFiltered({ days, top_n: 8 })
      .then((res) => {
        setData(res.daily || [])
        setTopItems(res.top_items || [])
        setTopCategories(res.top_categories || [])
      })
      .finally(() => setLoading(false))
  }, [days])

  if (loading) return <div className="loading">Loading reports...</div>

  return (
    <div className="app-page">
      <div className="app-hero">
        <div>
          <div className="app-hero-eyebrow">Insights</div>
          <h1 className="app-hero-title">Reports</h1>
          <p className="app-hero-sub">Revenue and order momentum at a glance.</p>
        </div>
        <div className="app-hero-metrics">
          <div className="app-kpi">
            <div className="app-kpi-label">Days Tracked</div>
            <div className="app-kpi-value">{data.length}</div>
          </div>
          <div className="app-kpi">
            <div className="app-kpi-label">Total Revenue</div>
            <div className="app-kpi-value">
              {formatRupees(data.reduce((sum, d) => sum + (d.revenue || 0), 0))}
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Controls</div>
        <div className="card-body">
          <div className="filters-row">
            <select className="input" value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
            </select>
            <select className="input" value={exportKind} onChange={(e) => setExportKind(e.target.value)}>
              <option value="daily">Export Daily</option>
              <option value="top_items">Export Top Items</option>
              <option value="top_categories">Export Top Categories</option>
            </select>
            <button
              className="btn btn-primary"
              onClick={() => {
                exportReportsCsv({ kind: exportKind, days })
                  .then((blob) => {
                    const url = window.URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `reports_${exportKind}_${days}d.csv`
                    a.click()
                    window.URL.revokeObjectURL(url)
                  })
              }}
            >
              Download CSV
            </button>
          </div>
        </div>
      </div>

      <div className="app-grid-2">
        <motion.div className="card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="card-header">Daily Revenue</div>
          <div className="card-body">
            {data.length === 0 ? (
              <div className="muted">No report data available.</div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={data}>
                  <defs>
                    <linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.6} />
                      <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                  <XAxis dataKey="date" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => formatRupees(v)} />
                  <Area type="monotone" dataKey="revenue" stroke="var(--accent)" fill="url(#revFill)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </motion.div>

        <motion.div className="card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="card-header">Daily Orders</div>
          <div className="card-body">
            {data.length === 0 ? (
              <div className="muted">No report data available.</div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                  <XAxis dataKey="date" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="orders" fill="var(--data-4)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </motion.div>
      </div>

      <div className="app-grid-2">
        <div className="card">
          <div className="card-header">Top Items</div>
          <div className="card-body">
            {topItems.length === 0 ? (
              <div className="muted">No item drilldown available.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Revenue</th>
                    <th>Qty</th>
                  </tr>
                </thead>
                <tbody>
                  {topItems.map((i) => (
                    <tr key={i.item_id}>
                      <td style={{ fontWeight: 600 }}>{i.name}</td>
                      <td>{formatRupees(i.revenue)}</td>
                      <td>{i.qty}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">Top Categories</div>
          <div className="card-body">
            {topCategories.length === 0 ? (
              <div className="muted">No category drilldown available.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {topCategories.map((c) => (
                    <tr key={c.category_id}>
                      <td style={{ fontWeight: 600 }}>{c.name}</td>
                      <td>{formatRupees(c.revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import { exportReportsCsv, getOpsReportsFiltered } from '../api/client'
import { formatRupees } from '../utils/format'
import { motion } from 'motion/react'
import { Download } from 'lucide-react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Line,
} from 'recharts'

const TOOLTIP_STYLE = {
  backgroundColor: 'var(--bg-overlay)',
  border: '1px solid var(--border-strong)',
  padding: '8px 12px',
  color: '#FFFFFF',
  fontSize: 12,
  fontFamily: 'var(--font-body)',
  borderRadius: 8,
  boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
}

function formatShortDate(value) {
  if (!value) return ''
  const dt = new Date(`${value}T00:00:00`)
  if (Number.isNaN(dt.valueOf())) return value
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function todayIso() {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export default function Reports() {
  const [data, setData] = useState([])
  const [topItems, setTopItems] = useState([])
  const [topCategories, setTopCategories] = useState([])
  const [hourlyHeatmap, setHourlyHeatmap] = useState([])
  const [hourlyHeatmapMax, setHourlyHeatmapMax] = useState(0)
  const [comboPerformance, setComboPerformance] = useState([])
  const [voiceAccuracy, setVoiceAccuracy] = useState(null)
  const [repeatRate, setRepeatRate] = useState(null)
  const [days, setDays] = useState(14)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [customRange, setCustomRange] = useState(false)
  const [loading, setLoading] = useState(true)

  // When days dropdown changes, auto-compute start/end dates
  useEffect(() => {
    if (customRange) return
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - days + 1)
    setStartDate(start.toISOString().slice(0, 10))
    setEndDate(end.toISOString().slice(0, 10))
  }, [days, customRange])

  function handleDaysChange(val) {
    setCustomRange(false)
    setDays(val)
  }

  function handleStartDateChange(val) {
    setCustomRange(true)
    setStartDate(val)
    if (val && endDate) {
      const diff = Math.round((new Date(endDate) - new Date(val)) / 86400000) + 1
      if (diff > 0) setDays(diff)
    }
  }

  function handleEndDateChange(val) {
    setCustomRange(true)
    setEndDate(val)
    if (startDate && val) {
      const diff = Math.round((new Date(val) - new Date(startDate)) / 86400000) + 1
      if (diff > 0) setDays(diff)
    }
  }

  useEffect(() => {
    if (!startDate || !endDate) return
    setLoading(true)
    getOpsReportsFiltered({
      days,
      top_n: 8,
      start_date: startDate,
      end_date: endDate,
    })
      .then((res) => {
        setData(res.daily || [])
        setTopItems(res.top_items || [])
        setTopCategories(res.top_categories || [])
        setHourlyHeatmap(res.hourly_order_heatmap || [])
        setHourlyHeatmapMax(res.hourly_order_heatmap_max || 0)
        setComboPerformance(res.combo_performance || [])
        setVoiceAccuracy(res.voice_accuracy || null)
        setRepeatRate(res.customer_repeat_rate || null)
      })
      .finally(() => setLoading(false))
  }, [days, startDate, endDate])

  const chartData = useMemo(
    () => data.map((row) => ({
      ...row,
      date_label: formatShortDate(row.date),
      revenue_solid: row.is_today ? null : row.revenue,
      revenue_live: row.is_today ? row.revenue : null,
    })),
    [data],
  )

  function downloadCsv(kind) {
    exportReportsCsv({ kind, days })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `reports_${kind}_${days}d.csv`
        a.click()
        window.URL.revokeObjectURL(url)
      })
  }

  const totalRevenue = data.reduce((sum, d) => sum + (d.revenue || 0), 0)
  const voiceAccuracyPct = voiceAccuracy?.accuracy_pct || 0
  const voiceTotal = voiceAccuracy?.voice_total || 0

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
            <div className="app-kpi-value">{formatRupees(totalRevenue)}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <div className="filters-row reports-filters-row">
            <select className="input" value={days} onChange={(e) => handleDaysChange(Number(e.target.value))}>
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
            </select>
            <input className="input" type="date" value={startDate} max={endDate || undefined} onChange={(e) => handleStartDateChange(e.target.value)} />
            <input className="input" type="date" value={endDate} min={startDate || undefined} onChange={(e) => handleEndDateChange(e.target.value)} />
          </div>
        </div>
      </div>

      <div className="app-grid-2">
        <motion.div className="card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="card-header">
            Daily Revenue
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="reports-live-chip">Today (live)<span className="reports-live-dot" /></span>
              <button className="btn btn-ghost" style={{ padding: '4px 8px' }} title="Download CSV" onClick={() => downloadCsv('daily')}><Download size={14} /></button>
            </span>
          </div>
          <div className="card-body">
            {chartData.length === 0 ? (
              <div className="muted">No report data available.</div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.6} />
                      <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                  <XAxis dataKey="date_label" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} itemStyle={{ color: '#fff' }} labelStyle={{ color: '#fff' }} formatter={(v) => formatRupees(v)} />
                  <Area type="monotone" dataKey="revenue_solid" stroke="var(--accent)" fill="url(#revFill)" strokeWidth={2} connectNulls />
                  <Line type="monotone" dataKey="revenue_live" stroke="var(--accent)" strokeDasharray="6 4" strokeWidth={2} dot={{ r: 4 }} connectNulls />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </motion.div>

        <motion.div className="card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="card-header">
            Daily Orders
            <button className="btn btn-ghost" style={{ padding: '4px 8px' }} title="Download CSV" onClick={() => downloadCsv('daily')}><Download size={14} /></button>
          </div>
          <div className="card-body">
            {chartData.length === 0 ? (
              <div className="muted">No report data available.</div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                  <XAxis dataKey="date_label" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} itemStyle={{ color: '#fff' }} labelStyle={{ color: '#fff' }} />
                  <Bar dataKey="orders" fill="var(--info)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </motion.div>
      </div>

      <div className="app-grid-2">
        <div className="card">
          <div className="card-header">Hourly Order Heatmap</div>
          <div className="card-body">
            {hourlyHeatmap.length === 0 ? (
              <div className="muted">No hourly order data available.</div>
            ) : (
              <div className="reports-heatmap-wrap">
                {hourlyHeatmap.map((row) => (
                  <div key={row.day} className="reports-heatmap-row">
                    <div className="reports-heatmap-day">{row.day}</div>
                    <div className="reports-heatmap-cells">
                      {row.hours.map((cell) => {
                        const intensity = hourlyHeatmapMax > 0 ? cell.count / hourlyHeatmapMax : 0
                        return (
                          <div
                            key={`${row.day}-${cell.hour}`}
                            className="reports-heatmap-cell"
                            title={`${row.day} ${String(cell.hour).padStart(2, '0')}:00 - ${cell.count} orders`}
                            style={{ background: `rgba(232, 93, 42, ${0.08 + intensity * 0.75})` }}
                          />
                        )
                      })}
                    </div>
                  </div>
                ))}
                <div className="reports-heatmap-scale">00:00 to 23:00</div>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">Voice Order Accuracy</div>
          <div className="card-body">
            {voiceAccuracy ? (
              <div className="reports-kpi-stack">
                <div className="reports-kpi-value">{voiceAccuracyPct}%</div>
                <div className="reports-kpi-sub">Completed without cancellation</div>
                <div className="reports-kpi-meta">Voice orders sampled: {voiceTotal}</div>
              </div>
            ) : (
              <div className="muted">No voice order accuracy data available.</div>
            )}
          </div>
        </div>
      </div>

      <div className="app-grid-2">
        <div className="card">
          <div className="card-header">Combo Performance</div>
          <div className="card-body">
            {comboPerformance.length === 0 ? (
              <div className="muted">No combo performance data available.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Combo</th>
                    <th>Accepted Orders</th>
                    <th>Acceptance Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {comboPerformance.map((combo, idx) => (
                    <tr key={`${combo.combo_name}-${idx}`}>
                      <td style={{ fontWeight: 600 }}>{combo.combo_name}</td>
                      <td>{combo.accepted_orders}</td>
                      <td>{combo.acceptance_rate_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">Customer Repeat Rate</div>
          <div className="card-body">
            {repeatRate?.available ? (
              <div className="reports-kpi-stack">
                <div className="reports-kpi-value">{repeatRate.repeat_rate_pct}%</div>
                <div className="reports-kpi-sub">Orders from returning customers</div>
              </div>
            ) : (
              <div className="muted">{repeatRate?.note || 'Repeat-rate data is not available yet.'}</div>
            )}
          </div>
        </div>
      </div>

      <div className="app-grid-2">
        <div className="card">
          <div className="card-header">
            Top Items
            <button className="btn btn-ghost" style={{ padding: '4px 8px' }} title="Download CSV" onClick={() => downloadCsv('top_items')}><Download size={14} /></button>
          </div>
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
          <div className="card-header">
            Top Categories
            <button className="btn btn-ghost" style={{ padding: '4px 8px' }} title="Download CSV" onClick={() => downloadCsv('top_categories')}><Download size={14} /></button>
          </div>
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

export default function ComboCard({ combo }) {
  return (
    <div className="card">
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 13 }}>
          <span style={{ color: 'var(--text-muted)' }}>If orders </span>
          <strong>{combo.antecedent_name}</strong>
          <span style={{ color: 'var(--text-muted)' }}> → suggest </span>
          <strong>{combo.consequent_name}</strong>
        </span>
        <span className="tag tag-star">Lift: {parseFloat(combo.lift)?.toFixed(2)}x</span>
      </div>
      <div className="card-body">
        {/* Confidence Progress Bar */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
            <span>Confidence</span>
            <span>{(combo.confidence * 100)?.toFixed(1)}%</span>
          </div>
          <div style={{ width: '100%', height: 6, background: 'var(--surface2)', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ width: `${combo.confidence * 100}%`, height: '100%', background: 'var(--blue)', borderRadius: 3 }} />
          </div>
        </div>

        {/* Pricing & Gains */}
        <div style={{ padding: '8px 12px', background: 'var(--surface2)', borderRadius: 6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
            <span style={{ color: 'var(--text-muted)' }}>CM Gain</span>
            <span style={{ color: 'var(--green)', fontWeight: 600 }}>+₹{parseFloat(combo.cm_gain)?.toFixed(2)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
            <span style={{ color: 'var(--text-muted)' }}>Suggested Bundle Price</span>
            <span style={{ fontWeight: 600 }}>₹{parseFloat(combo.suggested_bundle_price)?.toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

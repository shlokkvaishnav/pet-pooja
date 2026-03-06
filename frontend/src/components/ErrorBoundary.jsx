import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '50vh', gap: 16, padding: 32 }}>
          <div style={{ fontSize: 48 }}>⚠</div>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary, #fff)' }}>Something went wrong</h2>
          <p style={{ fontSize: 13, color: 'var(--text-secondary, #888)', maxWidth: 400, textAlign: 'center' }}>
            An unexpected error occurred. Please refresh the page to continue.
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{ padding: '10px 20px', borderRadius: 8, background: 'var(--accent, #c8450a)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}
          >
            Refresh Page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

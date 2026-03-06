import { motion, AnimatePresence } from 'motion/react'
import { useState } from 'react'

export default function InfoTooltip({ title, explanation, components }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div 
      className="info-tooltip-wrap"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      <button className="info-btn" aria-label="More info">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div 
            className="info-tooltip"
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.15 }}
          >
            <div className="info-tooltip-header">{title}</div>
            
            {explanation && (
              <p className="info-tooltip-explanation">{explanation}</p>
            )}

            <div className="info-tooltip-grid">
              {components?.map((item, idx) => (
                <div key={idx} className="info-tooltip-row">
                  <div className="info-tooltip-row-top">
                    <span className="info-tooltip-name">{item.name}</span>
                    <span className={`info-tooltip-score ${item.score >= 0 ? 'pos' : 'neg'}`}>
                      {item.score >= 0 ? '+' : ''}{item.score}
                    </span>
                  </div>
                  <div className="info-tooltip-detail">{item.detail}</div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

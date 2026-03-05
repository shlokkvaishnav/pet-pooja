/** Indian number formatting utilities */

const inrFormatter = new Intl.NumberFormat('en-IN', {
  maximumFractionDigits: 0,
})

const inrDecimalFormatter = new Intl.NumberFormat('en-IN', {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
})

/** Format rupee amount with ₹ prefix and Indian grouping: ₹1,00,000 */
export function formatRupees(value) {
  if (value == null || isNaN(value)) return '₹0'
  return `₹${inrFormatter.format(value)}`
}

/** Format large rupee amounts: ₹1.2L, ₹45K etc. */
export function formatRupeesShort(value) {
  if (value == null || isNaN(value)) return '₹0'
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`
  if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`
  return `₹${inrFormatter.format(value)}`
}

/** Format percentage to 1 decimal max */
export function formatPct(value) {
  if (value == null || isNaN(value)) return '0%'
  return `${Number(value).toFixed(1)}%`
}

/** Format a decimal like 0.12 to '12% of orders' */
export function formatSupport(value) {
  if (value == null || isNaN(value)) return '0%'
  return `${Math.round(value * 100)}% of orders`
}

/** Format confidence decimal to percentage: 0.78 → '78%' */
export function formatConfidence(value) {
  if (value == null || isNaN(value)) return '0%'
  return `${Math.round(value * 100)}%`
}

/** Format lift: 2.3 → '2.3×' */
export function formatLift(value) {
  if (value == null || isNaN(value)) return '0×'
  return `${Number(value).toFixed(1)}×`
}

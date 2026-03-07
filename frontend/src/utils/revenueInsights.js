import { TARGET_UPSELL_CM as _TARGET_CM, MIN_ORDER_HISTORY as _MIN_HISTORY } from '../config'

const TARGET_UPSELL_CM = _TARGET_CM
const MIN_ORDER_HISTORY = _MIN_HISTORY

function num(value, fallback = 0) {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function lower(value) {
  return String(value || '').toLowerCase()
}

function safeName(item) {
  return item?.name || item?.item_name || 'Unnamed Item'
}

function inferCategory(item) {
  const raw = lower(item?.category || item?.category_name || '')
  if (!raw) return 'other'
  if (/(biryani|main|curry|thali|rice|gravy)/.test(raw)) return 'main'
  if (/(bread|naan|roti|kulcha|paratha)/.test(raw)) return 'bread'
  if (/(drink|beverage|lassi|juice|soda|coffee|tea)/.test(raw)) return 'beverage'
  if (/(dessert|sweet|ice cream|halwa|jamun|kheer|rabri)/.test(raw)) return 'dessert'
  if (/(starter|side|appetizer|salad|raita)/.test(raw)) return 'side'
  return 'other'
}

function cmPercent(item) {
  return num(item?.cm_percent ?? item?.margin_pct ?? item?.current_margin_pct)
}

function popularity(item) {
  return num(item?.popularity_score)
}

function price(item) {
  return num(item?.selling_price ?? item?.current_price ?? item?.unit_price)
}

function confidenceLevel(score) {
  if (score >= 0.78) return 'High'
  if (score >= 0.56) return 'Medium'
  return 'Low'
}

function matchMenuItemsByNames(menuItems, names = []) {
  if (!Array.isArray(menuItems) || menuItems.length === 0) return []
  const lookup = new Map(menuItems.map((item) => [lower(safeName(item)), item]))
  return names
    .map((name) => lookup.get(lower(name)))
    .filter(Boolean)
}



function normalizeCombo(combo, index, menuItems = []) {
  const names = Array.isArray(combo.item_names) && combo.item_names.length
    ? combo.item_names
    : (Array.isArray(combo.items) ? combo.items.map((i) => i?.name).filter(Boolean) : [])

  const matched = matchMenuItemsByNames(menuItems, names)
  const itemPrices = Array.isArray(combo.item_prices) && combo.item_prices.length
    ? combo.item_prices.map((v) => num(v))
    : names.map((name, idx) => {
      const found = matched[idx]
      if (found) return price(found)
      return num(combo?.individual_prices?.[idx], 0)
    })

  const combined = itemPrices.reduce((sum, p) => sum + num(p), 0)
  const discountPct = Math.min(25, Math.max(5, num(combo.discount_pct, 10)))
  const bundlePrice = num(combo.combo_price ?? combo.suggested_bundle_price, Math.round(combined * (1 - discountPct / 100)))
  const uplift = Math.max(6, Math.min(28, Math.round((num(combo.lift, 1.4) - 1) * 12 + num(combo.confidence, 0.6) * 10)))
  const confidence = Math.max(0.35, Math.min(0.99, num(combo.confidence, 0.55)))
  const support = Math.max(0.03, Math.min(0.9, num(combo.support, 0.08)))

  return {
    id: combo.combo_id || combo.id || `combo-${index + 1}`,
    itemNames: names.length ? names : [`Combo ${index + 1}`],
    itemPrices,
    combinedPrice: combined,
    bundlePrice,
    discountPct,
    confidence,
    support,
    occurrenceCount: num(combo.occurrence_count, 0),
    lift: num(combo.lift, 1.3),
    aovUpliftPct: uplift,
    source: combo.source || 'real',
  }
}

export function shouldUseSynthetic(totalOrders) {
  return num(totalOrders) < MIN_ORDER_HISTORY
}

export function buildComboInsights({
  combos = [],
  menuItems = [],
  totalOrders = 0,
  promotedIds = [],
}) {
  const insufficientData = shouldUseSynthetic(totalOrders)
  const base = !Array.isArray(combos) || combos.length === 0 ? [] : combos

  const normalized = base.map((combo, idx) => normalizeCombo(combo, idx, menuItems))
  const promotedSet = new Set(promotedIds || [])
  const withState = normalized.map((combo) => ({ ...combo, isPromoted: promotedSet.has(combo.id) }))

  const avgUplift = withState.length
    ? withState.reduce((sum, c) => sum + c.aovUpliftPct, 0) / withState.length
    : 0

  return {
    combos: withState,
    insufficientData,
    summary: {
      totalCombos: withState.length,
      avgAovUpliftPct: avgUplift,
      activePromoted: withState.filter((c) => c.isPromoted).length,
    },
    promotedIds: [...promotedSet],
  }
}

export function buildUpsellCandidates({
  items = [],
  trends = null,
  currentOrderItems = [],
  limit = 3,
}) {
  const itemList = Array.isArray(items) ? items : []
  const trendCats = Array.isArray(trends?.category_trends) ? trends.category_trends : []
  const categoryFreq = new Map(
    trendCats.map((row) => [lower(row.category_name), num(row.revenue_last_30d)]),
  )
  const topFreq = Math.max(1, ...Array.from(categoryFreq.values()))

  const currentNames = new Set((currentOrderItems || []).map((i) => lower(i.item_name || i.name)))
  const currentCats = new Set((currentOrderItems || []).map((i) => inferCategory(i)))

  const candidates = itemList
    .map((item) => {
      const margin = cmPercent(item)
      const pop = popularity(item)
      const cat = inferCategory(item)
      const freq = categoryFreq.get(lower(item.category || item.category_name || '')) || 0
      const freqScore = freq / topFreq
      const lowPopGap = Math.max(0, 0.62 - pop)
      const catGapBonus = currentCats.size > 0 && !currentCats.has(cat) ? 0.16 : 0
      const score = (margin / 100) * 0.56 + lowPopGap * 0.28 + freqScore * 0.16 + catGapBonus
      return {
        item_id: item.item_id,
        name: safeName(item),
        category: item.category,
        price: price(item),
        cm_percent: margin,
        popularity_score: pop,
        score,
      }
    })
    .filter((item) =>
      item.cm_percent >= TARGET_UPSELL_CM &&
      !currentNames.has(lower(item.name)) &&
      item.score > 0.45,
    )
    .sort((a, b) => b.score - a.score)

  const targetOrder = ['bread', 'beverage', 'dessert', 'side', 'main', 'other']
  const chosen = []
  const used = new Set()
  for (const cat of targetOrder) {
    const pick = candidates.find((c) => inferCategory(c) === cat && !used.has(c.item_id))
    if (pick) {
      chosen.push(pick)
      used.add(pick.item_id)
    }
    if (chosen.length >= limit) break
  }
  if (chosen.length < limit) {
    for (const c of candidates) {
      if (!used.has(c.item_id)) {
        chosen.push(c)
        used.add(c.item_id)
      }
      if (chosen.length >= limit) break
    }
  }

  return chosen.slice(0, limit).map((item) => ({
    ...item,
    reason: item.popularity_score < 0.45
      ? 'High margin, low visibility - ideal to suggest at order time'
      : 'Strong margin in a high-order category - good upsell fit',
  }))
}

export function buildPriceOpportunities({
  items = [],
  combos = [],
  apiRecommendations = [],
  totalOrders = 0,
}) {
  const itemList = Array.isArray(items) ? items : []
  const byCategory = new Map()
  for (const item of itemList) {
    const key = lower(item.category || 'uncategorized')
    const list = byCategory.get(key) || []
    list.push(price(item))
    byCategory.set(key, list)
  }
  const categoryAvg = new Map(
    Array.from(byCategory.entries()).map(([key, vals]) => [key, vals.reduce((a, b) => a + b, 0) / Math.max(1, vals.length)]),
  )

  const opportunities = []

  for (const item of itemList) {
    const cm = cmPercent(item)
    const pop = popularity(item)
    const p = price(item)
    const q = lower(item.quadrant)
    const avg = categoryAvg.get(lower(item.category || 'uncategorized')) || p

    if (q === 'star' && pop > 0.7 && p <= avg * 0.85) {
      const increasePct = 8
      const newPrice = Math.round((p * (1 + increasePct / 100)) / 5) * 5
      const cmImpactLow = Math.round((newPrice - p) / p * 100)
      const cmImpactHigh = cmImpactLow + 3
      const volImpactHigh = -Math.round(increasePct * 0.12)
      const volImpactLow = -Math.round(increasePct * 0.38)
      opportunities.push({
        id: `inc-${item.item_id}`,
        item_id: item.item_id,
        item_name: safeName(item),
        current_price: p,
        suggested_price: newPrice,
        suggested_action: `Increase to Rs ${newPrice}`,
        expected_cm_impact: `+${cmImpactLow}% to +${cmImpactHigh}%`,
        expected_volume_impact: `${volImpactLow}% to ${volImpactHigh}%`,
        confidence_level: 'High',
      })
    }
    if (q === 'plowhorse' && pop > 0.65 && cm < 50) {
      const decreasePct = 4
      const newPrice = Math.max(10, Math.round((p * (1 - decreasePct / 100)) / 5) * 5)
      const priceDiff = p - newPrice
      const cmImpactLow = -Math.round(priceDiff / p * 100)
      const cmImpactHigh = cmImpactLow + 1
      const volImpactLow = Math.round(decreasePct * 1.0)
      const volImpactHigh = Math.round(decreasePct * 2.25)
      opportunities.push({
        id: `dec-${item.item_id}`,
        item_id: item.item_id,
        item_name: safeName(item),
        current_price: p,
        suggested_price: newPrice,
        suggested_action: `Decrease to Rs ${newPrice}`,
        expected_cm_impact: `${cmImpactLow}% to ${cmImpactHigh > 0 ? '+' : ''}${cmImpactHigh}%`,
        expected_volume_impact: `+${volImpactLow}% to +${volImpactHigh}%`,
        confidence_level: 'Medium',
      })
    }
  }

  const normalizedCombos = (Array.isArray(combos) ? combos : []).map((c, idx) => normalizeCombo(c, idx, itemList))
  const marginByName = new Map(itemList.map((i) => [lower(safeName(i)), cmPercent(i)]))
  for (const combo of normalizedCombos.slice(0, 8)) {
    const [a, b] = combo.itemNames
    const ma = marginByName.get(lower(a)) || 0
    const mb = marginByName.get(lower(b)) || 0
    if ((ma >= 65 || mb >= 65) && combo.confidence >= 0.58) {
      const discountFrac = combo.combinedPrice > 0 ? (combo.combinedPrice - combo.bundlePrice) / combo.combinedPrice : 0
      const cmImpactLow = Math.round(discountFrac * 100 * 0.3)
      const cmImpactHigh = Math.round(discountFrac * 100 * 0.8)
      const volImpactLow = Math.round(combo.confidence * 8)
      const volImpactHigh = Math.round(combo.confidence * 18)
      opportunities.push({
        id: `bundle-${combo.id}`,
        item_name: `${a} + ${b}`,
        current_price: combo.combinedPrice,
        suggested_action: `Bundle at Rs ${combo.bundlePrice}`,
        expected_cm_impact: `+${cmImpactLow}% to +${cmImpactHigh}%`,
        expected_volume_impact: `+${volImpactLow}% to +${volImpactHigh}%`,
        confidence_level: confidenceLevel(combo.confidence),
      })
    }
  }

  if (Array.isArray(apiRecommendations) && apiRecommendations.length > 0) {
    for (const rec of apiRecommendations.slice(0, 4)) {
      const suggested = num(rec.recommended_price ?? rec.suggested_price, num(rec.current_price))
      const currentP = num(rec.current_price)
      const priceDelta = currentP > 0 ? Math.abs(suggested - currentP) / currentP * 100 : 0
      let apiCmImpact, apiVolImpact
      if (rec.direction === 'decrease') {
        apiCmImpact = `-${Math.round(priceDelta * 0.3)}% to +${Math.max(1, Math.round(priceDelta * 0.15))}%`
        apiVolImpact = `+${Math.round(priceDelta * 0.6)}% to +${Math.round(priceDelta * 1.5)}%`
      } else if (rec.direction === 'hold') {
        apiCmImpact = '0%'
        apiVolImpact = '0%'
      } else {
        apiCmImpact = `+${Math.round(priceDelta * 0.4)}% to +${Math.round(priceDelta * 0.9)}%`
        apiVolImpact = `-${Math.round(priceDelta * 0.3)}% to +${Math.max(1, Math.round(priceDelta * 0.2))}%`
      }
      const mlScore = num(rec.ml_opportunity_score, num(rec.confidence))
      opportunities.push({
        id: `api-${rec.item_id || rec.name}`,
        item_name: rec.name || rec.item_name || 'Menu Item',
        current_price: currentP,
        suggested_action: rec.direction === 'decrease'
          ? `Decrease to Rs ${Math.round(suggested)}`
          : rec.direction === 'hold'
            ? `Maintain at Rs ${Math.round(suggested)}`
            : `Increase to Rs ${Math.round(suggested)}`,
        expected_cm_impact: apiCmImpact,
        expected_volume_impact: apiVolImpact,
        confidence_level: confidenceLevel(num(rec.confidence)),
        ml_opportunity_score: mlScore,
        ml_badge: mlScore >= 0.7 ? 'High' : mlScore >= 0.45 ? 'Medium' : 'Low',
      })
    }
  }

  const deduped = []
  const seen = new Set()
  for (const row of opportunities) {
    const key = lower(row.item_name)
    if (!seen.has(key)) {
      seen.add(key)
      deduped.push(row)
    }
  }

  const insufficientData = shouldUseSynthetic(totalOrders)

  return {
    insufficientData,
    opportunities: deduped.slice(0, 18),
  }
}

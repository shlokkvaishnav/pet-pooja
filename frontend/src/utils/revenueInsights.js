const TARGET_UPSELL_CM = 65
const MIN_ORDER_HISTORY = 30

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

function chooseFallback(menuItems, matcher, fallbackName) {
  const found = menuItems.find(matcher)
  if (found) return found
  return menuItems.find((i) => safeName(i) !== fallbackName) || menuItems[0] || {
    item_id: Math.random(),
    name: fallbackName,
    selling_price: 199,
    cm_percent: 68,
    category: 'Main Course',
  }
}

function syntheticCombos(menuItems = []) {
  const biryani = chooseFallback(menuItems, (i) => /biryani/.test(lower(safeName(i))), 'Chicken Biryani')
  const raita = chooseFallback(menuItems, (i) => /raita/.test(lower(safeName(i))), 'Boondi Raita')
  const cola = chooseFallback(menuItems, (i) => /(cola|soda|coke|beverage|lassi)/.test(lower(safeName(i))), 'Masala Cola')

  const butterChicken = chooseFallback(menuItems, (i) => /butter chicken/.test(lower(safeName(i))), 'Butter Chicken')
  const naan = chooseFallback(menuItems, (i) => /(naan|bread|roti|kulcha)/.test(lower(safeName(i))), 'Butter Naan')
  const gulab = chooseFallback(menuItems, (i) => /(gulab|jamun|dessert|sweet)/.test(lower(safeName(i))), 'Gulab Jamun')

  const paneer = chooseFallback(menuItems, (i) => /(paneer|tikka|kebab)/.test(lower(safeName(i))), 'Paneer Tikka')
  const mojito = chooseFallback(menuItems, (i) => /(lime|mojito|drink|beverage)/.test(lower(safeName(i))), 'Mint Lime Soda')

  return [
    {
      combo_id: 'SYN-001',
      source: 'synthetic',
      item_names: [safeName(biryani), safeName(raita), safeName(cola)],
      item_prices: [price(biryani) || 340, price(raita) || 90, price(cola) || 80],
      confidence: 0.81,
      support: 0.29,
      lift: 2.2,
    },
    {
      combo_id: 'SYN-002',
      source: 'synthetic',
      item_names: [safeName(butterChicken), safeName(naan), safeName(gulab)],
      item_prices: [price(butterChicken) || 360, price(naan) || 60, price(gulab) || 110],
      confidence: 0.76,
      support: 0.22,
      lift: 1.9,
    },
    {
      combo_id: 'SYN-003',
      source: 'synthetic',
      item_names: [safeName(paneer), safeName(naan), safeName(mojito)],
      item_prices: [price(paneer) || 290, price(naan) || 60, price(mojito) || 120],
      confidence: 0.73,
      support: 0.2,
      lift: 1.8,
    },
  ]
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
  const syntheticRequired = shouldUseSynthetic(totalOrders)
  const base = syntheticRequired || !Array.isArray(combos) || combos.length === 0
    ? syntheticCombos(menuItems)
    : combos

  const normalized = base.map((combo, idx) => normalizeCombo(combo, idx, menuItems))
  const promotedSet = new Set(promotedIds || [])
  const withState = normalized.map((combo) => ({ ...combo, isPromoted: promotedSet.has(combo.id) }))

  const promotedRows = withState.filter((c) => c.isPromoted).map((combo, idx) => {
    const timesSuggested = Math.max(18, Math.round(combo.support * 220) + idx * 7)
    const timesAccepted = Math.max(4, Math.round(timesSuggested * Math.min(combo.confidence, 0.7)))
    const acceptanceRate = timesSuggested ? (timesAccepted / timesSuggested) * 100 : 0
    const avgBill = combo.bundlePrice || combo.combinedPrice
    return {
      id: combo.id,
      comboName: combo.itemNames.join(' + '),
      timesSuggested,
      timesAccepted,
      acceptanceRate,
      revenueAttributed: timesAccepted * avgBill,
    }
  })

  const avgUplift = withState.length
    ? withState.reduce((sum, c) => sum + c.aovUpliftPct, 0) / withState.length
    : 0

  return {
    combos: withState,
    usedSynthetic: syntheticRequired,
    summary: {
      totalCombos: withState.length,
      avgAovUpliftPct: avgUplift,
      activePromoted: withState.filter((c) => c.isPromoted).length,
    },
    promotedPerformance: promotedRows,
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

  let finalList = chosen.slice(0, limit).map((item) => ({
    ...item,
    reason: item.popularity_score < 0.45
      ? 'High margin, low visibility - ideal to suggest at order time'
      : 'Strong margin in a high-order category - good upsell fit',
  }))

  if (finalList.length < limit) {
    const synthetic = [
      { item_id: 'syn-upsell-1', name: 'Butter Naan', price: 55, cm_percent: 71, reason: 'High margin, low visibility - ideal to suggest at order time' },
      { item_id: 'syn-upsell-2', name: 'Masala Buttermilk', price: 79, cm_percent: 74, reason: 'High margin in a high-order category - easy add-on with mains' },
      { item_id: 'syn-upsell-3', name: 'Gulab Jamun', price: 99, cm_percent: 69, reason: 'Dessert add-on with strong attachment potential after main course' },
    ]
    for (const row of synthetic) {
      if (!finalList.find((x) => lower(x.name) === lower(row.name))) {
        finalList.push(row)
      }
      if (finalList.length >= limit) break
    }
  }

  return finalList.slice(0, limit)
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
      opportunities.push({
        id: `inc-${item.item_id}`,
        item_name: safeName(item),
        current_price: p,
        suggested_action: `Increase to Rs ${Math.round((p * 1.08) / 5) * 5}`,
        expected_cm_impact: '+3% to +6%',
        expected_volume_impact: '-1% to -3%',
        confidence_level: 'High',
      })
    }
    if (q === 'plowhorse' && pop > 0.65 && cm < 50) {
      opportunities.push({
        id: `dec-${item.item_id}`,
        item_name: safeName(item),
        current_price: p,
        suggested_action: `Decrease to Rs ${Math.max(10, Math.round((p * 0.96) / 5) * 5)}`,
        expected_cm_impact: '-1% to -2%',
        expected_volume_impact: '+4% to +9%',
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
      opportunities.push({
        id: `bundle-${combo.id}`,
        item_name: `${a} + ${b}`,
        current_price: combo.combinedPrice,
        suggested_action: `Bundle at Rs ${combo.bundlePrice}`,
        expected_cm_impact: '+2% to +5%',
        expected_volume_impact: '+5% to +12%',
        confidence_level: confidenceLevel(combo.confidence),
      })
    }
  }

  if (Array.isArray(apiRecommendations) && apiRecommendations.length > 0) {
    for (const rec of apiRecommendations.slice(0, 4)) {
      const suggested = num(rec.recommended_price ?? rec.suggested_price, num(rec.current_price))
      opportunities.push({
        id: `api-${rec.item_id || rec.name}`,
        item_name: rec.name || rec.item_name || 'Menu Item',
        current_price: num(rec.current_price),
        suggested_action: rec.direction === 'decrease'
          ? `Decrease to Rs ${Math.round(suggested)}`
          : rec.direction === 'hold'
            ? `Maintain at Rs ${Math.round(suggested)}`
            : `Increase to Rs ${Math.round(suggested)}`,
        expected_cm_impact: rec.direction === 'decrease' ? '-1% to +1%' : '+2% to +5%',
        expected_volume_impact: rec.direction === 'decrease' ? '+3% to +8%' : '-2% to +2%',
        confidence_level: confidenceLevel(num(rec.confidence)),
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

  const syntheticNeeded = shouldUseSynthetic(totalOrders) || deduped.length === 0
  const syntheticRows = [
    {
      id: 'syn-price-1',
      item_name: 'Chicken Biryani',
      current_price: 329,
      suggested_action: 'Increase to Rs 349',
      expected_cm_impact: '+4% to +7%',
      expected_volume_impact: '-2% to +1%',
      confidence_level: 'High',
    },
    {
      id: 'syn-price-2',
      item_name: 'Masala Buttermilk',
      current_price: 79,
      suggested_action: 'Bundle with Biryani at Rs 59 add-on',
      expected_cm_impact: '+3% to +5%',
      expected_volume_impact: '+8% to +14%',
      confidence_level: 'Medium',
    },
    {
      id: 'syn-price-3',
      item_name: 'Paneer Tikka',
      current_price: 289,
      suggested_action: 'Decrease to Rs 269 for lunch slots',
      expected_cm_impact: '-2% to 0%',
      expected_volume_impact: '+6% to +11%',
      confidence_level: 'Medium',
    },
  ]

  return {
    usedSynthetic: syntheticNeeded,
    opportunities: syntheticNeeded ? syntheticRows : deduped.slice(0, 18),
  }
}

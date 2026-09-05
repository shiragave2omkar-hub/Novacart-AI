export const formatINR = (value) => {
  if (value === null || value === undefined) return 'Price unavailable'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value)
}

export const shortSpecs = (product, limit = 3) => Object.entries(product?.specifications || {})
  .filter(([, value]) => value)
  .slice(0, limit)
  .map(([key, value]) => ({ key: key.replace(/_/g, ' '), value: String(value) }))

export const displayEvent = (event) => String(event || '').replaceAll('_', ' ')
  .replace(/\b\w/g, (letter) => letter.toUpperCase())

export const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return Number.isNaN(date.valueOf()) ? timestamp : date.toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', day: 'numeric', month: 'short' })
}

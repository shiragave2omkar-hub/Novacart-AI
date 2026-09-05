const request = async (path, options = {}) => {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error || 'NovaCart could not complete that request.')
  return data
}

export const api = {
  chat: (body) => request('/api/chat', { method: 'POST', body: JSON.stringify(body) }),
  getCart: () => request('/api/cart'),
  addToCart: (productId, quantity = 1) => request('/api/cart/add', { method: 'POST', body: JSON.stringify({ product_id: productId, quantity }) }),
  removeFromCart: (productId) => request('/api/cart/remove', { method: 'POST', body: JSON.stringify({ product_id: productId }) }),
  checkout: (budget) => request('/api/checkout/summary', { method: 'POST', body: JSON.stringify({ budget_inr: budget }) }),
  createPaymentOrder: () => request('/api/payment/create-order', { method: 'POST' }),
  verifyPayment: (payment) => request('/api/payment/verify', { method: 'POST', body: JSON.stringify(payment) }),
  analytics: () => request('/api/merchant/analytics'),
  campaign: (goal) => request('/api/campaign', { method: 'POST', body: JSON.stringify({ goal }) }),
  audit: () => request('/api/audit'),
  aiBuyerQuote: (goal) => request('/api/ai-buyer/quote', { method: 'POST', body: JSON.stringify({ goal }) }),
}

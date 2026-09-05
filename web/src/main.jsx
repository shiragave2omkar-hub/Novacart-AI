import { useEffect, useState } from 'react'
import { Activity, BarChart3, Bot, ChevronDown, Menu, Megaphone, ShoppingBag, Sparkles, X } from 'lucide-react'
import { createRoot } from 'react-dom/client'
import { api } from './lib/api'
import { CustomerView } from './components/CustomerView'
import { AIBuyerView, AuditTrail, CampaignBuilder, MerchantDashboard } from './components/MerchantViews'
import { CartDrawer, CheckoutPanel, Toast } from './components/ui'
import './styles.css'

const customerStarter = 'I need a coding laptop for college under ₹80,000.'

function App() {
  const [view, setView] = useState('shop')
  const [merchantView, setMerchantView] = useState('dashboard')
  const [cart, setCart] = useState({ items: [], total: 0 })
  const [cartOpen, setCartOpen] = useState(false)
  const [checkout, setCheckout] = useState(null)
  const [recommendations, setRecommendations] = useState(null)
  const [response, setResponse] = useState('')
  const [history, setHistory] = useState([])
  const [budget, setBudget] = useState(null)
  const [chatLoading, setChatLoading] = useState(false)
  const [merchantLoading, setMerchantLoading] = useState(false)
  const [analytics, setAnalytics] = useState(null)
  const [campaign, setCampaign] = useState(null)
  const [audit, setAudit] = useState(null)
  const [auditLoading, setAuditLoading] = useState(false)
  const [quote, setQuote] = useState(null)
  const [buyerLoading, setBuyerLoading] = useState(false)
  const [toast, setToast] = useState(null)
  const [mobileOpen, setMobileOpen] = useState(false)

  const notify = (message, type = 'success') => {
    setToast({ message, type })
    window.setTimeout(() => setToast(null), 4200)
  }

  const loadCart = async () => {
    try { setCart(await api.getCart()) } catch { notify('NovaCart could not load your cart.', 'error') }
  }

  const loadAnalytics = async () => {
    setMerchantLoading(true)
    try { setAnalytics(await api.analytics()) } catch (error) { notify(error.message, 'error') } finally { setMerchantLoading(false) }
  }

  const loadAudit = async () => {
    setAuditLoading(true)
    try { setAudit(await api.audit()) } catch (error) { notify(error.message, 'error') } finally { setAuditLoading(false) }
  }

  useEffect(() => { loadCart() }, [])
  useEffect(() => { if (view === 'merchant' && merchantView === 'dashboard' && !analytics) loadAnalytics() }, [view, merchantView])
  useEffect(() => { if (view === 'merchant' && merchantView === 'audit') loadAudit() }, [view, merchantView])

  const handleChat = async (message) => {
    setChatLoading(true)
    const nextHistory = [...history, { role: 'user', content: message }]
    try {
      const result = await api.chat({
        message,
        history,
        context: { best_fit_id: recommendations?.best_fit?.id, budget_inr: budget },
      })
      setResponse(result.message || '')
      setHistory([...nextHistory, { role: 'assistant', content: result.message || '' }])
      if (result.recommendations) {
        setRecommendations(result.recommendations)
        if (result.recommendations.budget_inr) setBudget(result.recommendations.budget_inr)
      }
      if (result.cart) setCart(result.cart)
      if (/\b(checkout|check out)\b/i.test(message)) await openCheckout()
    } catch (error) {
      setHistory(nextHistory)
      notify(error.message || 'NovaCart could not complete that request. Your cart has been preserved.', 'error')
    } finally { setChatLoading(false) }
  }

  const addProduct = async (product) => {
    try {
      setCart(await api.addToCart(product.id))
      notify(`${product.brand || ''} ${product.name} added to your cart.`.trim())
    } catch (error) { notify(error.message, 'error') }
  }

  const removeProduct = async (productId) => {
    try { setCart(await api.removeFromCart(productId)) } catch (error) { notify(error.message, 'error') }
  }

  const openCheckout = async () => {
    try {
      setCheckout(await api.checkout(budget))
      setCartOpen(false)
    } catch (error) { notify(error.message, 'error') }
  }

  const createCampaign = async (goal) => {
    setMerchantLoading(true)
    try {
      setCampaign(await api.campaign(goal))
      await Promise.all([loadAnalytics(), loadAudit()])
      notify('Campaign draft created. It has not been launched.')
    } catch (error) { notify(error.message, 'error') } finally { setMerchantLoading(false) }
  }

  const requestQuote = async (goal) => {
    setBuyerLoading(true)
    try { setQuote(await api.aiBuyerQuote(goal)) } catch (error) { notify(error.message, 'error') } finally { setBuyerLoading(false) }
  }

  const switchView = (next) => {
    setView(next)
    setMobileOpen(false)
    if (next === 'merchant' && !analytics) loadAnalytics()
  }

  return <div className="app-shell">
    <header className="topbar">
      <button className="brand-lockup" onClick={() => switchView('shop')} aria-label="NovaCart home"><span className="brand-mark"><Sparkles size={17} /></span><span>NovaCart</span><small>AI Commerce Engine</small></button>
      <nav className={mobileOpen ? 'mobile-nav-open' : ''} aria-label="Primary navigation">
        <button className={view === 'shop' ? 'active' : ''} onClick={() => switchView('shop')}>Customer</button>
        <button className={view === 'merchant' ? 'active' : ''} onClick={() => switchView('merchant')}>Merchant</button>
        <button className={view === 'buyer' ? 'active' : ''} onClick={() => switchView('buyer')}>AI Buyer</button>
      </nav>
      <div className="topbar-actions"><button className="cart-button" onClick={() => setCartOpen(true)}><ShoppingBag size={17} /> <span>Cart</span>{cart.items.length > 0 && <b>{cart.items.reduce((count, item) => count + item.quantity, 0)}</b>}</button><button className="menu-button" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle navigation">{mobileOpen ? <X size={20} /> : <Menu size={20} />}</button></div>
    </header>

    {view === 'shop' && <CustomerView chat={handleChat} loading={chatLoading} recommendations={recommendations} response={response} cart={cart} budget={budget} onAdd={addProduct} />}
    {view === 'merchant' && <main className="merchant-shell"><aside className="merchant-nav"><span>Merchant workspace</span><button className={merchantView === 'dashboard' ? 'active' : ''} onClick={() => setMerchantView('dashboard')}><BarChart3 size={17} /> Dashboard</button><button className={merchantView === 'campaigns' ? 'active' : ''} onClick={() => setMerchantView('campaigns')}><Megaphone size={17} /> Campaigns</button><button className={merchantView === 'audit' ? 'active' : ''} onClick={() => setMerchantView('audit')}><Activity size={17} /> Audit trail</button></aside><div className="merchant-content">{merchantView === 'dashboard' && <MerchantDashboard analytics={analytics} loading={merchantLoading} onOpenCampaign={() => setMerchantView('campaigns')} />}{merchantView === 'campaigns' && <CampaignBuilder campaign={campaign} loading={merchantLoading} onCreate={createCampaign} />}{merchantView === 'audit' && <AuditTrail audit={audit} loading={auditLoading} reload={loadAudit} />}</div></main>}
    {view === 'buyer' && <AIBuyerView onRequest={requestQuote} quote={quote} loading={buyerLoading} />}

    <CartDrawer open={cartOpen} cart={cart} budget={budget} onClose={() => setCartOpen(false)} onRemove={removeProduct} onCheckout={openCheckout} />
    <CheckoutPanel summary={checkout} onClose={() => setCheckout(null)} />
    <Toast toast={toast} onClose={() => setToast(null)} />
  </div>
}

createRoot(document.getElementById('root')).render(<App />)

import { useState } from 'react'
import {
  ArrowUpRight, Bot, Check, ChevronRight, CircleAlert, ExternalLink, Laptop,
  LoaderCircle, Minus, Package, Plus, ShieldCheck, ShoppingBag, Sparkles,
  Trash2, X,
} from 'lucide-react'
import { formatINR, shortSpecs } from '../lib/format'

export function ProductImage({ product, compact = false }) {
  const [failedProductId, setFailedProductId] = useState(null)
  const productId = product?.id
  const image = productId && failedProductId !== productId ? `/products/${productId}.jpg` : '/nova-product-placeholder.png'
  return (
    <div className={`product-image ${compact ? 'compact' : ''}`}>
      <img src={image} alt={product ? `${product.brand} ${product.name}` : ''} onError={() => setFailedProductId(productId)} />
      <span className="product-category"><Package size={12} /> {product?.category}</span>
    </div>
  )
}

export function ProductCard({ product, onAdd, label, featured = false, compact = false }) {
  if (!product) return null
  const sourceUrl = product.product_url || product.source?.url
  const sourceLabel = product.product_url ? 'View product' : 'Official source'
  const specs = shortSpecs(product, compact ? 2 : 3)
  return (
    <article className={`product-card ${featured ? 'featured' : ''} ${compact ? 'card-compact' : ''}`}>
      <ProductImage product={product} compact={compact} />
      <div className="product-copy">
        {label && <span className="eyebrow accent"><Sparkles size={13} /> {label}</span>}
        <p className="brand">{product.brand || 'Catalog product'}</p>
        <h3>{product.name}</h3>
        <p className="price">{formatINR(product.price_inr)}</p>
        {product.price_status && <p className="price-note">{product.price_status.replaceAll('_', ' ')}</p>}
        {!compact && specs.length > 0 && (
          <dl className="spec-list">
            {specs.map(({ key, value }) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}
          </dl>
        )}
        {!compact && product.tags?.length > 0 && <div className="tag-row">{product.tags.slice(0, 3).map((tag) => <span key={tag}>{tag}</span>)}</div>}
      </div>
      <div className="product-actions">
        {onAdd && <button className="button primary" onClick={() => onAdd(product)} disabled={product.price_inr === null || product.price_inr === undefined}>
          <ShoppingBag size={16} /> Add to cart
        </button>}
        {sourceUrl && <a className="button ghost" href={sourceUrl} target="_blank" rel="noreferrer">{sourceLabel} <ExternalLink size={14} /></a>}
      </div>
    </article>
  )
}

export function BudgetMeter({ budget, total = 0, showLabel = true }) {
  if (!budget) return null
  const difference = budget - total
  const status = difference < 0 ? 'over' : difference <= budget * 0.12 ? 'near' : 'within'
  const label = status === 'over' ? 'Over target' : status === 'near' ? 'Near target' : 'Within target'
  const width = Math.min((total / budget) * 100, 100)
  return (
    <section className={`budget-meter ${status}`} aria-label="Budget status">
      <div className="meter-top"><span>{showLabel ? 'Budget intelligence' : 'Budget'}</span><strong>{label}</strong></div>
      <div className="meter-values"><span>{formatINR(total)}</span><span>of {formatINR(budget)}</span></div>
      <div className="meter-track"><span style={{ width: `${width}%` }} /></div>
      <p>{difference >= 0 ? `${formatINR(difference)} remaining` : `${formatINR(Math.abs(difference))} above your target`}</p>
    </section>
  )
}

export function LoadingRecommendations() {
  return <section className="loading-results" aria-live="polite"><div className="loading-label"><LoaderCircle size={17} /> NovaCart is analyzing your goal...</div><div className="skeleton-grid">{[1, 2, 3].map((item) => <div className="skeleton-card" key={item}><span /><span /><span /><span /></div>)}</div></section>
}

export function EmptyState({ title, message, icon: Icon = CircleAlert }) {
  return <section className="empty-state"><Icon size={24} /><h2>{title}</h2><p>{message}</p></section>
}

export function Toast({ toast, onClose }) {
  if (!toast) return null
  return <div className={`toast ${toast.type || 'success'}`} role="status"><Check size={18} /><span>{toast.message}</span><button onClick={onClose} aria-label="Dismiss notification"><X size={16} /></button></div>
}

export function CartDrawer({ open, cart, budget, onClose, onRemove, onCheckout }) {
  if (!open) return null
  return <div className="drawer-layer" role="presentation"><button className="drawer-backdrop" aria-label="Close cart" onClick={onClose} /><aside className="cart-drawer" aria-label="Shopping cart">
    <header><div><span className="eyebrow"><ShoppingBag size={14} /> Your selection</span><h2>Cart</h2></div><button className="icon-button" onClick={onClose} aria-label="Close cart"><X size={19} /></button></header>
    <div className="cart-items">
      {cart?.items?.length ? cart.items.map((item) => <div className="cart-item" key={item.id}>
        <ProductImage product={item.product} compact />
        <div><p className="brand">{item.brand}</p><h3>{item.name}</h3><p>{item.quantity} x {formatINR(item.price)}</p></div>
        <div className="cart-item-end"><strong>{formatINR(item.subtotal)}</strong><button className="icon-button subtle" aria-label={`Remove ${item.name}`} onClick={() => onRemove(item.id)}><Trash2 size={16} /></button></div>
      </div>) : <EmptyState title="Your cart is clear" message="Add catalog products when you are ready." icon={ShoppingBag} />}
    </div>
    {cart?.items?.length > 0 && <footer className="cart-footer"><BudgetMeter budget={budget} total={cart.total} showLabel={false} /><div className="cart-total"><span>Total</span><strong>{formatINR(cart.total)}</strong></div><button className="button primary full" onClick={onCheckout}>Review checkout <ChevronRight size={17} /></button><p className="security-note"><ShieldCheck size={14} /> Totals are calculated from the catalog on the server.</p></footer>}
  </aside></div>
}

export function CheckoutPanel({ summary, onClose }) {
  if (!summary) return null
  const isEmpty = summary.status === 'empty'
  return <div className="modal-layer"><button className="drawer-backdrop" aria-label="Close checkout" onClick={onClose} /><section className="checkout-modal" role="dialog" aria-modal="true" aria-label="Checkout review">
    <button className="icon-button modal-close" onClick={onClose} aria-label="Close checkout"><X size={18} /></button>
    <span className="eyebrow accent"><ShieldCheck size={14} /> Confirm order details</span>
    <h2>{isEmpty ? 'Nothing to check out' : 'Order summary'}</h2>
    {isEmpty ? <p>{summary.message}</p> : <>
      <div className="checkout-lines">{summary.items.map((item) => <div key={item.id}><span>{item.brand} {item.name} <small>x{item.quantity}</small></span><strong>{formatINR(item.subtotal)}</strong></div>)}</div>
      <div className="checkout-total"><span>Exact catalog total</span><strong>{formatINR(summary.total)}</strong></div>
      {summary.budget_inr && <BudgetMeter budget={summary.budget_inr} total={summary.total} showLabel={false} />}
      <div className="payment-state"><CircleAlert size={18} /><div><strong>Payment sandbox unavailable</strong><p>This prototype has not initiated a Razorpay payment. Confirming is intentionally unavailable until a live payment integration is connected.</p></div></div>
    </>}
  </section></div>
}

export function IconStat({ label, value, detail, icon: Icon }) {
  return <article className="stat"><div className="stat-icon"><Icon size={18} /></div><p>{label}</p><strong>{value}</strong>{detail && <small>{detail}</small>}</article>
}

export { ArrowUpRight, Bot, Laptop, Minus, Plus }

import { useState } from 'react'
import { ArrowRight, CheckCircle2, CircleAlert, MessageSquareText, Send, Sparkles } from 'lucide-react'
import { BudgetMeter, LoadingRecommendations, ProductCard } from './ui'
import { formatINR } from '../lib/format'

const prompts = [
  'Best laptop for coding under ₹80k',
  'Best laptop for ML',
  'Gaming setup under ₹1 lakh',
  'College productivity setup',
]

export function CustomerView({ chat, loading, recommendations, response, cart, budget, onAdd }) {
  const [draft, setDraft] = useState('')
  const submit = (event) => {
    event.preventDefault()
    if (!draft.trim() || loading) return
    chat(draft.trim())
    setDraft('')
  }
  const selectPrompt = (prompt) => {
    setDraft(prompt)
    chat(prompt)
  }
  const currentTotal = cart?.total || 0

  return <main className="customer-view">
    <section className={`command-hero ${recommendations ? 'compact-hero' : ''}`}>
      <div className="hero-copy">
        <span className="eyebrow"><Sparkles size={14} /> AI-native commerce</span>
        <h1>Tell NovaCart what<br />you are trying to accomplish.</h1>
        <p>One goal, your constraints, and a product path you can inspect before you buy.</p>
      </div>
      <div className="hero-signal" aria-hidden="true"><div className="signal-ring ring-one" /><div className="signal-ring ring-two" /><div className="signal-core"><MessageSquareText size={26} /></div><span>Goal-aware selection</span></div>
      <form className="prompt-composer" onSubmit={submit}>
        <div className="composer-label"><span><span className="status-dot" /> NovaCart AI</span><small>Catalog-connected</small></div>
        <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="I need a coding laptop for college under ₹80,000." rows="2" aria-label="Tell NovaCart your shopping goal" />
        <div className="composer-footer"><div className="prompt-chips">{prompts.map((prompt) => <button type="button" onClick={() => selectPrompt(prompt)} key={prompt}>{prompt}</button>)}</div><button className="send-button" type="submit" disabled={loading || !draft.trim()} aria-label="Send goal"><Send size={18} /></button></div>
      </form>
    </section>

    {loading && <LoadingRecommendations />}

    {!loading && response && <section className="agent-message"><div className="message-mark"><Sparkles size={17} /></div><div><span className="eyebrow">AI message</span><p>{response}</p></div></section>}

    {!loading && recommendations && <section className="recommendation-space">
      <div className="results-head"><div><span className="eyebrow accent"><Sparkles size={14} /> Goal analysis</span><h2>Optimized around your brief</h2></div>{recommendations.budget_inr && <BudgetMeter budget={recommendations.budget_inr} total={currentTotal || recommendations.best_fit?.price_inr || 0} />}</div>
      <div className="best-fit-layout">
        <div className="best-fit-product"><div className="section-heading"><span>01</span><div><p>Best fit</p><h2>Start here</h2></div></div><ProductCard product={recommendations.best_fit} label="Recommended for your goal" featured onAdd={onAdd} /></div>
        <aside className="reason-stack">
          <section className="reason-panel"><span className="eyebrow"><CheckCircle2 size={14} /> Why this</span><h3>Catalog-backed match</h3><ul>{recommendations.why_this?.map((reason) => <li key={reason}><CheckCircle2 size={16} />{reason}</li>)}</ul></section>
          {recommendations.best_fit?.compatible_with?.length > 0 && <section className="reason-panel soft"><span className="eyebrow">Compatibility</span><p>{recommendations.best_fit.compatible_with.join(', ')}</p></section>}
          {recommendations.why_not && <section className="reason-panel caution"><span className="eyebrow"><CircleAlert size={14} /> Trade-off</span><p>{recommendations.why_not}</p></section>}
        </aside>
      </div>

      {recommendations.alternatives?.length > 0 && <section className="result-section"><div className="section-heading"><span>02</span><div><p>Alternatives</p><h2>Different ways to meet the brief</h2></div></div><div className="product-grid">{recommendations.alternatives.map((product) => <ProductCard product={product} onAdd={onAdd} key={product.id} />)}</div></section>}

      {recommendations.cross_sell?.length > 0 && <section className="result-section addons"><div className="section-heading"><span>03</span><div><p>Recommended with your selection</p><h2>Useful add-ons</h2></div><p className="section-note">Optional complements listed in the catalog. They remain separate from your main recommendation.</p></div><div className="product-grid compact-grid">{recommendations.cross_sell.map((product) => <ProductCard product={product} onAdd={onAdd} compact key={product.id} />)}</div></section>}

      {recommendations.stretch_option && <section className="stretch-section"><div><span className="eyebrow"><ArrowRight size={14} /> Stretch option</span><h2>{recommendations.stretch_option.brand} {recommendations.stretch_option.name}</h2><p><strong>{formatINR(recommendations.stretch_option.price_inr)}</strong> <span>•</span> {formatINR(recommendations.stretch_option.overage_inr)} above your stated budget.</p></div><ProductCard product={recommendations.stretch_option} onAdd={onAdd} compact /></section>}
    </section>}

    {!loading && !recommendations && !response && <section className="how-it-works"><span className="eyebrow">A goal, not a filter</span><div><article><span>01</span><h3>Understand the objective</h3><p>Natural language becomes an intent-aware catalog search.</p></article><article><span>02</span><h3>Expose the reasoning</h3><p>See products, price boundaries, and catalog facts in one view.</p></article><article><span>03</span><h3>Protect the transaction</h3><p>Server-calculated cart and checkout data stay authoritative.</p></article></div></section>}
  </main>
}

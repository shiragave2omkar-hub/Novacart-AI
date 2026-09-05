import { useState } from 'react'
import { Activity, ArrowUpRight, BarChart3, Bot, CalendarClock, CheckCircle2, CircleAlert, Lightbulb, Megaphone, MousePointer2, Send, ShieldCheck, Users } from 'lucide-react'
import { EmptyState, IconStat, ProductCard } from './ui'
import { displayEvent, formatINR, formatTime } from '../lib/format'

export function MerchantDashboard({ analytics, loading, onOpenCampaign }) {
  const overall = analytics?.accessory_attachment
  const opportunity = analytics?.growth_opportunity
  if (loading) return <DashboardSkeleton />
  if (!analytics) return <EmptyState title="Merchant intelligence is unavailable" message="The synthetic demo analytics dataset could not be loaded." />
  return <section className="merchant-page"><div className="page-title"><div><span className="eyebrow"><BarChart3 size={14} /> Merchant intelligence</span><h1>Revenue opportunities, made inspectable.</h1><p>{analytics.data_label}</p></div><button className="button primary" onClick={onOpenCampaign}><Megaphone size={16} /> Build campaign</button></div>
    <div className="stat-grid"><IconStat label="Accessory attachment" value={`${overall?.accessory_attach_rate || 0}%`} detail="Across demo laptop buyers" icon={Activity} /><IconStat label="Laptop buyers" value={overall?.laptop_buyers || 0} detail="Synthetic purchase records" icon={Users} /><IconStat label="With accessories" value={overall?.laptop_buyers_with_accessories || 0} detail="Synthetic purchase records" icon={MousePointer2} /><IconStat label="Growth opportunity" value={opportunity?.category || 'Unavailable'} detail={opportunity ? `${opportunity.attachment_rate}% attachment` : undefined} icon={Lightbulb} /></div>
    <div className="merchant-layout"><section className="opportunity-card"><div className="section-heading"><span>Opportunity</span><div><p>Catalog + synthetic sales signals</p><h2>{opportunity?.category || 'No category signal'}</h2></div></div>{opportunity && <><div className="opportunity-metric"><span>Current attachment</span><strong>{opportunity.attachment_rate}%</strong></div><p>Among the demo laptop-buyer cohort, this category has the strongest policy-eligible attachment opportunity.</p><button className="text-button" onClick={onOpenCampaign}>Explore campaign draft <ArrowUpRight size={16} /></button></>}</section>
      <section className="recent-actions"><div className="section-heading"><span>Recent</span><div><p>Agent activity</p><h2>Audit-linked actions</h2></div></div><div>{analytics.recent_actions?.length ? analytics.recent_actions.slice().reverse().map((event, index) => <div className="mini-event" key={`${event.timestamp}-${index}`}><span className="event-dot" /><div><strong>{displayEvent(event.event)}</strong><p>{formatTime(event.timestamp)}</p></div></div>) : <p className="muted">No audit actions recorded.</p>}</div></section>
    </div>
  </section>
}

export function CampaignBuilder({ campaign, loading, onCreate }) {
  const [goal, setGoal] = useState('Increase laptop accessory sales.')
  const submit = (event) => { event.preventDefault(); if (goal.trim()) onCreate(goal.trim()) }
  return <section className="merchant-page campaign-page"><div className="page-title"><div><span className="eyebrow"><Megaphone size={14} /> Campaign orchestrator</span><h1>Create a policy-aware campaign draft.</h1><p>NovaCart selects real catalog products and applies the merchant discount limit.</p></div></div>
    <form className="campaign-prompt" onSubmit={submit}><label htmlFor="campaign-goal">What do you want to improve?</label><div><input id="campaign-goal" value={goal} onChange={(event) => setGoal(event.target.value)} /><button className="button primary" disabled={loading}><Send size={16} /> Generate draft</button></div></form>
    {loading && <DashboardSkeleton />}
    {!loading && !campaign && <EmptyState title="No draft yet" message="Describe a merchant objective to build a policy-aware campaign draft." icon={Megaphone} />}
    {!loading && campaign && <CampaignDraft campaign={campaign} />}
  </section>
}

function CampaignDraft({ campaign }) {
  const blocked = campaign.status === 'blocked'
  return <section className="campaign-draft"><header><div><span className={`draft-status ${blocked ? 'blocked' : ''}`}>{campaign.status}</span><h2>{campaign.campaign_name || 'Campaign review'}</h2><p>{campaign.goal}</p></div><div className="draft-date"><CalendarClock size={17} /> {campaign.duration_days ? `${campaign.duration_days} day duration` : 'Review required'}</div></header>
    {blocked ? <div className="policy-callout blocked"><CircleAlert size={19} /><p>{campaign.reason}</p></div> : <><div className="campaign-facts"><article><span>Opportunity detected</span><strong>{campaign.opportunity?.category}</strong><p>{campaign.opportunity?.attachment_rate}% attachment among demo laptop buyers</p></article><article><span>Target audience</span><strong>{campaign.target}</strong><p>Derived from the synthetic demo dataset</p></article><article><span>Offer</span><strong>{campaign.offer?.value}% off</strong><p>Maximum discount {formatINR(campaign.offer?.max_discount_inr)}</p></article></div>
      <div className="policy-callout"><ShieldCheck size={19} /><div><strong>Merchant policy reviewed</strong><p>{campaign.discount_validation?.allowed ? 'All selected product discounts are within the ₹500 policy cap.' : 'One or more discounts require review.'}</p></div></div>
      <section className="campaign-products"><div className="section-heading"><span>Catalog</span><div><p>Recommended products</p><h2>Products in this draft</h2></div></div><div className="product-grid compact-grid">{campaign.recommended_products?.map((product) => <ProductCard key={product.id} product={product} compact />)}</div></section>
      <section className="economics-unavailable"><CircleAlert size={18} /><div><strong>Campaign economics unavailable</strong><p>The existing backend does not calculate expected orders, revenue, discount cost, or ROI. This draft intentionally does not present simulated outcomes as actual performance.</p></div></section></>}
  </section>
}

export function AuditTrail({ audit, loading, reload }) {
  if (loading) return <DashboardSkeleton />
  const events = audit?.events || []
  return <section className="merchant-page audit-page"><div className="page-title"><div><span className="eyebrow"><Activity size={14} /> Audit trail</span><h1>Decisions leave a trace.</h1><p>Live events read from the backend audit log.</p></div><button className="button ghost" onClick={reload}>Refresh</button></div>{events.length ? <div className="audit-timeline">{events.slice().reverse().map((event, index) => <article className="audit-event" key={`${event.timestamp}-${index}`}><div className="timeline-marker"><CheckCircle2 size={15} /></div><div className="event-time">{formatTime(event.timestamp)}</div><div className="event-body"><h2>{displayEvent(event.event)}</h2>{Object.keys(event.details || {}).length > 0 && <dl>{Object.entries(event.details).filter(([key]) => !['result_ids', 'recommended_product_ids'].includes(key)).slice(0, 4).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{Array.isArray(value) ? value.join(', ') : String(value)}</dd></div>)}</dl>}</div></article>)}</div> : <EmptyState title="No audit activity" message="Events from customer and merchant workflows will appear here." icon={Activity} />}</section>
}

export function AIBuyerView({ onRequest, quote, loading }) {
  const [goal, setGoal] = useState('I need a coding laptop under ₹80,000.')
  const submit = (event) => { event.preventDefault(); if (goal.trim()) onRequest(goal.trim()) }
  return <section className="buyer-page"><div className="page-title"><div><span className="eyebrow"><Bot size={14} /> AI Buyer</span><h1>A structured commerce surface for AI agents.</h1><p>This is an API-ready catalog quote interface. It does not claim to connect to an external agent.</p></div></div><form className="campaign-prompt" onSubmit={submit}><label htmlFor="buyer-goal">Buyer goal</label><div><input id="buyer-goal" value={goal} onChange={(event) => setGoal(event.target.value)} /><button className="button primary" disabled={loading}><Send size={16} /> Request quote</button></div></form>{loading && <DashboardSkeleton />}{quote && !loading && <section className="buyer-quote"><div className="quote-status"><CheckCircle2 size={18} /><span>{quote.status.replaceAll('_', ' ')}</span><small>{quote.mode.replaceAll('_', ' ')}</small></div><div className="quote-grid"><div><span>Goal</span><p>{quote.goal}</p></div><div><span>Best catalog fit</span><p>{quote.recommendations?.best_fit ? `${quote.recommendations.best_fit.brand} ${quote.recommendations.best_fit.name}` : 'No catalog fit returned'}</p></div><div><span>Catalog price</span><p>{formatINR(quote.recommendations?.best_fit?.price_inr)}</p></div></div><p className="structured-note">The full structured response is available at <code>POST /api/ai-buyer/quote</code>. Cart prices and policy decisions remain server-authoritative.</p></section>}</section>
}

function DashboardSkeleton() { return <div className="dashboard-skeleton"><span /><span /><span /><span /></div> }

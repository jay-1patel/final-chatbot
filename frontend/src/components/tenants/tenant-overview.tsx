import { Link2, Phone, Rocket, Sparkles } from 'lucide-react'
import { useTenants } from '@/lib/tenants'
import { navigate } from '@/lib/router'
import { getVertical } from '@/lib/verticals'
import { FEATURE_LABELS } from '@/lib/verticals'
import type { FeatureFlag } from '@/lib/types'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, LoadingBlock } from '@/components/ui/feedback'
import { PageHeader } from '@/components/layout/page-header'
import { VerticalGlyph } from '@/components/vertical-icon'
import { useResolved } from './hooks'

const GROUPS: { label: string; flags: FeatureFlag[] }[] = [
  { label: 'Selling online', flags: ['cart', 'buy_now', 'orders', 'payments', 'track_order', 'returns', 'distributors'] },
  { label: 'Offerings & brochure', flags: ['offerings', 'offering_details', 'services', 'products', 'products_schemes', 'brochure_pdf'] },
  { label: 'Enquiries', flags: ['lead_capture', 'quote', 'callback', 'book_appointment'] },
  { label: 'Support', flags: ['faq', 'kb', 'complaints', 'campaigns'] },
  { label: 'Human', flags: ['handoff', 'human_handover'] },
]

export function TenantOverview({ tenantId }: { tenantId: string }) {
  const { tenants } = useTenants()
  const tenant = tenants.find((t) => t.id === tenantId) ?? null
  const { data, error, loading } = useResolved(tenantId)
  const vertical = getVertical(tenant?.vertical)

  if (loading) return <LoadingBlock label="Reading the live profile…" />
  if (error || !data) {
    return (
      <Alert tone="danger" title="Could not read the profile">
        {error ?? 'Unknown error'}
      </Alert>
    )
  }

  const brand = data.brand
  const onFlags = Object.entries(data.features).filter(([, on]) => on).map(([flag]) => flag as FeatureFlag)

  const stats = [
    { label: 'Live version', value: data.version ? `v${data.version}` : 'none', tone: data.version ? 'success' : 'warning' },
    { label: 'Menu buttons', value: String(data.menu?.buttons?.length ?? 0), tone: 'accent' },
    { label: 'Active intents', value: String(data.active_intents?.length ?? 0), tone: 'accent' },

  ] as const

  return (
    <div>
      <PageHeader
        title={
          <span className="flex items-center gap-3">
            <VerticalGlyph name={vertical.icon} className="h-6 w-6 text-accent-700" />
            {brand.name || tenant?.display_name || tenantId}
          </span>
        }
        description={vertical.blurb}
        meta={
          <>
            <Badge tone="accent">{vertical.label}</Badge>
            <Badge tone={data.version ? 'success' : 'warning'}>
              {data.version ? `live · v${data.version}` : 'no published version'}
            </Badge>
            <Badge tone="neutral">source: {data.source}</Badge>
            {brand.website && (
              <a
                href={brand.website}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-accent-700 hover:text-accent-700"
              >
                <Link2 className="h-3 w-3" />
                {brand.website.replace(/^https?:\/\//, '')}
              </a>
            )}
            {tenant?.waba_phone_id && (
              <Badge tone="neutral">
                <Phone className="h-3 w-3" />
                {tenant.waba_phone_id}
              </Badge>
            )}
          </>
        }
        actions={
          <>
            <Button size="sm" variant="secondary" onClick={() => navigate(`/tenants/${tenantId}/profile`)}>
              Edit profile
            </Button>
            <Button
              size="sm"
              variant="primary"
              icon={<Rocket className="h-4 w-4" />}
              onClick={() => navigate(`/tenants/${tenantId}/versions`)}
            >
              Publish
            </Button>
          </>
        }
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label} className="px-4 py-3.5">
            <p className="text-xs uppercase tracking-wide text-slate-500">{stat.label}</p>
            <p className="mt-1.5 text-xl font-semibold text-slate-100">{stat.value}</p>
            <Badge tone={stat.tone} className="mt-2">
              {stat.tone === 'success' ? 'published' : stat.tone === 'warning' ? 'action needed' : 'live'}
            </Badge>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Bot identity" description="Exactly what the bot will call things." icon={<Sparkles className="h-4 w-4" />} />
          <CardBody className="space-y-3 text-xs">
            <Row label="Bot name" value={brand.bot_name || brand.name} />
            <Row label="Tagline" value={brand.tagline || '—'} />
            <Row label="Calls its offerings" value={String(data.vocabulary?.item_noun ?? '—')} />
            <Row label="Enquiries are" value={String(data.vocabulary?.lead_noun ?? '—')} />
            <Row label="Support email" value={brand.support_email || '—'} />
            <Row label="Support phone" value={brand.support_phone || '—'} />
            <Row
              label="Working hours"
              value={
                data.business_hours?.always_open
                  ? 'Always open'
                  : `${data.business_hours?.open}–${data.business_hours?.close} (${data.business_hours?.timezone})`
              }
            />
            <Row label="Menu greeting" value={data.menu?.body || '—'} />
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Capabilities in force"
            description="Live flags, straight from the published profile."
            icon={<Sparkles className="h-4 w-4" />}
          />
          <CardBody className="space-y-4">
            {GROUPS.map((group) => {
              const enabled = group.flags.filter((f) => data.features[f])
              if (!enabled.length) return null
              return (
                <div key={group.label}>
                  <p className="text-xs uppercase tracking-wide text-slate-500">{group.label}</p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {enabled.map((flag) => (
                      <Badge key={flag} tone="accent">
                        {FEATURE_LABELS[flag].label}
                      </Badge>
                    ))}
                  </div>
                </div>
              )
            })}
            {!onFlags.length && <p className="text-xs text-slate-500">No features enabled.</p>}
          </CardBody>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader
          title="The WhatsApp menu this tenant gets"
          description="Rendered from the profile, with gated buttons already hidden."
          actions={
            <Button size="sm" variant="ghost" onClick={() => navigate(`/tenants/${tenantId}/menu`)}>
              Details
            </Button>
          }
        />
        <CardBody>
          {(() => {
            const seenTitles = new Set<string>()
            const validButtons = (data.menu?.buttons || []).filter((b) => {
              if (!b.enabled) return false
              if (!b.title || !b.title.trim()) return false
              const norm = b.title.trim().toLowerCase()
              if (['button title', 'parameter', 'action', '__new_page__', 'none', 'empty'].includes(norm)) return false
              if (b.requires_feature && !data.features[b.requires_feature as FeatureFlag]) return false
              if (seenTitles.has(norm)) return false
              seenTitles.add(norm)
              return true
            })

            if (!validButtons.length) {
              return <p className="text-xs text-slate-500">No menu buttons configured in the profile.</p>
            }

            return (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {validButtons.map((button) => {
                  const iconEmoji = button.icon || getFallbackButtonIcon(button.title, data.vertical)
                  return (
                    <div
                      key={button.id}
                      className="flex items-start gap-3 rounded-lg bg-surface-panel p-3.5 ring-1 ring-inset ring-surface-line hover:ring-surface-line/80 transition-all shadow-xs"
                    >
                      {button.image_url ? (
                        <img
                          src={button.image_url}
                          alt=""
                          className="h-9 w-9 rounded-md object-cover border border-white/10 shrink-0 shadow-xs"
                          onError={(e) => {
                            ;(e.currentTarget as HTMLElement).style.display = 'none'
                          }}
                        />
                      ) : (
                        <div className="h-9 w-9 rounded-md flex items-center justify-center bg-white/5 border border-white/10 text-lg shrink-0 shadow-inner">
                          {iconEmoji}
                        </div>
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-1.5">
                          <span className="text-xs font-semibold text-slate-100 truncate">{button.title}</span>
                          {button.section && button.section !== 'General' && (
                            <span className="text-[9px] uppercase tracking-wider text-slate-400 bg-white/5 px-1.5 py-0.5 rounded border border-white/5 shrink-0">
                              {button.section.replace(/^[^\w\s]+/, '').trim()}
                            </span>
                          )}
                        </div>
                        {button.description ? (
                          <p className="mt-1 text-xs leading-relaxed text-slate-400 line-clamp-2">{button.description}</p>
                        ) : (
                          <p className="mt-1 text-xs italic text-slate-500">Interactive WhatsApp action</p>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          })()}
        </CardBody>
      </Card>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-surface-line pb-2 last:border-0">
      <span className="shrink-0 text-slate-500">{label}</span>
      <span className="min-w-0 text-right text-slate-200">{value}</span>
    </div>
  )
}

function getFallbackButtonIcon(title: string, vertical?: string): string {
  const t = (title || '').toLowerCase()
  const v = (vertical || '').toLowerCase()

  if (['callback', 'call', 'advisor', 'expert', 'talk to', 'contact', 'speak', 'phone', 'human'].some((k) => t.includes(k))) return '📞'
  if (['support', 'help', 'ticket', 'complaint', 'issue'].some((k) => t.includes(k))) return '💬'
  if (['quote', 'pricing', 'plans', 'cost', 'fee', 'rate'].some((k) => t.includes(k))) return '💰'
  if (['brochure', 'download', 'pdf', 'terms'].some((k) => t.includes(k))) return '📄'
  if (['visit', 'schedule', 'book', 'appointment'].some((k) => t.includes(k))) return '📅'

  if (v.includes('estate') || v.includes('property')) {
    if (['villa', 'plot', 'land'].some((k) => t.includes(k))) return '🏡'
    if (['rera', 'legal'].some((k) => t.includes(k))) return '⚖️'
    return '🏢'
  }
  if (v.includes('bank') || v.includes('finance')) {
    if (['loan', 'credit', 'mortgage', 'emi'].some((k) => t.includes(k))) return '💳'
    if (['invest', 'mutual', 'wealth'].some((k) => t.includes(k))) return '📈'
    return '🏦'
  }
  if (v.includes('travel') || v.includes('tour')) {
    if (['destination', 'place', 'city'].some((k) => t.includes(k))) return '🗺️'
    if (['visa', 'passport'].some((k) => t.includes(k))) return '🛂'
    if (['itinerary', 'custom'].some((k) => t.includes(k))) return '🧭'
    if (['policy', 'cancellation'].some((k) => t.includes(k))) return '📋'
    return '🌴'
  }
  if (v.includes('software') || v.includes('it')) {
    if (['tech', 'stack'].some((k) => t.includes(k))) return '⚙️'
    if (['project', 'portfolio'].some((k) => t.includes(k))) return '🚀'
    if (['career', 'job'].some((k) => t.includes(k))) return '💼'
    return '💻'
  }
  if (v.includes('ecom') || v.includes('retail')) return '🛍️'
  if (v.includes('health') || v.includes('clinic')) return '🏥'

  return '✨'
}

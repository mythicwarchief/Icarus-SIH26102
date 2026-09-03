'use client'

import Link from 'next/link'
import { useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTheme } from 'next-themes'
import { ArrowLeft, ArrowRight, ArrowUpRight, Bell, ChevronRight, CircleHelp, FolderKanban, LayoutDashboard, ListFilter, LogOut, Menu, Moon, RotateCcw, Search, Settings, ShieldCheck, Sun, TrendingUp, X } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, LineChart, Line } from 'recharts'
import { formatINR, monthlyTrend, regionalRisk, statusLabels, type Project, type ProjectStatus, type RiskTier } from '@/lib/types'
import { useAsyncData } from '@/hooks/useAsyncData'
import { MetricCardsSkeleton, RegistryRowSkeleton, RiskGaugeSkeleton, ErrorPanel, Skeleton } from '@/components/LoadingStates'
import { CostEstimatePanel, DelayRiskPanel, DuplicateIntelligencePanel } from '@/components/intelligence/InnovationPanels'
import { getAnomalySummary } from '@/services/summaryApi'
import { getAllScoredWorksComplete, getScoredWork, getHighRiskAnomalies } from '@/services/api'
import { adaptAnomalyRecordToProject } from '@/services/realAdapter'

const rise = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0 } }

export function CountUp({ value }: { value: number }) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    const start = performance.now()
    let frame = 0
    const tick = (now: number) => { const progress = Math.min((now - start) / 800, 1); setCount(Math.round(value * (1 - Math.pow(1 - progress, 3)))); if (progress < 1) frame = requestAnimationFrame(tick) }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [value])
  return <span>{count}</span>
}

export function Reveal({ children, index = 0, className = '' }: { children: React.ReactNode; index?: number; className?: string }) {
  return (
    <motion.div
      className={className}
      variants={rise}
      initial="hidden"
      animate="show"
      transition={{ duration: .45, ease: 'easeOut', delay: Math.min(index, 3) * .05 }}
    >
      {children}
    </motion.div>
  )
}

function HeaderPopover({ trigger, children, align = 'right' }: { trigger: React.ReactNode; children: React.ReactNode; align?: 'left' | 'right' }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(o => !o)} className="grid size-9 place-items-center rounded-lg border border-border hover:bg-accent">
        {trigger}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.15, ease: [0.22, 1, 0.36, 1] }}
            className={`absolute top-11 z-20 w-72 rounded-xl border border-border bg-card p-4 shadow-lg ${align === 'right' ? 'right-0' : 'left-0'}`}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function Shell({ children }: { children: React.ReactNode }) {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => setMounted(true), [])

  const navLinks = (
    <>
      <Nav href="/" icon={<LayoutDashboard size={17} />} label="Oversight dashboard" onClick={() => setMobileOpen(false)} />
      <Nav href="/projects" icon={<FolderKanban size={17} />} label="Project registry" onClick={() => setMobileOpen(false)} />
      <Nav href="/analytics" icon={<TrendingUp size={17} />} label="Analytics & trends" onClick={() => setMobileOpen(false)} />
    </>
  )

  return (
    <div className="min-h-screen bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-border bg-sidebar px-5 py-6 lg:flex lg:flex-col">
        <div className="flex items-center gap-3 px-2">
          <div className="grid size-9 place-items-center rounded-xl bg-primary text-primary-foreground">
            <ShieldCheck size={20} />
          </div>
          <div>
            <p className="font-serif text-xl font-bold tracking-tight">Nirikshan</p>
            <p className="text-[10px] uppercase tracking-[.2em] text-muted-foreground">Authority console</p>
          </div>
        </div>
        <nav className="mt-12 space-y-1">{navLinks}</nav>
        <div className="mt-auto rounded-2xl bg-accent p-4 text-sm">
          <p className="font-semibold">Review with confidence</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Nirikshan surfaces unusual patterns for human verification.
          </p>
          <Link href="/projects" className="mt-4 flex items-center gap-1 text-xs font-semibold text-primary">
            Open registry <ArrowUpRight size={13} />
          </Link>
        </div>
      </aside>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-black/50 lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-border bg-sidebar px-5 py-6 lg:hidden"
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            >
              <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-3">
                  <div className="grid size-9 place-items-center rounded-xl bg-primary text-primary-foreground">
                    <ShieldCheck size={20} />
                  </div>
                  <p className="font-serif text-xl font-bold tracking-tight">Nirikshan</p>
                </div>
                <button aria-label="Close menu" onClick={() => setMobileOpen(false)} className="grid size-9 place-items-center rounded-lg border border-border">
                  <X size={17} />
                </button>
              </div>
              <nav className="mt-10 space-y-1">{navLinks}</nav>
              <div className="mt-auto rounded-2xl bg-accent p-4 text-sm">
                <p className="font-semibold">Review with confidence</p>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  Nirikshan surfaces unusual patterns for human verification.
                </p>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-border bg-background/90 px-5 backdrop-blur md:px-8">
          <div className="flex items-center gap-3">
            <button aria-label="Open menu" onClick={() => setMobileOpen(true)} className="grid size-9 place-items-center rounded-lg border border-border lg:hidden">
              <Menu size={17} />
            </button>
            <div className="relative hidden md:block">
              <Search className="absolute left-3 top-2.5 text-muted-foreground" size={16} />
              <input
                aria-label="Search projects"
                placeholder="Search projects, locations..."
                className="h-9 w-72 rounded-lg border border-input bg-card pl-9 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              aria-label="Toggle theme"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="grid size-9 place-items-center rounded-lg border border-border hover:bg-accent"
            >
              {mounted && (theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />)}
            </button>

            <div className="hidden md:block">
              <HeaderPopover trigger={<CircleHelp size={17} />}>
                <p className="font-semibold">How Nirikshan works</p>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Risk scores and flags are system-generated signals, not findings. Every flagged project surfaces
                  unusual patterns — cost, delay, or duplication — for a human reviewer to verify before any action is taken.
                </p>
              </HeaderPopover>
            </div>

            <HeaderPopover trigger={<Settings size={17} />}>
              <p className="font-semibold">Settings</p>
              <div className="mt-3 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Theme</span>
                <button
                  onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                  className="flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-semibold hover:bg-accent"
                >
                  {mounted && (theme === 'dark' ? <Moon size={14} /> : <Sun size={14} />)}
                  {mounted && (theme === 'dark' ? 'Dark' : 'Light')}
                </button>
              </div>
              <button
                onClick={() => window.location.href = '/projects'}
                className="mt-3 flex w-full items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-accent"
              >
                <RotateCcw size={14} /> Reset registry filters
              </button>
            </HeaderPopover>

            <HeaderPopover trigger={<span className="text-xs font-bold text-primary">AS</span>}>
              <p className="font-semibold">Ananya Sharma</p>
              <p className="mt-0.5 text-xs text-muted-foreground">Authority reviewer · MPLADS oversight</p>
              <button className="mt-3 flex w-full items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-accent">
                <LogOut size={14} /> Sign out
              </button>
            </HeaderPopover>
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] px-5 py-8 md:px-8">{children}</main>
      </div>
    </div>
  )
}

function Nav({ href, icon, label, onClick }: { href: string; icon: React.ReactNode; label: string; onClick?: () => void }) {
  return (
    <Link href={href} onClick={onClick} className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground">
      {icon}{label}
    </Link>
  )
}
export function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) { return <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end"><div><p className="mb-2 text-xs font-semibold uppercase tracking-[.18em] text-primary">{eyebrow}</p><h1 className="font-serif text-3xl font-bold tracking-tight md:text-4xl">{title}</h1><p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">{description}</p></div>{action}</div> }
export function MetricCards() {
  const { data: s, loading, error, retry } = useAsyncData(() => getAnomalySummary(), [])
  if (loading) return <MetricCardsSkeleton />
  if (error || !s) return <ErrorPanel message={error ?? 'No summary data available.'} onRetry={retry} />
  const cards = [
    ['Projects monitored', s.total_works_analyzed, 'Across all regions', 'FolderKanban'],
    ['Flagged for review', s.total_anomalies, `${s.anomaly_rate_percent.toFixed(1)}% of portfolio`, 'Bell'],
    ['High priority', s.severity_distribution.critical + s.severity_distribution.high, 'Requires immediate attention', 'ShieldCheck'],
    ['Ongoing works', s.status_distribution.Ongoing, 'Currently in progress', 'TrendingUp'],
  ] as const
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map(([label, value, note, icon], i) => (
        <Reveal key={label} index={i}>
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="flex items-start justify-between">
              <p className="text-sm text-muted-foreground">{label}</p>
              <span className="text-primary">{icon === 'TrendingUp' ? <TrendingUp size={18} /> : icon === 'Bell' ? <Bell size={18} /> : icon === 'ShieldCheck' ? <ShieldCheck size={18} /> : <FolderKanban size={18} />}</span>
            </div>
            <p className="mt-4 text-3xl font-semibold tracking-tight"><CountUp value={value} /></p>
            <p className="mt-1 text-xs text-muted-foreground">{note}</p>
          </div>
        </Reveal>
      ))}
    </div>
  )
}
export function RiskChart() {
  const { data: s, loading, error, retry } = useAsyncData(() => getAnomalySummary(), [])
  if (loading) return <Panel title="Risk distribution" note="Current portfolio"><Skeleton className="h-64 w-full" /></Panel>
  if (error || !s) return <Panel title="Risk distribution" note="Current portfolio"><ErrorPanel message={error ?? 'No data available.'} onRetry={retry} /></Panel>
  const dist = [
    { name: 'No anomalies', value: s.total_works_analyzed - s.total_anomalies, fill: '#2f8f83' },
    { name: 'Medium severity', value: s.severity_distribution.medium, fill: '#d89b3d' },
    { name: 'High severity', value: s.severity_distribution.high + s.severity_distribution.critical, fill: '#c95c4b' },
  ]
  return (
    <Reveal>
      <Panel title="Risk distribution" note="Current portfolio">
        <div className="flex h-64 items-center gap-5">
          <ResponsiveContainer width="58%" height="100%">
            <PieChart>
              <Pie data={dist} dataKey="value" innerRadius={65} outerRadius={90} paddingAngle={3} animationDuration={800} animationEasing="ease-out">
                {dist.map(x => <Cell key={x.name} fill={x.fill} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-4">
            {dist.map(x => (
              <div key={x.name} className="flex items-center gap-2 text-sm">
                <span className="size-2.5 rounded-full" style={{ background: x.fill }} />
                <span className="text-muted-foreground">{x.name}</span>
                <b className="ml-auto"><CountUp value={x.value} /></b>
              </div>
            ))}
          </div>
        </div>
      </Panel>
    </Reveal>
  )
}
export function AnomalyChart() {
  const { data: s, loading, error, retry } = useAsyncData(() => getAnomalySummary(), [])
  if (loading) return <Panel title="Anomaly types" note="Flagged signals"><Skeleton className="h-64 w-full" /></Panel>
  if (error || !s) return <Panel title="Anomaly types" note="Flagged signals"><ErrorPanel message={error ?? 'No data available.'} onRetry={retry} /></Panel>
  const categoryLabels: Record<string, string> = { financial: 'Financial', temporal: 'Temporal', vendor: 'Vendor', compliance: 'Compliance', statistical: 'Statistical' }
  const data = Object.entries(s.category_distribution)
    .map(([key, value]) => ({ name: categoryLabels[key] ?? key, value }))
    .filter(d => d.value > 0)
    .sort((a, b) => b.value - a.value)
  return (
    <Reveal index={1}>
      <Panel title="Anomaly types" note="Flagged signals">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ left: 10, right: 10 }}>
              <CartesianGrid horizontal={false} strokeDasharray="3 3" />
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="name" width={105} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#2f8f83" radius={[0, 5, 5, 0]} animationDuration={800} animationEasing="ease-out" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </Reveal>
  )
}
export function TrendMini() { return <Reveal><Panel title="Flagging activity" note="Last 6 months"><div className="h-64"><ResponsiveContainer width="100%" height="100%"><LineChart data={monthlyTrend}><CartesianGrid vertical={false} strokeDasharray="3 3" /><XAxis dataKey="month" tick={{ fontSize: 11 }} /><YAxis hide /><Tooltip /><Line type="monotone" dataKey="flagged" stroke="#c95c4b" strokeWidth={3} dot={false} animationDuration={800} animationEasing="ease-out" /><Line type="monotone" dataKey="reviewed" stroke="#2f8f83" strokeWidth={2} dot={false} animationDuration={800} animationEasing="ease-out" /></LineChart></ResponsiveContainer></div></Panel></Reveal> }
export function Panel({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) { return <section className="rounded-2xl border border-border bg-card p-5 shadow-sm"><div className="mb-3 flex items-center justify-between"><h2 className="font-semibold">{title}</h2>{note && <span className="text-xs text-muted-foreground">{note}</span>}</div>{children}</section> }
export function Queue() {
  const { data, loading, error, retry } = useAsyncData(() => getHighRiskAnomalies(6), [])
  if (loading) return <Panel title="Priority investigation queue" note="Loading…"><RegistryRowSkeleton /></Panel>
  if (error || !data) return <Panel title="Priority investigation queue" note="—"><ErrorPanel message={error ?? 'No data available.'} onRetry={retry} /></Panel>
  const queue = data.data.map(adaptAnomalyRecordToProject)
  return (
    <Panel title="Priority investigation queue" note={`${queue.length} surfaced`}>
      <div className="divide-y divide-border">
        {queue.map(p => (
          <Link href={`/projects/${p.id}`} key={p.id} className="flex items-center gap-4 py-3 first:pt-1 last:pb-1">
            <span className={`grid size-9 place-items-center rounded-xl text-sm font-bold ${p.riskTier === 'high' ? 'bg-risk-high/10 text-risk-high' : 'bg-risk-medium/10 text-risk-medium'}`}>
              <CountUp value={p.riskScore} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{p.name}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{p.location} · {p.anomalies?.[0]?.explanation}</p>
            </div>
            <ChevronRight size={17} className="text-muted-foreground" />
          </Link>
        ))}
      </div>
    </Panel>
  )
}
export function Dashboard() { return <Shell><PageHeading eyebrow="MPLADS oversight / 01" title="Good morning !!!" description="A clear view of project health, unusual patterns, and the works that need your attention." action={<Link href="/projects" className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground">Review projects <ArrowUpRight size={16} /></Link>} /><MetricCards /><div className="mt-5 grid gap-5 lg:grid-cols-2"><RiskChart /><AnomalyChart /></div><div className="mt-5 grid gap-5 lg:grid-cols-[1.25fr_.75fr]"><Queue /><TrendMini /></div><p className="mt-8 text-center text-xs text-muted-foreground">Signals are system-generated indicators. Every flag requires human verification before action.</p></Shell> }
export function ProjectRow({ p }: { p: Project }) { return <Link href={`/projects/${p.id}`} className="grid grid-cols-[1fr_110px_100px_95px_30px] items-center gap-3 border-b border-border px-4 py-4 hover:bg-accent/50"><div><p className="text-sm font-medium">{p.name}</p><p className="text-xs text-muted-foreground">{p.id} · {p.location}, {p.region}</p></div><span className="text-sm">{formatINR(p.sanctionedAmount)}</span><span className="text-sm">{statusLabels[p.status]}</span><span className={`text-sm font-semibold ${p.riskTier === 'high' ? 'text-risk-high' : p.riskTier === 'medium' ? 'text-risk-medium' : 'text-risk-low'}`}>{p.riskScore} / 100</span><ChevronRight size={16} className="text-muted-foreground" /></Link> }
export function Registry() {
  const { data: rawWorks, loading, error, retry } = useAsyncData(() => getAllScoredWorksComplete(), [])
  const allProjects = useMemo(() => rawWorks?.map(adaptAnomalyRecordToProject), [rawWorks])
  const [query, setQuery] = useState('')
  const [risk, setRisk] = useState<'all' | RiskTier>('all')
  const [status, setStatus] = useState<'all' | ProjectStatus>('all')
  const [page, setPage] = useState(1)
  const pageSize = 20
  const filtered = useMemo(
    () => (allProjects ?? []).filter(p =>
      `${p.name} ${p.location} ${p.id}`.toLowerCase().includes(query.toLowerCase())
      && (risk === 'all' || p.riskTier === risk)
      && (status === 'all' || p.status === status)
    ),
    [allProjects, query, risk, status]
  )
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const visible = filtered.slice((page - 1) * pageSize, page * pageSize)
  useEffect(() => setPage(1), [query, risk, status, allProjects])

  return (
    <Shell>
      <PageHeading
        eyebrow="Project registry / 02"
        title="All projects"
        description="Search and review the full MPLADS portfolio. Risk scores prioritize attention; they do not determine outcomes."
        action={<button className="inline-flex items-center gap-2 rounded-xl border border-border px-4 py-2.5 text-sm font-semibold"><ListFilter size={16} /> Filters</button>}
      />
      <div className="mb-5 flex flex-col gap-3 md:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 text-muted-foreground" size={16} />
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search by project, ID, or location" className="h-10 w-full rounded-xl border border-input bg-card pl-9 text-sm outline-none focus:ring-2 focus:ring-ring" />
        </div>
        <select aria-label="Risk tier filter" value={risk} onChange={e => setRisk(e.target.value as 'all' | RiskTier)} className="h-10 rounded-xl border border-input bg-card px-3 text-sm">
          <option value="all">All risk tiers</option>
          <option value="high">High risk</option>
          <option value="medium">Medium risk</option>
          <option value="low">Low risk</option>
        </select>
        <select aria-label="Project status filter" value={status} onChange={e => setStatus(e.target.value as 'all' | ProjectStatus)} className="h-10 rounded-xl border border-input bg-card px-3 text-sm">
          <option value="all">All statuses</option>
          <option value="ongoing">Ongoing</option>
          <option value="completed">Completed</option>
          <option value="not_started">Not started</option>
        </select>
      </div>
      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        <div className="hidden grid-cols-[1fr_110px_100px_95px_30px] gap-3 border-b border-border bg-accent/50 px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground md:grid">
          <span>Project</span><span>Sanctioned</span><span>Status</span><span>Risk score</span><span />
        </div>
        {loading ? (
          <RegistryRowSkeleton />
        ) : error ? (
          <div className="p-4"><ErrorPanel message={error} onRetry={retry} /></div>
        ) : (
          <div>
            {visible.length > 0 ? visible.map(p => <ProjectRow key={p.id} p={p} />) : (
              <div className="flex flex-col items-center gap-3 px-4 py-16 text-center">
                <Search size={28} className="text-muted-foreground" />
                <p className="font-semibold">No projects match your filters</p>
                <button onClick={() => { setQuery(''); setRisk('all'); setStatus('all') }} className="mt-2 rounded-lg border border-border px-4 py-2 text-sm font-semibold hover:bg-accent">Clear all filters</button>
              </div>
            )}
          </div>
        )}
      </div>
      {!loading && !error && (
        <div className="mt-4 flex flex-col gap-3 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>Showing {filtered.length ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, filtered.length)} of {filtered.length} projects</span>
          <div className="flex items-center gap-1">
            <button aria-label="Previous page" disabled={page === 1} onClick={() => setPage(p => p - 1)} className="grid size-8 place-items-center rounded-lg border border-border disabled:opacity-40"><ArrowLeft size={14} /></button>
            {Array.from({ length: pages }, (_, i) => i + 1).map(n => (
              <button key={n} aria-label={`Page ${n}`} onClick={() => setPage(n)} className={`grid size-8 place-items-center rounded-lg border text-xs ${n === page ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:bg-accent'}`}>{n}</button>
            ))}
            <button aria-label="Next page" disabled={page === pages} onClick={() => setPage(p => p + 1)} className="grid size-8 place-items-center rounded-lg border border-border disabled:opacity-40"><ArrowRight size={14} /></button>
          </div>
        </div>
      )}
    </Shell>
  )
}
export function DuplicateMatchPanel({ project }: { project: Project }) { const match = project.duplicateMatch; if (!match) return null; return <Panel title="Potential duplicate match" note="Requires human verification"><div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-stretch"><div className="rounded-xl border border-border p-4"><p className="text-xs text-muted-foreground">Current project</p><p className="mt-2 font-semibold">{project.name}</p><p className="mt-1 text-xs text-muted-foreground">{project.id}</p></div><div className="flex flex-col items-center justify-center rounded-xl bg-risk-medium/10 px-5 py-3 text-center"><p className="text-2xl font-bold text-risk-medium"><CountUp value={match.similarityScore} />%</p><p className="text-xs text-muted-foreground">similarity</p></div><div className="rounded-xl border border-border p-4"><p className="text-xs text-muted-foreground">Matched project</p><p className="mt-2 font-semibold">{match.matchedProjectName}</p><p className="mt-1 text-xs text-muted-foreground">{match.matchedProjectId}</p></div></div><p className="mt-4 text-sm leading-relaxed text-muted-foreground"><span className="font-medium text-foreground">Why it surfaced:</span> {match.reason}</p></Panel> }
export function Investigation({ project }: { project: Project }) { return <Shell><Link href="/projects" className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft size={15} /> Back to registry</Link><PageHeading eyebrow="Project investigation / 03" title={project.name} description={`${project.id} · ${project.location}, ${project.region}`} action={<span className={`rounded-full px-3 py-1.5 text-sm font-semibold ${project.isFlagged ? 'bg-risk-medium/10 text-risk-medium' : 'bg-risk-low/10 text-risk-low'}`}>{project.isFlagged ? 'Flagged for review' : 'No active flags'}</span>} /><div className="grid gap-5 lg:grid-cols-[.8fr_1.2fr]"><Panel title="Risk score" note="Explainable indicator"><div className="flex items-center gap-6"><div className={`grid size-32 place-items-center rounded-full border-[12px] ${project.riskTier === 'high' ? 'border-risk-high/30 text-risk-high' : project.riskTier === 'medium' ? 'border-risk-medium/30 text-risk-medium' : 'border-risk-low/30 text-risk-low'}`}><span className="text-3xl font-bold"><CountUp value={project.riskScore} /></span></div><div><p className="font-semibold capitalize">{project.riskTier} priority</p><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{project.isFlagged ? 'This project shows unusual behavior compared with similar works and requires human verification.' : 'No unusual behavior is currently surfaced by the screening rules.'}</p></div></div></Panel><Panel title="Key financials"><div className="grid grid-cols-2 gap-5">{[['Sanctioned', formatINR(project.sanctionedAmount)], ['Released', formatINR(project.releasedAmount)], ['Utilized', formatINR(project.utilizedAmount)], ['Planned duration', `${project.plannedDuration} days`]].map(([a, b]) => <div key={a}><p className="text-xs text-muted-foreground">{a}</p><p className="mt-1 text-lg font-semibold">{b}</p></div>)}</div></Panel></div><div className="mt-5 grid gap-5 lg:grid-cols-[1.2fr_.8fr]"><Panel title="Why this was flagged" note="Plain-English explanation">{project.anomalies?.length ? <div className="space-y-3">{project.anomalies.map((a, i) => <div key={`${a.type}-${i}`} className="rounded-xl bg-accent p-4"><div className="flex items-center justify-between"><p className="font-medium capitalize">{a.type.replaceAll('_', ' ')}</p><span className="text-xs text-muted-foreground">{Math.round(a.confidence * 100)}% confidence</span></div><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{a.explanation}</p></div>)}</div> : <p className="text-sm text-muted-foreground">No active screening signals. Continue routine monitoring.</p>}</Panel><Panel title="Project timeline"><div className="space-y-4 text-sm"><div><p className="text-xs text-muted-foreground">Sanctioned</p><p className="mt-1">{project.sanctionedDate}</p></div><div><p className="text-xs text-muted-foreground">Work started</p><p className="mt-1">{project.workStartDate ?? 'Not started'}</p></div><div><p className="text-xs text-muted-foreground">Completed</p><p className="mt-1">{project.completedDate ?? 'In progress'}</p></div></div></Panel></div>{project.duplicateMatch && <div className="mt-5"><DuplicateMatchPanel project={project} /></div>}<p className="mt-8 text-center text-xs text-muted-foreground">This is an explainable screening signal, not a finding. Verify against source records before taking action.</p></Shell> }

export function InvestigationWithLoading({ workId }: { workId: string }) {
  const { data: rawWork, loading, error, retry } = useAsyncData(() => getScoredWork(workId), [workId])
  const project = rawWork ? adaptAnomalyRecordToProject(rawWork) : null
  if (loading) {
    return (
      <Shell>
        <PageHeading eyebrow="Project investigation / 03" title="Loading project…" description="Fetching the latest screening data for this work." />
        <Panel title="Risk score" note="Explainable indicator"><RiskGaugeSkeleton /></Panel>
      </Shell>
    )
  }
  if (error || !project) {
    return (
      <Shell>
        <ErrorPanel message={error ?? 'This project could not be found.'} onRetry={retry} />
      </Shell>
    )
  }
    return (
    <>
      <Investigation project={project} />
      <div className="lg:pl-64">
        <div className="mx-auto max-w-[1500px] px-5 pb-8 md:px-8">
          <div className="grid gap-5 lg:grid-cols-2">
            <CostEstimatePanel workId={workId} />
            <DelayRiskPanel workId={workId} />
          </div>
          <div className="mt-5">
            <DuplicateIntelligencePanel workId={workId} />
          </div>
        </div>
      </div>
    </>
  )
}

export function Analytics() { return <Shell><PageHeading eyebrow="Analytics / 04" title="Portfolio trends" description="Understand how screening signals and expenditure patterns move across the portfolio." /><div className="grid gap-5 lg:grid-cols-2"><Panel title="Flagging and review trend" note="Monthly activity"><div className="h-80"><ResponsiveContainer width="100%" height="100%"><LineChart data={monthlyTrend}><CartesianGrid vertical={false} strokeDasharray="3 3" /><XAxis dataKey="month" /><YAxis /><Tooltip /><Line dataKey="flagged" name="Flagged" stroke="#c95c4b" strokeWidth={3} animationDuration={800} animationEasing="ease-out" /><Line dataKey="reviewed" name="Reviewed" stroke="#2f8f83" strokeWidth={3} animationDuration={800} animationEasing="ease-out" /></LineChart></ResponsiveContainer></div></Panel><Panel title="Regional risk index" note="Relative indicator"><div className="h-80"><ResponsiveContainer width="100%" height="100%"><BarChart data={regionalRisk}><CartesianGrid vertical={false} strokeDasharray="3 3" /><XAxis dataKey="region" tick={{ fontSize: 10 }} /><YAxis /><Tooltip /><Bar dataKey="risk" name="Risk index" fill="#d89b3d" radius={[5, 5, 0, 0]} animationDuration={800} animationEasing="ease-out" /></BarChart></ResponsiveContainer></div></Panel></div></Shell> }
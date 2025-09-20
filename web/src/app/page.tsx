"use client"

import useSWR from 'swr'
import { useEffect, useMemo, useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8081'
const fetcher = (url: string) => fetch(url).then(r => r.json())

type Summary = {
  window: string
  total_commits: number
  total_lines_updated: number
  repos_updated_count: number
  last_checked_at: string | null
  per_repo: { id: number, full_name: string, commits_count: number, is_private: boolean }[]
}

export default function HomePage() {
  const summaryUrl = `${API_BASE}/metrics/summary?window=24h`
  const { data, error, isLoading, mutate } = useSWR<Summary>(summaryUrl, fetcher, { refreshInterval: 15000 })
  const [refreshing, setRefreshing] = useState(false)
  const [showProgress, setShowProgress] = useState(true)
  const [tapeVariant, setTapeVariant] = useState<'green'|'amber'|'red'|'mint'>('green')
  const [tapeText, setTapeText] = useState<string>('Booting · Connecting to API · Loading summary …')

  async function refreshNow() {
    try {
      setRefreshing(true)
      setShowProgress(true)
      setTapeVariant('amber')
      setTapeText('Refreshing · Triggering ingestion · Updating summary …')
      await fetch(`${API_BASE}/admin/ingest`, { method: 'POST' })
      // revalidate summary after triggering
      await mutate()
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    if (isLoading && !refreshing) {
      setShowProgress(true)
      setTapeVariant('green')
      setTapeText('Booting · Connecting to API · Loading summary …')
    }
  }, [isLoading, refreshing])

  useEffect(() => {
    if (data && !isLoading) {
      setTapeVariant('mint')
      setTapeText(`Summary ready · ${data.total_lines_updated} lines · ${data.repos_updated_count} repos · window ${data.window}`)
      const t = setTimeout(() => setShowProgress(false), 400)
      return () => clearTimeout(t)
    }
  }, [data, isLoading])

  return (
    <main className="max-w-5xl mx-auto space-y-6">
      <header className="ink-panel p-6 flex items-center justify-between gap-4 relative">
        <div>
          <h1 className="text-3xl font-bold mb-1">Git Habit Tracker</h1>
          <p className="opacity-80">Activity in the last 24 hours</p>
        </div>
        <div className="hidden md:block flex-1 px-4">
          <div className={`log-tape ${tapeVariant}`} aria-live="polite">
            <div className="tape-track">
              <div className="tape-scroll">
                <span>{tapeText}</span>
                <span>• {tapeText}</span>
                <span>• {tapeText}</span>
                <span>• {tapeText}</span>
              </div>
              <div className="tape-scroll" aria-hidden>
                <span>{tapeText}</span>
                <span>• {tapeText}</span>
                <span>• {tapeText}</span>
                <span>• {tapeText}</span>
              </div>
            </div>
            <div className="tape-fade" />
          </div>
        </div>
        <button onClick={refreshNow} disabled={refreshing} className="pill hover:translate-y-px active:translate-y-[2px] transition-transform">
          {refreshing ? 'Refreshing…' : 'Refresh now'}
        </button>
        {showProgress && (
          <div className="absolute -bottom-3 left-4 right-4">
            <div className="progress-host">
              <div className="progress-bar" />
            </div>
          </div>
        )}
      </header>

      <section className="ink-panel p-6 flex items-center justify-between">
        <div>
          <div className="text-sm opacity-80">Lines updated (24h)</div>
          <div className="big-number font-extrabold">{isLoading ? '…' : (data?.total_lines_updated ?? 0)}</div>
        </div>
        <div className="text-right space-y-1">
          <div>
            <div className="text-sm opacity-80">Repos updated</div>
            <div className="text-lg font-semibold">{isLoading ? '…' : (data?.repos_updated_count ?? 0)}</div>
          </div>
          <div className="text-xs opacity-80">Last checked: {data?.last_checked_at ? new Date(data.last_checked_at).toLocaleString() : '—'}</div>
        </div>
      </section>

      <section className="grid md:grid-cols-2 gap-4">
        {data?.per_repo?.map(r => (
          <a key={r.id} href={`/repo/${r.id}`} className="ink-panel p-4 block hover:-translate-y-0.5 transition-transform">
            <div className="flex items-center justify-between">
              <div className="font-semibold flex items-center gap-2">
                <span>{r.full_name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded-full border border-black/70" style={{borderWidth:2, background:'white'}}>
                  {r.is_private ? 'private' : 'public'}
                </span>
              </div>
              <div className="text-lg">{r.commits_count}</div>
            </div>
          </a>
        ))}
      </section>
      {error && <div className="text-red-700">Error loading data</div>}
    </main>
  )
}

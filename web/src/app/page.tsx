"use client"

import useSWR from 'swr'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8081'
const fetcher = (url: string) => fetch(url).then(r => r.json())

type Summary = {
  window: string
  total_commits: number
  last_checked_at: string | null
  per_repo: { id: number, full_name: string, commits_count: number, is_private: boolean }[]
}

export default function HomePage() {
  const { data, error, isLoading } = useSWR<Summary>(`${API_BASE}/metrics/summary?window=24h`, fetcher, { refreshInterval: 15000 })

  return (
    <main className="max-w-5xl mx-auto space-y-6">
      <header className="ink-panel p-6">
        <h1 className="text-3xl font-bold mb-2">Git Habit Tracker</h1>
        <p className="opacity-80">Commits in the last 24 hours across your repos</p>
      </header>

      <section className="ink-panel p-6 flex items-center justify-between">
        <div>
          <div className="text-sm opacity-80">Commits (24h)</div>
          <div className="big-number font-extrabold">{isLoading ? '…' : (data?.total_commits ?? 0)}</div>
        </div>
        <div className="text-right">
          <div className="text-sm opacity-80">Last checked</div>
          <div>{data?.last_checked_at ? new Date(data.last_checked_at).toLocaleString() : '—'}</div>
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

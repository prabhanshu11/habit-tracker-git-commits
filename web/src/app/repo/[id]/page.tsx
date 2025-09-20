"use client"

import useSWR from 'swr'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8081'
const fetcher = (url: string) => fetch(url).then(r => r.json())

type Commit = {
  sha: string
  author_name?: string
  author_login?: string
  committed_at: string
  message: string
  additions: number
  deletions: number
  changed_files: number
  url?: string
}

type Metrics = {
  window: string
  repo_id: number
  full_name: string
  commits_count: number
  lines_added: number
  lines_deleted: number
}

export default function RepoPage({ params }: { params: { id: string } }) {
  const { data: metrics } = useSWR<Metrics>(`${API_BASE}/repos/${params.id}/metrics?window=24h`, fetcher, { refreshInterval: 20000 })
  const { data: commits } = useSWR<Commit[]>(`${API_BASE}/repos/${params.id}/commits?window=24h&limit=100`, fetcher, { refreshInterval: 20000 })

  return (
    <main className="max-w-5xl mx-auto space-y-6">
      <a href="/" className="inline-block underline">← Back</a>
      <header className="ink-panel p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">{metrics?.full_name || 'Repo'}</h1>
            <div className="opacity-70 text-sm">Window: {metrics?.window}</div>
          </div>
          <div className="text-right">
            <div className="text-sm opacity-80">Commits</div>
            <div className="text-2xl font-extrabold">{metrics?.commits_count ?? 0}</div>
          </div>
        </div>
        <div className="mt-3 text-sm">+{metrics?.lines_added ?? 0} / -{metrics?.lines_deleted ?? 0}</div>
      </header>

      <section className="ink-panel p-4">
        <div className="font-semibold mb-2">Recent commits</div>
        <ul className="space-y-3">
          {commits?.map(c => (
            <li key={c.sha} className="p-3 border border-ink rounded-md" style={{borderWidth: 2}}>
              <div className="flex items-center justify-between">
                <div className="font-medium truncate pr-2">{c.message}</div>
                <div className="text-sm opacity-70 ml-2">{new Date(c.committed_at).toLocaleString()}</div>
              </div>
              <div className="text-sm opacity-80">{c.author_login || c.author_name || 'Unknown'} • +{c.additions} / -{c.deletions} • {c.changed_files} files</div>
              {c.url && <a href={c.url} target="_blank" className="underline text-sm">View on GitHub</a>}
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}


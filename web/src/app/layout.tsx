import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Git Habit Tracker',
  description: 'Track commits in the last 24h',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen p-4">
          <div className="relative">
            <img className="star" style={{top: 8, left: 12}} src="/star-mint.svg" alt="*"/>
            <img className="star" style={{top: 64, right: 24}} src="/star-rose.svg" alt="*"/>
          </div>
          {children}
        </div>
      </body>
    </html>
  )
}


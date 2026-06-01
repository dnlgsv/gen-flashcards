import type { Metadata } from "next"
import "./globals.css"
import { Providers } from "./providers"
import { Sidebar } from "@/components/layout/Sidebar"

export const metadata: Metadata = {
  title: "LM Anki Cards Creator",
  description:
    "Create Anki vocabulary decks with definitions, examples, and audio in seconds.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen flex flex-col antialiased">
        <Providers>
          <div className="flex flex-1 flex-col md:flex-row">
            <Sidebar />
            <main className="min-w-0 flex-1">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  )
}

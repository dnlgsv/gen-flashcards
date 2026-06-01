import type { Metadata } from "next"
import "./globals.css"
import { Providers } from "./providers"
import { Sidebar } from "@/components/layout/Sidebar"

export const metadata: Metadata = {
  title: "LM Anki Cards Creator",
  description:
    "Create Anki vocabulary decks with definitions, examples, and audio in seconds.",
}

const themeScript = `
  (() => {
    const storedTheme = localStorage.getItem("lm-anki-cards-theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const theme = storedTheme ?? (prefersDark ? "dark" : "light");
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.style.colorScheme = theme;
  })();
`

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-screen flex flex-col bg-background text-foreground antialiased">
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

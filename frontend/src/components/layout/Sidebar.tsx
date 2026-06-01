"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Layers, PlusCircle, type LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { ThemeToggle } from "./ThemeToggle"

const LINKS: Array<{ href: string; label: string; icon: LucideIcon }> = [
  { href: "/create", label: "Create Deck", icon: PlusCircle },
  { href: "/dashboard", label: "My Decks", icon: Layers },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex shrink-0 border-b bg-background md:sticky md:top-0 md:h-screen md:w-52 md:flex-col md:border-b-0 md:border-r">
      <nav className="flex flex-1 gap-1 px-3 py-2 md:flex-col md:py-4">
        {LINKS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}?`)
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex h-9 items-center gap-2 rounded-md px-3 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{label}</span>
            </Link>
          )
        })}
      </nav>
      <div className="flex items-center px-3 py-2 md:border-t">
        <ThemeToggle />
      </div>
    </aside>
  )
}

"use client"

import { MessageSquare, Calendar, BarChart3, Bot } from "lucide-react"
import type { ActivePage } from "@/app/page"
import { cn } from "@/lib/utils"

interface SidebarProps {
  activePage: ActivePage
  setActivePage: (page: ActivePage) => void
}

const navItems = [
  { id: "sessions" as const, label: "Sessions", icon: MessageSquare },
  { id: "appointments" as const, label: "Appointments", icon: Calendar },
  { id: "analytics" as const, label: "Analytics", icon: BarChart3 },
]

export function Sidebar({ activePage, setActivePage }: SidebarProps) {
  return (
    <aside className="flex w-64 flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sidebar-primary">
          <Bot className="h-5 w-5 text-sidebar-primary-foreground" />
        </div>
        <span className="text-lg font-semibold text-sidebar-foreground">DentaAI</span>
      </div>
      
      <nav className="flex-1 p-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = activePage === item.id
            
            return (
              <li key={item.id}>
                <button
                  onClick={() => setActivePage(item.id)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-muted hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                  )}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </button>
              </li>
            )
          })}
        </ul>
      </nav>
      
      <div className="border-t border-sidebar-border p-4">
        <div className="text-xs text-sidebar-muted">
          Powered by AI
        </div>
      </div>
    </aside>
  )
}

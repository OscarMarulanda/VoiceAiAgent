"use client"

import { useState } from "react"
import { Sidebar } from "@/components/dashboard/sidebar"
import { Header } from "@/components/dashboard/header"
import { SessionsPage } from "@/components/dashboard/sessions-page"
import { AppointmentsPage } from "@/components/dashboard/appointments-page"
import { AnalyticsPage } from "@/components/dashboard/analytics-page"

export type ActivePage = "sessions" | "appointments" | "analytics"

export default function Dashboard() {
  const [activePage, setActivePage] = useState<ActivePage>("sessions")

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar activePage={activePage} setActivePage={setActivePage} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto p-6">
          {activePage === "sessions" && <SessionsPage />}
          {activePage === "appointments" && <AppointmentsPage />}
          {activePage === "analytics" && <AnalyticsPage />}
        </main>
      </div>
    </div>
  )
}

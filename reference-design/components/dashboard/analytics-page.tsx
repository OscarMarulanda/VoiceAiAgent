"use client"

import { Phone, MessageSquare, CalendarCheck, CalendarX, Clock, Zap } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { analyticsData } from "@/lib/mock-data"
import {
  PieChart,
  Pie,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts"

export function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <MetricCard
          title="Total Sessions Today"
          value={analyticsData.totalSessionsToday.toString()}
          icon={<MessageSquare className="h-4 w-4" />}
        />
        <MetricCard
          title="Voice Calls"
          value={analyticsData.voiceSessions.toString()}
          icon={<Phone className="h-4 w-4" />}
          subtitle={`${Math.round((analyticsData.voiceSessions / analyticsData.totalSessionsToday) * 100)}% of total`}
        />
        <MetricCard
          title="Chat Sessions"
          value={analyticsData.chatSessions.toString()}
          icon={<MessageSquare className="h-4 w-4" />}
          subtitle={`${Math.round((analyticsData.chatSessions / analyticsData.totalSessionsToday) * 100)}% of total`}
        />
        <MetricCard
          title="Appointments Booked"
          value={analyticsData.appointmentsBookedToday.toString()}
          icon={<CalendarCheck className="h-4 w-4" />}
          variant="success"
        />
        <MetricCard
          title="Cancelled Today"
          value={analyticsData.cancelledToday.toString()}
          icon={<CalendarX className="h-4 w-4" />}
          variant="destructive"
        />
        <MetricCard
          title="Avg Session Duration"
          value={analyticsData.avgSessionDuration}
          icon={<Clock className="h-4 w-4" />}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Language Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={analyticsData.languageBreakdown}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {analyticsData.languageBreakdown.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-lg">
                            <p className="text-sm font-medium text-card-foreground">
                              {payload[0].payload.language}: {payload[0].value} sessions
                            </p>
                          </div>
                        )
                      }
                      return null
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 flex justify-center gap-6">
              {analyticsData.languageBreakdown.map((item) => (
                <div key={item.language} className="flex items-center gap-2">
                  <div
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: item.fill }}
                  />
                  <span className="text-sm text-muted-foreground">
                    {item.language} ({item.value})
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Top Procedures</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart
                data={analyticsData.topProcedures}
                layout="vertical"
                margin={{ left: 0, right: 20 }}
              >
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="procedure"
                  axisLine={false}
                  tickLine={false}
                  width={80}
                  tick={{ fontSize: 12, fill: "var(--color-muted-foreground)" }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-lg">
                          <p className="text-sm font-medium text-card-foreground">
                            {payload[0].payload.procedure}: {payload[0].value} appointments
                          </p>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Bar dataKey="count" fill="var(--color-chart-1)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Busiest Days</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={analyticsData.busiestDays} margin={{ top: 10 }}>
                <XAxis
                  dataKey="day"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: "var(--color-muted-foreground)" }}
                />
                <YAxis hide />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-lg">
                          <p className="text-sm font-medium text-card-foreground">
                            {payload[0].payload.day}: {payload[0].value} sessions
                          </p>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Bar dataKey="sessions" fill="var(--color-chart-2)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Response Latency</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-[200px] flex-col items-center justify-center">
              <div className="flex items-center gap-3">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-success/10">
                  <Zap className="h-7 w-7 text-success" />
                </div>
                <div>
                  <p className="text-3xl font-bold text-foreground">
                    {analyticsData.avgResponseLatency}
                    <span className="ml-1 text-lg font-normal text-muted-foreground">ms</span>
                  </p>
                  <p className="text-sm text-muted-foreground">Avg. Response Time</p>
                </div>
              </div>
              <div className="mt-6 w-full max-w-xs">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>0ms</span>
                  <span>Target: 2000ms</span>
                  <span>3000ms</span>
                </div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-success"
                    style={{
                      width: `${Math.min((analyticsData.avgResponseLatency / 3000) * 100, 100)}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

interface MetricCardProps {
  title: string
  value: string
  icon: React.ReactNode
  subtitle?: string
  variant?: "default" | "success" | "destructive"
}

function MetricCard({ title, value, icon, subtitle, variant = "default" }: MetricCardProps) {
  const variantStyles = {
    default: "bg-secondary/50 text-muted-foreground",
    success: "bg-success/10 text-success",
    destructive: "bg-destructive/10 text-destructive",
  }

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">{title}</span>
          <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${variantStyles[variant]}`}>
            {icon}
          </div>
        </div>
        <p className="mt-2 text-2xl font-bold text-foreground">{value}</p>
        {subtitle && (
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  )
}

"use client"

import { useState } from "react"
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { mockAppointments, mockProviders, type Appointment, type Provider } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

type ViewMode = "day" | "week"

const timeSlots = Array.from({ length: 10 }, (_, i) => {
  const hour = 8 + i
  return `${hour > 12 ? hour - 12 : hour}:00 ${hour >= 12 ? "PM" : "AM"}`
})

const weekDays = ["Mon", "Tue", "Wed", "Thu", "Fri"]

export function AppointmentsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("day")
  const [currentDate, setCurrentDate] = useState(new Date(2026, 2, 14))
  const [selectedProviders, setSelectedProviders] = useState<string[]>(
    mockProviders.map((p) => p.id)
  )

  const toggleProvider = (providerId: string) => {
    setSelectedProviders((prev) =>
      prev.includes(providerId)
        ? prev.filter((id) => id !== providerId)
        : [...prev, providerId]
    )
  }

  const filteredAppointments = mockAppointments.filter((apt) =>
    selectedProviders.includes(apt.provider)
  )

  const navigateDate = (direction: "prev" | "next") => {
    const days = viewMode === "day" ? 1 : 7
    const newDate = new Date(currentDate)
    newDate.setDate(currentDate.getDate() + (direction === "next" ? days : -days))
    setCurrentDate(newDate)
  }

  const goToToday = () => setCurrentDate(new Date(2026, 2, 14))

  const formatDate = () => {
    if (viewMode === "day") {
      return currentDate.toLocaleDateString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    }
    const endDate = new Date(currentDate)
    endDate.setDate(currentDate.getDate() + 4)
    return `${currentDate.toLocaleDateString("en-US", { month: "short", day: "numeric" })} - ${endDate.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={() => navigateDate("prev")}
              >
                <ChevronLeft className="h-4 w-4" />
                <span className="sr-only">Previous</span>
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => navigateDate("next")}
              >
                <ChevronRight className="h-4 w-4" />
                <span className="sr-only">Next</span>
              </Button>
              <Button variant="outline" onClick={goToToday}>
                Today
              </Button>
            </div>
            <h2 className="text-lg font-semibold text-foreground">{formatDate()}</h2>
          </div>

          <div className="flex items-center gap-4">
            <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as ViewMode)}>
              <TabsList>
                <TabsTrigger value="day">Day</TabsTrigger>
                <TabsTrigger value="week">Week</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="border-t border-border">
            <div className="flex items-center gap-6 border-b border-border px-6 py-3">
              <span className="text-sm font-medium text-muted-foreground">Providers:</span>
              {mockProviders.map((provider) => (
                <label
                  key={provider.id}
                  className="flex cursor-pointer items-center gap-2"
                >
                  <Checkbox
                    checked={selectedProviders.includes(provider.id)}
                    onCheckedChange={() => toggleProvider(provider.id)}
                  />
                  <div className={cn("h-3 w-3 rounded-full", provider.color)} />
                  <span className="text-sm text-foreground">{provider.name}</span>
                </label>
              ))}
            </div>

            {viewMode === "day" ? (
              <DayView
                appointments={filteredAppointments}
                providers={mockProviders.filter((p) =>
                  selectedProviders.includes(p.id)
                )}
              />
            ) : (
              <WeekView
                appointments={filteredAppointments}
                providers={mockProviders.filter((p) =>
                  selectedProviders.includes(p.id)
                )}
              />
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

interface CalendarViewProps {
  appointments: Appointment[]
  providers: Provider[]
}

function DayView({ appointments, providers }: CalendarViewProps) {
  const getAppointmentsForProvider = (providerId: string) =>
    appointments.filter((apt) => apt.provider === providerId)

  const getAppointmentPosition = (apt: Appointment) => {
    const [startHour, startMinute] = apt.startTime.split(":").map(Number)
    const [endHour, endMinute] = apt.endTime.split(":").map(Number)
    
    const top = ((startHour - 8) * 60 + startMinute) * (48 / 60)
    const height = ((endHour - startHour) * 60 + (endMinute - startMinute)) * (48 / 60)
    
    return { top, height }
  }

  return (
    <div className="flex overflow-x-auto">
      <div className="w-20 flex-shrink-0 border-r border-border">
        <div className="h-12 border-b border-border" />
        {timeSlots.map((time) => (
          <div
            key={time}
            className="flex h-12 items-start justify-end border-b border-border pr-3 pt-0 text-xs text-muted-foreground"
          >
            <span className="-translate-y-2">{time}</span>
          </div>
        ))}
      </div>

      <div className="flex flex-1">
        {providers.map((provider) => (
          <div key={provider.id} className="flex-1 min-w-[180px] border-r border-border last:border-r-0">
            <div className="flex h-12 items-center justify-center border-b border-border bg-secondary/30">
              <div className={cn("mr-2 h-3 w-3 rounded-full", provider.color)} />
              <span className="text-sm font-medium text-foreground">{provider.name}</span>
            </div>
            <div className="relative">
              {timeSlots.map((_, i) => (
                <div key={i} className="h-12 border-b border-border" />
              ))}
              {getAppointmentsForProvider(provider.id).map((apt) => {
                const { top, height } = getAppointmentPosition(apt)
                return (
                  <div
                    key={apt.id}
                    className={cn(
                      "absolute left-1 right-1 rounded-md px-2 py-1 text-xs",
                      apt.color,
                      apt.status === "cancelled" && "opacity-50 line-through"
                    )}
                    style={{ top: `${top}px`, height: `${height}px` }}
                  >
                    <div className="font-medium text-white truncate">{apt.patientName}</div>
                    <div className="text-white/80 truncate">{apt.procedure}</div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function WeekView({ appointments, providers }: CalendarViewProps) {
  const getAppointmentPosition = (apt: Appointment) => {
    const [startHour, startMinute] = apt.startTime.split(":").map(Number)
    const [endHour, endMinute] = apt.endTime.split(":").map(Number)
    
    const top = ((startHour - 8) * 60 + startMinute) * (48 / 60)
    const height = ((endHour - startHour) * 60 + (endMinute - startMinute)) * (48 / 60)
    
    return { top, height }
  }

  return (
    <div className="flex overflow-x-auto">
      <div className="w-20 flex-shrink-0 border-r border-border">
        <div className="h-12 border-b border-border" />
        {timeSlots.map((time) => (
          <div
            key={time}
            className="flex h-12 items-start justify-end border-b border-border pr-3 pt-0 text-xs text-muted-foreground"
          >
            <span className="-translate-y-2">{time}</span>
          </div>
        ))}
      </div>

      <div className="flex flex-1">
        {weekDays.map((day, dayIndex) => (
          <div key={day} className="flex-1 min-w-[150px] border-r border-border last:border-r-0">
            <div className="flex h-12 items-center justify-center border-b border-border bg-secondary/30">
              <span className="text-sm font-medium text-foreground">{day}</span>
            </div>
            <div className="relative">
              {timeSlots.map((_, i) => (
                <div key={i} className="h-12 border-b border-border" />
              ))}
              {appointments
                .filter((_, i) => i % 5 === dayIndex)
                .map((apt) => {
                  const { top, height } = getAppointmentPosition(apt)
                  return (
                    <div
                      key={apt.id}
                      className={cn(
                        "absolute left-1 right-1 rounded-md px-2 py-1 text-xs",
                        apt.color,
                        apt.status === "cancelled" && "opacity-50 line-through"
                      )}
                      style={{ top: `${top}px`, height: `${height}px` }}
                    >
                      <div className="font-medium text-white truncate">{apt.patientName}</div>
                      <div className="text-white/80 truncate">{apt.procedure}</div>
                    </div>
                  )
                })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

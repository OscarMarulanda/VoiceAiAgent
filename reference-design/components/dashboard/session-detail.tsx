"use client"

import { X, Phone, MessageSquare, Clock, Check, XIcon } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import type { Session } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

interface SessionDetailProps {
  session: Session
  onClose: () => void
  mobile?: boolean
}

export function SessionDetail({ session, onClose, mobile }: SessionDetailProps) {
  const content = (
    <div className="flex h-full flex-col">
      <SessionHeader session={session} onClose={onClose} showClose={!mobile} />
      <div className="flex flex-1 flex-col gap-4 overflow-hidden p-4">
        <Transcript messages={session.messages} />
        <Metrics session={session} />
      </div>
    </div>
  )

  if (mobile) {
    return (
      <Sheet open onOpenChange={onClose}>
        <SheetContent side="right" className="w-full p-0 sm:max-w-lg">
          <SheetHeader className="sr-only">
            <SheetTitle>Session Details</SheetTitle>
          </SheetHeader>
          {content}
        </SheetContent>
      </Sheet>
    )
  }

  return (
    <Card className="flex h-full flex-col overflow-hidden">
      {content}
    </Card>
  )
}

function SessionHeader({ session, onClose, showClose }: { session: Session; onClose: () => void; showClose: boolean }) {
  const startTime = new Date(session.startTime).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  })

  return (
    <div className="flex items-start justify-between border-b border-border p-4">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary">
          {session.channel === "phone" ? (
            <Phone className="h-5 w-5 text-muted-foreground" />
          ) : (
            <MessageSquare className="h-5 w-5 text-muted-foreground" />
          )}
        </div>
        <div>
          <h3 className="font-semibold text-foreground">
            {session.channel === "phone" ? "Voice Call" : "Chat Session"}
          </h3>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{startTime}</span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {session.duration}
            </span>
            {session.callerNumber && (
              <>
                <span>•</span>
                <span>{session.callerNumber}</span>
              </>
            )}
          </div>
        </div>
      </div>
      {showClose && (
        <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </Button>
      )}
    </div>
  )
}

function Transcript({ messages }: { messages: Session["messages"] }) {
  return (
    <div className="flex-1 overflow-hidden rounded-lg border border-border bg-secondary/30">
      <div className="border-b border-border px-4 py-2">
        <h4 className="text-sm font-medium text-foreground">Transcript</h4>
      </div>
      <ScrollArea className="h-[300px] p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex flex-col",
                message.role === "user" ? "items-end" : "items-start"
              )}
            >
              <div
                className={cn(
                  "max-w-[85%] rounded-2xl px-4 py-2.5",
                  message.role === "user"
                    ? "bg-primary text-primary-foreground rounded-br-md"
                    : "bg-muted text-foreground rounded-bl-md"
                )}
              >
                <p className="text-sm">{message.content}</p>
              </div>
              <span className="mt-1 text-[10px] text-muted-foreground">
                {message.timestamp}
              </span>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

function Metrics({ session }: { session: Session }) {
  const { metrics } = session

  return (
    <div className="rounded-lg border border-border bg-secondary/30 p-4">
      <h4 className="mb-3 text-sm font-medium text-foreground">Metrics</h4>
      <div className="grid grid-cols-2 gap-4">
        <MetricItem label="Total Turns" value={metrics.totalTurns.toString()} />
        <MetricItem 
          label="Avg Response Time" 
          value={`${metrics.avgResponseTime}ms`} 
        />
        <div className="col-span-2">
          <span className="text-xs text-muted-foreground">Tools Used</span>
          <div className="mt-1 flex flex-wrap gap-1">
            {metrics.toolsUsed.length > 0 ? (
              metrics.toolsUsed.map((tool) => (
                <Badge key={tool} variant="secondary" className="text-xs font-mono">
                  {tool}
                </Badge>
              ))
            ) : (
              <span className="text-xs text-muted-foreground">None</span>
            )}
          </div>
        </div>
        <div className="col-span-2 flex items-center justify-between rounded-lg bg-card p-3">
          <span className="text-sm text-foreground">Appointment Booked</span>
          {metrics.appointmentBooked ? (
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-success">
              <Check className="h-4 w-4 text-success-foreground" />
            </div>
          ) : (
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-muted">
              <XIcon className="h-4 w-4 text-muted-foreground" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs text-muted-foreground">{label}</span>
      <p className="text-lg font-semibold text-foreground">{value}</p>
    </div>
  )
}

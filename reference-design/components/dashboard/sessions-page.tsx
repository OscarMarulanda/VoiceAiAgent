"use client"

import { useState } from "react"
import { Phone, MessageSquare, Clock, ChevronRight } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { mockSessions, type Session } from "@/lib/mock-data"
import { SessionDetail } from "./session-detail"
import { cn } from "@/lib/utils"

export function SessionsPage() {
  const [selectedSession, setSelectedSession] = useState<Session | null>(null)

  return (
    <div className="flex h-full gap-6">
      <div className={cn("flex-1 transition-all", selectedSession ? "lg:flex-[2]" : "")}>
        <Card className="h-full">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg font-semibold">Recent Sessions</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {mockSessions.map((session) => (
                <SessionRow 
                  key={session.id} 
                  session={session} 
                  isSelected={selectedSession?.id === session.id}
                  onClick={() => setSelectedSession(session)}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
      
      {selectedSession && (
        <div className="hidden flex-1 lg:block lg:flex-[1.5]">
          <SessionDetail 
            session={selectedSession} 
            onClose={() => setSelectedSession(null)} 
          />
        </div>
      )}

      {selectedSession && (
        <div className="lg:hidden">
          <SessionDetail 
            session={selectedSession} 
            onClose={() => setSelectedSession(null)} 
            mobile
          />
        </div>
      )}
    </div>
  )
}

interface SessionRowProps {
  session: Session
  isSelected: boolean
  onClick: () => void
}

function SessionRow({ session, isSelected, onClick }: SessionRowProps) {
  const isActive = session.status === "active"
  const startTime = new Date(session.startTime).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  })

  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-4 px-6 py-4 text-left transition-colors hover:bg-muted/50",
        isSelected && "bg-muted"
      )}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary">
        {session.channel === "phone" ? (
          <Phone className="h-5 w-5 text-muted-foreground" />
        ) : (
          <MessageSquare className="h-5 w-5 text-muted-foreground" />
        )}
      </div>
      
      <div className="flex flex-1 items-center gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className={cn(
              "h-2 w-2 rounded-full",
              isActive ? "bg-success animate-pulse" : "bg-muted-foreground"
            )} />
            <span className="text-sm font-medium text-foreground">
              {session.channel === "phone" ? "Voice Call" : "Chat Session"}
            </span>
          </div>
          <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
            <span>{startTime}</span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {session.duration}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="text-xs">
            {session.language}
          </Badge>
          
          <span className="text-xs text-muted-foreground">
            {session.messageCount} msgs
          </span>
          
          <OutcomeBadge outcome={session.outcome} />
          
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
    </button>
  )
}

function OutcomeBadge({ outcome }: { outcome: Session["outcome"] }) {
  const variants = {
    completed: "bg-success/10 text-success border-success/20",
    abandoned: "bg-warning/10 text-warning-foreground border-warning/20",
    transferred: "bg-primary/10 text-primary border-primary/20",
  }

  return (
    <Badge 
      variant="outline" 
      className={cn("text-xs capitalize", variants[outcome])}
    >
      {outcome}
    </Badge>
  )
}

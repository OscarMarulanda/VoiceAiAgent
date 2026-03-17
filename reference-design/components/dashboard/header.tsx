"use client"

import { Badge } from "@/components/ui/badge"
import { AlertTriangle } from "lucide-react"

export function Header() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
      <h1 className="text-lg font-semibold text-card-foreground">
        Bright Smile Dental
      </h1>
      
      <Badge 
        variant="outline" 
        className="gap-1.5 border-warning bg-warning/10 text-warning-foreground"
      >
        <AlertTriangle className="h-3.5 w-3.5 text-warning" />
        Demo — Not HIPAA Compliant
      </Badge>
    </header>
  )
}

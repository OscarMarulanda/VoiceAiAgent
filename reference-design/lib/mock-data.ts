export type SessionStatus = "active" | "ended"
export type SessionChannel = "phone" | "chat"
export type SessionOutcome = "completed" | "abandoned" | "transferred"
export type Language = "EN" | "ES"

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
}

export interface Session {
  id: string
  channel: SessionChannel
  status: SessionStatus
  startTime: string
  duration: string
  language: Language
  messageCount: number
  outcome: SessionOutcome
  callerNumber?: string
  messages: Message[]
  metrics: {
    totalTurns: number
    avgResponseTime: number
    toolsUsed: string[]
    appointmentBooked: boolean
  }
}

export interface Appointment {
  id: string
  patientName: string
  procedure: string
  provider: string
  startTime: string
  endTime: string
  status: "confirmed" | "cancelled" | "pending"
  color: string
}

export interface Provider {
  id: string
  name: string
  color: string
}

// Mock sessions data
export const mockSessions: Session[] = [
  {
    id: "sess_001",
    channel: "phone",
    status: "active",
    startTime: "2026-03-14T09:15:00",
    duration: "5:23",
    language: "EN",
    messageCount: 12,
    outcome: "completed",
    callerNumber: "+1 (555) 123-4567",
    messages: [
      { id: "msg_1", role: "assistant", content: "Good morning! Thank you for calling Bright Smile Dental. How may I help you today?", timestamp: "09:15:00" },
      { id: "msg_2", role: "user", content: "Hi, I'd like to schedule a cleaning appointment.", timestamp: "09:15:12" },
      { id: "msg_3", role: "assistant", content: "I'd be happy to help you schedule a cleaning. Could you please provide your name?", timestamp: "09:15:14" },
      { id: "msg_4", role: "user", content: "Yes, my name is Sarah Johnson.", timestamp: "09:15:28" },
      { id: "msg_5", role: "assistant", content: "Thank you, Sarah. I found your record. When would you like to come in? We have availability this week on Wednesday at 2pm or Friday at 10am.", timestamp: "09:15:31" },
      { id: "msg_6", role: "user", content: "Friday at 10am works great!", timestamp: "09:15:45" },
      { id: "msg_7", role: "assistant", content: "I've scheduled your cleaning appointment for Friday, March 20th at 10:00 AM with Dr. Martinez. You'll receive a confirmation text shortly. Is there anything else I can help you with?", timestamp: "09:15:48" },
      { id: "msg_8", role: "user", content: "No, that's all. Thank you!", timestamp: "09:16:02" },
    ],
    metrics: {
      totalTurns: 8,
      avgResponseTime: 1850,
      toolsUsed: ["lookup_patient", "check_availability", "book_appointment", "send_confirmation"],
      appointmentBooked: true,
    },
  },
  {
    id: "sess_002",
    channel: "chat",
    status: "ended",
    startTime: "2026-03-14T08:45:00",
    duration: "3:12",
    language: "ES",
    messageCount: 8,
    outcome: "completed",
    messages: [
      { id: "msg_1", role: "user", content: "Hola, necesito cancelar mi cita", timestamp: "08:45:00" },
      { id: "msg_2", role: "assistant", content: "¡Hola! Estaré encantado de ayudarle a cancelar su cita. ¿Podría darme su nombre?", timestamp: "08:45:02" },
      { id: "msg_3", role: "user", content: "Carlos Rivera", timestamp: "08:45:15" },
      { id: "msg_4", role: "assistant", content: "Gracias, Carlos. Veo que tiene una cita programada para mañana a las 3pm. ¿Desea cancelarla o reprogramarla?", timestamp: "08:45:18" },
      { id: "msg_5", role: "user", content: "Cancelar por favor", timestamp: "08:45:30" },
      { id: "msg_6", role: "assistant", content: "Su cita ha sido cancelada. ¿Hay algo más en lo que pueda ayudarle?", timestamp: "08:45:33" },
    ],
    metrics: {
      totalTurns: 6,
      avgResponseTime: 2100,
      toolsUsed: ["lookup_patient", "cancel_appointment"],
      appointmentBooked: false,
    },
  },
  {
    id: "sess_003",
    channel: "phone",
    status: "ended",
    startTime: "2026-03-14T08:20:00",
    duration: "1:45",
    language: "EN",
    messageCount: 4,
    outcome: "abandoned",
    callerNumber: "+1 (555) 987-6543",
    messages: [
      { id: "msg_1", role: "assistant", content: "Good morning! Thank you for calling Bright Smile Dental. How may I help you today?", timestamp: "08:20:00" },
      { id: "msg_2", role: "user", content: "Hello? Is this the dentist?", timestamp: "08:20:15" },
      { id: "msg_3", role: "assistant", content: "Yes, this is Bright Smile Dental. I'm the AI assistant. How can I assist you?", timestamp: "08:20:17" },
    ],
    metrics: {
      totalTurns: 3,
      avgResponseTime: 1500,
      toolsUsed: [],
      appointmentBooked: false,
    },
  },
  {
    id: "sess_004",
    channel: "chat",
    status: "ended",
    startTime: "2026-03-14T07:55:00",
    duration: "4:30",
    language: "EN",
    messageCount: 10,
    outcome: "completed",
    messages: [
      { id: "msg_1", role: "user", content: "What are your hours?", timestamp: "07:55:00" },
      { id: "msg_2", role: "assistant", content: "We're open Monday through Friday from 8 AM to 5 PM, and Saturdays from 9 AM to 2 PM. Would you like to schedule an appointment?", timestamp: "07:55:02" },
      { id: "msg_3", role: "user", content: "Do you accept Delta Dental insurance?", timestamp: "07:55:20" },
      { id: "msg_4", role: "assistant", content: "Yes, we accept Delta Dental along with most major insurance providers. I can verify your specific coverage when we schedule your appointment. Would you like to book now?", timestamp: "07:55:23" },
    ],
    metrics: {
      totalTurns: 10,
      avgResponseTime: 1650,
      toolsUsed: ["check_insurance", "get_hours"],
      appointmentBooked: false,
    },
  },
  {
    id: "sess_005",
    channel: "phone",
    status: "active",
    startTime: "2026-03-14T09:30:00",
    duration: "2:15",
    language: "EN",
    messageCount: 6,
    outcome: "completed",
    callerNumber: "+1 (555) 456-7890",
    messages: [
      { id: "msg_1", role: "assistant", content: "Good morning! Thank you for calling Bright Smile Dental.", timestamp: "09:30:00" },
      { id: "msg_2", role: "user", content: "I have a toothache and need to see someone today.", timestamp: "09:30:08" },
      { id: "msg_3", role: "assistant", content: "I'm sorry to hear that. Let me check our emergency availability for today.", timestamp: "09:30:10" },
    ],
    metrics: {
      totalTurns: 6,
      avgResponseTime: 1400,
      toolsUsed: ["check_emergency_slots"],
      appointmentBooked: false,
    },
  },
]

// Mock providers
export const mockProviders: Provider[] = [
  { id: "dr_martinez", name: "Dr. Martinez", color: "bg-chart-1" },
  { id: "dr_chen", name: "Dr. Chen", color: "bg-chart-2" },
  { id: "dr_patel", name: "Dr. Patel", color: "bg-chart-3" },
  { id: "dr_johnson", name: "Dr. Johnson", color: "bg-chart-5" },
]

// Mock appointments
export const mockAppointments: Appointment[] = [
  { id: "apt_1", patientName: "Sarah Johnson", procedure: "Cleaning", provider: "dr_martinez", startTime: "10:00", endTime: "10:30", status: "confirmed", color: "bg-chart-1" },
  { id: "apt_2", patientName: "Michael Brown", procedure: "Root Canal", provider: "dr_chen", startTime: "09:00", endTime: "10:30", status: "confirmed", color: "bg-chart-2" },
  { id: "apt_3", patientName: "Emily Davis", procedure: "Checkup", provider: "dr_martinez", startTime: "11:00", endTime: "11:30", status: "confirmed", color: "bg-chart-1" },
  { id: "apt_4", patientName: "James Wilson", procedure: "Filling", provider: "dr_patel", startTime: "09:30", endTime: "10:00", status: "cancelled", color: "bg-chart-3" },
  { id: "apt_5", patientName: "Lisa Anderson", procedure: "Crown Fitting", provider: "dr_chen", startTime: "11:00", endTime: "12:00", status: "confirmed", color: "bg-chart-2" },
  { id: "apt_6", patientName: "Robert Taylor", procedure: "Extraction", provider: "dr_johnson", startTime: "14:00", endTime: "14:45", status: "confirmed", color: "bg-chart-5" },
  { id: "apt_7", patientName: "Jennifer Martinez", procedure: "Cleaning", provider: "dr_martinez", startTime: "14:00", endTime: "14:30", status: "confirmed", color: "bg-chart-1" },
  { id: "apt_8", patientName: "David Lee", procedure: "Whitening", provider: "dr_patel", startTime: "13:00", endTime: "14:00", status: "pending", color: "bg-chart-3" },
  { id: "apt_9", patientName: "Amanda Clark", procedure: "Consultation", provider: "dr_johnson", startTime: "10:00", endTime: "10:30", status: "confirmed", color: "bg-chart-5" },
  { id: "apt_10", patientName: "Chris Evans", procedure: "Deep Cleaning", provider: "dr_chen", startTime: "14:00", endTime: "15:00", status: "confirmed", color: "bg-chart-2" },
]

// Analytics data
export const analyticsData = {
  totalSessionsToday: 47,
  voiceSessions: 28,
  chatSessions: 19,
  appointmentsBookedToday: 12,
  cancelledToday: 3,
  avgSessionDuration: "3:42",
  languageBreakdown: [
    { language: "English", value: 38, fill: "var(--color-chart-1)" },
    { language: "Spanish", value: 9, fill: "var(--color-chart-2)" },
  ],
  topProcedures: [
    { procedure: "Cleaning", count: 18 },
    { procedure: "Checkup", count: 14 },
    { procedure: "Filling", count: 8 },
    { procedure: "Root Canal", count: 4 },
    { procedure: "Whitening", count: 3 },
  ],
  busiestDays: [
    { day: "Mon", sessions: 52 },
    { day: "Tue", sessions: 48 },
    { day: "Wed", sessions: 61 },
    { day: "Thu", sessions: 45 },
    { day: "Fri", sessions: 58 },
  ],
  avgResponseLatency: 1720,
}

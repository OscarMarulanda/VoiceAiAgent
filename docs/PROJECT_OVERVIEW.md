# Project Overview

## AI Voice & Chat Agent for Healthcare Practices

### What Is This?

An AI-powered assistant that handles patient phone calls and website chat for healthcare practices (dental, medical, chiropractic, optometry). It can book appointments, answer frequently asked questions, handle rescheduling/cancellation, and respond in English or Spanish.

This is a portfolio/demo project targeting the "AI Agent Builder" role at MacPractice (owned by Valsoft Corporation). MacPractice makes practice management software (scheduling, billing, EHR) for Mac/iOS. The goal is a **working MVP** that proves the concept with a live phone number and embeddable chat widget.

### Who Is It For?

- **Patients** — Call a phone number or use a website chat widget to interact with the AI agent
- **Practice staff** — View an admin dashboard showing conversations and bookings
- **MacPractice/Valsoft evaluators** — Experience the system live to evaluate capabilities

### What Can the Agent Do?

1. **Book appointments** — Check provider availability, detect conflicts, confirm bookings
2. **Answer FAQs** — Practice hours, accepted insurance, provider info, location/directions
3. **Reschedule appointments** — Look up existing appointments and move them
4. **Cancel appointments** — Look up and cancel with confirmation
5. **Bilingual support** — Respond in English or Spanish based on caller preference

### Two Interfaces, One Brain

The same AI agent logic serves both channels:

1. **Voice (Phone)** — Patient calls a Twilio number → Deepgram transcribes speech → Claude processes → ElevenLabs generates voice response → Twilio plays it back
2. **Chat (Web Widget)** — Patient types in an embeddable widget on a WordPress site → FastAPI backend → Claude processes → text response returned

### What This Is NOT

- Not a production HIPAA-compliant system (demo only, mock data)
- Not a replacement for full practice management software
- Not handling real patient data or real billing

### Success Criteria

- [ ] A live phone number anyone can call and have a natural conversation with the AI
- [ ] A chat widget that can be embedded on any website
- [ ] Appointment booking that correctly detects scheduling conflicts
- [ ] FAQ responses that are accurate to the mock practice data
- [ ] Bilingual (English/Spanish) support
- [ ] Admin dashboard showing conversations and bookings
- [ ] Clean, documented codebase that demonstrates production-quality thinking
- [ ] Deployed and accessible for live demo

### Links & Context

- [MacPractice Software](https://www.macpractice.com/macpractice-software/)
- [MacPractice Services & Integrations](https://www.macpractice.com/services-and-integrations/)
- [Valsoft Corporation](https://www.valsoftcorp.com/)

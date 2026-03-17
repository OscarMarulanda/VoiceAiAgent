# Chat Widget

Documentation for the embeddable chat widget that provides the same AI agent experience on websites.

---

## Overview

A lightweight, self-contained JavaScript widget that can be embedded on any website (WordPress or otherwise) with a single `<script>` tag. It connects to the same FastAPI backend via WebSocket and uses the same Agent Core as the voice pipeline.

## Embedding

### Basic Embedding
```html
<script
  src="https://your-server.com/widget/widget.js"
  data-server="https://your-server.com"
  data-practice="Sunshine Dental"
></script>
```

### Configuration Options
```html
<script
  src="https://your-server.com/widget/widget.js"
  data-server="https://your-server.com"
  data-practice="Sunshine Dental"
  data-primary-color="#2563eb"
  data-position="bottom-right"
  data-greeting="Hi! How can I help you today?"
  data-language="en"
></script>
```

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-server` | (required) | Backend server URL |
| `data-practice` | "Our Practice" | Practice name shown in widget header |
| `data-primary-color` | "#2563eb" | Primary theme color |
| `data-position` | "bottom-right" | Widget position: bottom-right, bottom-left |
| `data-greeting` | "Hello! How can I help you today?" | Initial greeting message |
| `data-language` | "en" | Default language (en/es), auto-detected from conversation |

### WordPress Integration
For WordPress, the script tag goes in:
- Theme's `footer.php` (before `</body>`)
- Or via a "Custom HTML" widget in the footer area
- Or via a simple custom plugin that enqueues the script
- Or via WordPress Customizer → Additional Scripts

---

## Widget Architecture

```
┌─────────────────────────────────────┐
│  Widget Container (Shadow DOM)       │
│                                     │
│  ┌─ Header ──────────────────────┐  │
│  │  Practice Name     [—] [✕]    │  │
│  └───────────────────────────────┘  │
│  ┌─ Messages Area ───────────────┐  │
│  │  🤖 Hello! How can I help?    │  │
│  │                               │  │
│  │  👤 I'd like to book an       │  │
│  │     appointment               │  │
│  │                               │  │
│  │  🤖 I'd be happy to help!     │  │
│  │     Which provider...         │  │
│  │                               │  │
│  │  ···  (typing indicator)      │  │
│  └───────────────────────────────┘  │
│  ┌─ Input Area ──────────────────┐  │
│  │  [Type your message...] [Send]│  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘

         ┌──── Floating Button ────┐
         │   💬  (click to open)   │
         └─────────────────────────┘
```

## Widget Features

- **Shadow DOM** — Styles are encapsulated, won't conflict with host page CSS
- **Responsive** — Works on desktop and mobile
- **Auto-reconnect** — If WebSocket drops, automatically reconnects
- **Typing indicator** — Shows while agent is processing
- **Message history** — Persisted in sessionStorage (survives page navigation within session)
- **Minimize/close** — Can be minimized to the floating button
- **Draggable launcher** — Click to open, drag to reposition the floating button
- **Keyboard support** — Enter to send, Escape to minimize

## WebSocket Protocol

### Connection
```
WS: wss://your-server.com/chat/ws?practice_id=default
```

### Client → Server Messages
```json
{
  "type": "message",
  "content": "I'd like to book an appointment",
  "session_id": "client-generated-uuid"
}
```

```json
{
  "type": "ping"
}
```

### Server → Client Messages
```json
{
  "type": "message",
  "content": "I'd be happy to help you book an appointment! ...",
  "session_id": "server-session-uuid"
}
```

```json
{
  "type": "typing",
  "status": true
}
```

```json
{
  "type": "welcome",
  "content": "Hello! How can I help you today?",
  "session_id": "server-session-uuid"
}
```

```json
{
  "type": "error",
  "content": "I'm having trouble connecting. Please try again in a moment."
}
```

```json
{
  "type": "pong"
}
```

---

## Styling

The widget uses CSS embedded as a template literal inside the JS, injected into the Shadow DOM. Key design decisions:

- Clean, modern healthcare aesthetic
- Accessible: minimum 4.5:1 contrast ratio, keyboard navigable
- Customizable via `data-primary-color`
- Max height: 500px on desktop, 100vh on mobile
- Width: 380px on desktop, 100vw on mobile
- Smooth animations for open/close
- Scrollable message area with auto-scroll to latest message
- Lightweight markdown rendering for agent messages (bold, lists, line breaks)

### Shadow DOM CSS Isolation

Shadow DOM prevents external stylesheets from *matching* elements inside the shadow tree, but it does **not** block CSS inheritance through the host element. If a host page sets `* { font-family: "Comic Sans MS" !important; }`, the host element inherits that, and shadow children inherit from the host.

**Solution:** Two-layer reset inside the shadow:
1. `.widget-root { all: initial; display: contents; }` — breaks the inheritance chain completely
2. `* { font-family: ... !important; }` inside the shadow — explicitly sets the font on every element

This was verified against a test page (`test-wordpress.html`) with aggressive WordPress-like CSS: `!important` on `*` selectors, forced fonts, color overrides, position hijacking, animation kills, flexbox overrides, and z-index wars.

---

## Security Considerations

- Widget connects via WSS (secure WebSocket)
- No patient data stored in localStorage (only sessionStorage, cleared on browser close)
- CORS configured on backend to allow widget domains
- No authentication required for chat (same as calling a phone number — anyone can initiate)
- Rate limiting on WebSocket connections to prevent abuse

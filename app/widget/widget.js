/**
 * AI Chat Widget — Embeddable chat agent for healthcare practices.
 *
 * Usage:
 *   <script src="/widget/widget.js"
 *     data-server="https://your-server.com"
 *     data-practice="Sunshine Dental"
 *   ></script>
 *
 * See docs/CHAT_WIDGET.md for full configuration options.
 */
(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Config — read from script tag data attributes
  // ---------------------------------------------------------------------------
  const scriptTag = document.currentScript;
  const CONFIG = {
    server: scriptTag.getAttribute("data-server") || "",
    practice: scriptTag.getAttribute("data-practice") || "Our Practice",
    primaryColor: scriptTag.getAttribute("data-primary-color") || "#2563eb",
    position: scriptTag.getAttribute("data-position") || "bottom-right",
    bottomOffset: scriptTag.getAttribute("data-bottom") || "20",
    greeting:
      scriptTag.getAttribute("data-greeting") ||
      "Hello! How can I help you today?",
  };

  // Derive WebSocket URL from server URL
  const wsProtocol = CONFIG.server.startsWith("https") ? "wss" : "ws";
  const wsBase = CONFIG.server.replace(/^https?/, wsProtocol);
  const WS_URL = `${wsBase}/chat/ws`;

  // Reconnect settings
  const RECONNECT_BASE_MS = 1000;
  const RECONNECT_MAX_MS = 30000;
  const RECONNECT_MAX_ATTEMPTS = 10;

  // Ping interval
  const PING_INTERVAL_MS = 30000;

  // Session storage key
  const STORAGE_KEY = "voiceagent_chat";

  // ---------------------------------------------------------------------------
  // CSS (injected into Shadow DOM)
  // ---------------------------------------------------------------------------
  const CSS = `
    :host {
      --primary: ${CONFIG.primaryColor};
      --primary-dark: color-mix(in srgb, ${CONFIG.primaryColor} 80%, black);
      --primary-light: color-mix(in srgb, ${CONFIG.primaryColor} 15%, white);
      --text: #1f2937;
      --text-light: #6b7280;
      --bg: #ffffff;
      --bg-secondary: #f9fafb;
      --border: #e5e7eb;
      --radius: 12px;
      --shadow: 0 4px 24px rgba(0, 0, 0, 0.12);

      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        Helvetica, Arial, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      color: var(--text);
    }

    .widget-root {
      all: initial;
      display: contents;
    }

    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        Helvetica, Arial, sans-serif !important;
      font-size: inherit;
      line-height: 1.5;
      color: inherit;
    }

    /* -- Floating button -- */
    .launcher {
      position: fixed;
      ${CONFIG.position === "bottom-left" ? "left" : "right"}: 20px;
      bottom: ${CONFIG.bottomOffset}px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: var(--primary);
      color: white;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: var(--shadow);
      transition: transform 0.2s, background 0.2s;
      z-index: 999999;
    }
    .launcher:hover {
      background: var(--primary-dark);
    }
    .launcher:not(.dragging):hover {
      transform: scale(1.08);
    }
    .launcher.dragging {
      cursor: grabbing;
      transition: none;
    }
    .launcher svg {
      width: 26px;
      height: 26px;
      fill: currentColor;
    }
    .launcher.hidden { display: none; }

    /* -- Chat window -- */
    .chat-window {
      position: fixed;
      ${CONFIG.position === "bottom-left" ? "left" : "right"}: 20px;
      bottom: ${CONFIG.bottomOffset}px;
      width: 380px;
      max-height: 500px;
      display: flex;
      flex-direction: column;
      background: var(--bg);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
      z-index: 999999;
      opacity: 0;
      transform: translateY(16px) scale(0.96);
      pointer-events: none;
      transition: opacity 0.25s ease, transform 0.25s ease;
    }
    .chat-window.open {
      opacity: 1;
      transform: translateY(0) scale(1);
      pointer-events: auto;
    }

    /* -- Header -- */
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 16px;
      background: var(--primary);
      color: white;
      flex-shrink: 0;
    }
    .header-title {
      font-weight: 600;
      font-size: 15px;
    }
    .header-actions {
      display: flex;
      gap: 4px;
    }
    .header-btn {
      background: none;
      border: none;
      color: white;
      cursor: pointer;
      width: 28px;
      height: 28px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      opacity: 0.8;
      transition: opacity 0.15s, background 0.15s;
    }
    .header-btn:hover {
      opacity: 1;
      background: rgba(255,255,255,0.15);
    }

    /* -- Messages area -- */
    .messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-height: 200px;
      max-height: 340px;
      background: var(--bg-secondary);
    }

    .message {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 16px;
      word-wrap: break-word;
      font-size: 14px;
      line-height: 1.5;
    }
    .message.user {
      white-space: pre-wrap;
    }
    .message ul {
      margin: 4px 0;
      padding-left: 20px;
    }
    .message li {
      margin: 2px 0;
    }
    .message strong {
      font-weight: 600;
    }
    .message.agent {
      align-self: flex-start;
      background: var(--bg);
      border: 1px solid var(--border);
      border-bottom-left-radius: 4px;
    }
    .message.user {
      align-self: flex-end;
      background: var(--primary);
      color: white;
      border-bottom-right-radius: 4px;
    }

    /* -- Typing indicator -- */
    .typing {
      align-self: flex-start;
      display: none;
      align-items: center;
      gap: 4px;
      padding: 10px 14px;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      border-bottom-left-radius: 4px;
    }
    .typing.visible { display: flex; }
    .typing-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--text-light);
      animation: bounce 1.4s infinite ease-in-out;
    }
    .typing-dot:nth-child(2) { animation-delay: 0.16s; }
    .typing-dot:nth-child(3) { animation-delay: 0.32s; }
    @keyframes bounce {
      0%, 80%, 100% { transform: translateY(0); }
      40% { transform: translateY(-5px); }
    }

    /* -- Connection status -- */
    .status-bar {
      display: none;
      padding: 6px 16px;
      font-size: 12px;
      text-align: center;
      background: #fef3c7;
      color: #92400e;
      flex-shrink: 0;
    }
    .status-bar.visible { display: block; }
    .status-bar.error {
      background: #fee2e2;
      color: #991b1b;
    }
    .status-bar button {
      background: none;
      border: none;
      color: inherit;
      text-decoration: underline;
      cursor: pointer;
      font-size: 12px;
    }

    /* -- Input area -- */
    .input-area {
      display: flex;
      align-items: center;
      padding: 12px;
      border-top: 1px solid var(--border);
      background: var(--bg);
      flex-shrink: 0;
    }
    .input-area input {
      flex: 1;
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 8px 14px;
      font-size: 14px;
      outline: none;
      font-family: inherit;
      transition: border-color 0.15s;
    }
    .input-area input:focus {
      border-color: var(--primary);
    }
    .input-area input::placeholder {
      color: var(--text-light);
    }
    .send-btn {
      margin-left: 8px;
      width: 36px;
      height: 36px;
      border-radius: 50%;
      border: none;
      background: var(--primary);
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s, transform 0.15s;
      flex-shrink: 0;
    }
    .send-btn:hover {
      background: var(--primary-dark);
    }
    .send-btn:active {
      transform: scale(0.92);
    }
    .send-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }
    .send-btn svg {
      width: 18px;
      height: 18px;
      fill: currentColor;
    }

    /* -- Mobile responsive -- */
    @media (max-width: 480px) {
      .chat-window {
        width: 100vw;
        height: 100vh;
        max-height: 100vh;
        bottom: 0;
        right: 0;
        left: 0;
        border-radius: 0;
      }
      .messages {
        max-height: none;
        flex: 1;
      }
      .launcher {
        bottom: 16px;
        ${CONFIG.position === "bottom-left" ? "left" : "right"}: 16px;
      }
    }
  `;

  // ---------------------------------------------------------------------------
  // SVG icons
  // ---------------------------------------------------------------------------
  const ICON_CHAT = `<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>`;
  const ICON_SEND = `<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>`;
  const ICON_CLOSE = `<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>`;
  const ICON_MINIMIZE = `<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M6 19h12v-2H6z"/></svg>`;
  const ICON_RESET = `<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.65 6.35A7.96 7.96 0 0 0 12 4C7.58 4 4.01 7.58 4.01 12S7.58 20 12 20c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>`;

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let ws = null;
  let sessionId = null;
  let isOpen = false;
  let reconnectAttempts = 0;
  let reconnectTimer = null;
  let pingInterval = null;
  let messages = []; // {role: "agent"|"user", content: string}

  // DOM refs (set after build)
  let els = {};

  // ---------------------------------------------------------------------------
  // Session storage
  // ---------------------------------------------------------------------------
  function saveState() {
    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ sessionId, messages })
      );
    } catch (_) {}
  }

  function loadState() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (raw) {
        const data = JSON.parse(raw);
        sessionId = data.sessionId || null;
        messages = data.messages || [];
      }
    } catch (_) {}
  }

  // ---------------------------------------------------------------------------
  // Build DOM inside Shadow DOM
  // ---------------------------------------------------------------------------
  function buildWidget() {
    const host = document.createElement("div");
    host.id = "voiceagent-chat-widget";
    document.body.appendChild(host);

    const shadow = host.attachShadow({ mode: "closed" });

    // Styles
    const style = document.createElement("style");
    style.textContent = CSS;
    shadow.appendChild(style);

    // Root wrapper — `all: initial` breaks CSS inheritance from host page
    const root = document.createElement("div");
    root.className = "widget-root";
    shadow.appendChild(root);

    // Launcher button
    const launcher = document.createElement("button");
    launcher.className = "launcher";
    launcher.setAttribute("aria-label", "Open chat");
    launcher.innerHTML = ICON_CHAT;
    // Drag support for launcher — drag to reposition, click to open
    let _dragStartX, _dragStartY, _dragOrigX, _dragOrigY, _dragged;

    launcher.addEventListener("mousedown", (e) => {
      _dragged = false;
      _dragStartX = e.clientX;
      _dragStartY = e.clientY;
      const rect = launcher.getBoundingClientRect();
      _dragOrigX = rect.left;
      _dragOrigY = rect.top;
      launcher.classList.add("dragging");

      function onMove(ev) {
        const dx = ev.clientX - _dragStartX;
        const dy = ev.clientY - _dragStartY;
        if (Math.abs(dx) > 4 || Math.abs(dy) > 4) _dragged = true;
        if (!_dragged) return;
        launcher.style.left = (_dragOrigX + dx) + "px";
        launcher.style.top = (_dragOrigY + dy) + "px";
        launcher.style.right = "auto";
        launcher.style.bottom = "auto";
      }

      function onUp() {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        launcher.classList.remove("dragging");
        if (!_dragged) toggleOpen();
      }

      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      e.preventDefault();
    });

    root.appendChild(launcher);

    // Chat window
    const chatWindow = document.createElement("div");
    chatWindow.className = "chat-window";
    chatWindow.innerHTML = `
      <div class="header">
        <span class="header-title">${escapeHtml(CONFIG.practice)}</span>
        <div class="header-actions">
          <button class="header-btn reset-btn" aria-label="New conversation">${ICON_RESET}</button>
          <button class="header-btn minimize-btn" aria-label="Minimize">${ICON_MINIMIZE}</button>
          <button class="header-btn close-btn" aria-label="Close">${ICON_CLOSE}</button>
        </div>
      </div>
      <div class="status-bar"></div>
      <div class="messages">
        <div class="typing">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
      </div>
      <div class="input-area">
        <input type="text" placeholder="Type your message..." aria-label="Message" />
        <button class="send-btn" aria-label="Send">${ICON_SEND}</button>
      </div>
    `;
    root.appendChild(chatWindow);

    // Store element refs
    els = {
      launcher,
      chatWindow,
      messagesArea: chatWindow.querySelector(".messages"),
      typingIndicator: chatWindow.querySelector(".typing"),
      statusBar: chatWindow.querySelector(".status-bar"),
      input: chatWindow.querySelector("input"),
      sendBtn: chatWindow.querySelector(".send-btn"),
    };

    // Event listeners
    chatWindow.querySelector(".reset-btn").addEventListener("click", resetConversation);
    chatWindow.querySelector(".minimize-btn").addEventListener("click", minimize);
    chatWindow.querySelector(".close-btn").addEventListener("click", minimize);
    els.sendBtn.addEventListener("click", sendMessage);
    els.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
      if (e.key === "Escape") {
        minimize();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // UI helpers
  // ---------------------------------------------------------------------------
  function toggleOpen() {
    if (isOpen) {
      minimize();
    } else {
      openChat();
    }
  }

  function openChat() {
    isOpen = true;
    els.chatWindow.classList.add("open");
    els.launcher.classList.add("hidden");
    els.input.focus();

    // Connect if not connected
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      connect();
    }
  }

  function minimize() {
    isOpen = false;
    els.chatWindow.classList.remove("open");
    els.launcher.classList.remove("hidden");
  }

  function resetConversation() {
    // Clear state
    messages = [];
    sessionId = null;
    saveState();

    // Clear message bubbles from UI (keep typing indicator)
    const bubbles = els.messagesArea.querySelectorAll(".message");
    bubbles.forEach((el) => el.remove());

    // Close existing connection so a fresh session is created
    if (ws) {
      ws.onclose = null; // prevent reconnect
      ws.close();
      ws = null;
    }

    // Reconnect (will create new server session + show greeting)
    connect();
  }

  function addMessageToUI(role, content) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    if (role === "agent") {
      div.innerHTML = formatMarkdown(content);
    } else {
      div.textContent = content;
    }
    // Insert before typing indicator
    els.messagesArea.insertBefore(div, els.typingIndicator);
    scrollToBottom();
  }

  function formatMarkdown(text) {
    // Escape HTML first
    let html = escapeHtml(text);

    // Bold: **text**
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

    // Italic: *text* (but not inside bold)
    html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");

    // Split into lines for block-level processing
    const lines = html.split("\n");
    const result = [];
    let inList = false;

    for (const line of lines) {
      const trimmed = line.trim();

      // List item: - text or * text
      if (/^[-*]\s+/.test(trimmed)) {
        if (!inList) {
          result.push("<ul>");
          inList = true;
        }
        result.push("<li>" + trimmed.replace(/^[-*]\s+/, "") + "</li>");
      } else {
        if (inList) {
          result.push("</ul>");
          inList = false;
        }
        if (trimmed === "") {
          result.push("<br>");
        } else {
          result.push(trimmed);
        }
      }
    }
    if (inList) result.push("</ul>");

    return result.join("\n");
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      els.messagesArea.scrollTop = els.messagesArea.scrollHeight;
    });
  }

  function showTyping(visible) {
    els.typingIndicator.classList.toggle("visible", visible);
    if (visible) scrollToBottom();
  }

  function showStatus(text, isError) {
    els.statusBar.textContent = "";
    els.statusBar.className = `status-bar visible${isError ? " error" : ""}`;

    if (isError && reconnectAttempts >= RECONNECT_MAX_ATTEMPTS) {
      els.statusBar.textContent = text + " ";
      const btn = document.createElement("button");
      btn.textContent = "Retry";
      btn.addEventListener("click", () => {
        reconnectAttempts = 0;
        connect();
      });
      els.statusBar.appendChild(btn);
    } else {
      els.statusBar.textContent = text;
    }
  }

  function hideStatus() {
    els.statusBar.className = "status-bar";
  }

  function setInputEnabled(enabled) {
    els.input.disabled = !enabled;
    els.sendBtn.disabled = !enabled;
    if (enabled && isOpen) {
      els.input.focus();
    }
  }

  // ---------------------------------------------------------------------------
  // Restore messages from sessionStorage
  // ---------------------------------------------------------------------------
  function restoreMessages() {
    for (const msg of messages) {
      addMessageToUI(msg.role, msg.content);
    }
  }

  // ---------------------------------------------------------------------------
  // WebSocket
  // ---------------------------------------------------------------------------
  function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    showStatus("Connecting...", false);

    try {
      ws = new WebSocket(WS_URL);
    } catch (_) {
      showStatus("Connection failed.", true);
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      reconnectAttempts = 0;
      hideStatus();
      setInputEnabled(true);
      startPing();

      // If no prior messages, show greeting as agent message
      if (messages.length === 0) {
        messages.push({ role: "agent", content: CONFIG.greeting });
        addMessageToUI("agent", CONFIG.greeting);
        saveState();
      }
    };

    ws.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch (_) {
        return;
      }

      switch (data.type) {
        case "message":
          showTyping(false);
          // Track session_id from server
          if (data.session_id) {
            sessionId = data.session_id;
          }
          messages.push({ role: "agent", content: data.content });
          addMessageToUI("agent", data.content);
          saveState();
          setInputEnabled(true);
          break;

        case "typing":
          showTyping(data.status === true);
          break;

        case "welcome":
          if (data.session_id) sessionId = data.session_id;
          break;

        case "error":
          showTyping(false);
          messages.push({ role: "agent", content: data.content });
          addMessageToUI("agent", data.content);
          saveState();
          setInputEnabled(true);
          break;

        case "pong":
          // Keepalive acknowledged
          break;
      }
    };

    ws.onclose = () => {
      stopPing();
      if (isOpen) {
        showStatus("Disconnected. Reconnecting...", false);
        scheduleReconnect();
      }
    };

    ws.onerror = () => {
      // onclose will fire after this
    };
  }

  function scheduleReconnect() {
    if (reconnectTimer) return;
    if (reconnectAttempts >= RECONNECT_MAX_ATTEMPTS) {
      showStatus("Connection lost.", true);
      return;
    }

    const delay = Math.min(
      RECONNECT_BASE_MS * Math.pow(2, reconnectAttempts),
      RECONNECT_MAX_MS
    );
    reconnectAttempts++;

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, delay);
  }

  function startPing() {
    stopPing();
    pingInterval = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, PING_INTERVAL_MS);
  }

  function stopPing() {
    if (pingInterval) {
      clearInterval(pingInterval);
      pingInterval = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Send message
  // ---------------------------------------------------------------------------
  function sendMessage() {
    const text = (els.input.value || "").trim();
    if (!text) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    // Add to UI + state
    messages.push({ role: "user", content: text });
    addMessageToUI("user", text);
    els.input.value = "";
    saveState();

    // Disable input while waiting
    setInputEnabled(false);

    // Send to server
    ws.send(
      JSON.stringify({
        type: "message",
        content: text,
        session_id: sessionId,
      })
    );
  }

  // ---------------------------------------------------------------------------
  // Utils
  // ---------------------------------------------------------------------------
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  loadState();
  buildWidget();
  restoreMessages();
})();

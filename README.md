# **Hermes Messaging Service**

*A lightweight, extensible, queue-backed messaging system for the Prodigy platform.*

Hermes is the dedicated messaging microservice for the Prodigy ecosystem. It receives notification requests from other internal services, stores them reliably in a Postgres-backed queue, and dispatches them asynchronously through specialized adapters (Email, Telegram, and future channels such as Discord).

Hermes operates alongside **Charon**, the background worker responsible for processing queued messages and delivering them via the correct channel.

Hermes handles inbound webhooks (for verification flows), outbound queueing, idempotency, template rendering, and channel-specific adapter routing.

---

# **Architecture Overview**

```
           ┌────────────┐
           │ Upstream    │
           │ Services    │
           └──────┬──────┘
                  │   POST /messages
                  ▼
           ┌────────────┐
           │  Hermes     │  Flask HTTP API
           │  (API)      │
           └──────┬──────┘
                  │   INSERT queued rows
                  ▼
        ┌────────────────────┐
        │   Postgres Queue   │
        │  messages table    │
        └────────┬───────────┘
                 │   SELECT FOR UPDATE SKIP LOCKED
                 ▼
        ┌────────────────────┐
        │     Charon         │  Background worker
        │  (Dispatcher)      │
        └──────┬────────────┘
               │  adapter.send()
               ▼
       ┌──────────────────┐         ┌───────────────────┐
       │ Email Adapter     │ SMTP    │ Telegram Adapter  │ Bot API
       │ (Gmail SMTP)      ├────────►│ (MarkdownV2)      ├─────────► Users
       └──────────────────┘         └───────────────────┘
```

---

# **Key Responsibilities**

### **Hermes (API layer)**

* Accepts message requests via `/messages`
* Accepts Telegram Bot webhook events via `/webhooks/telegram`
* Validates payloads
* Assigns templates using subject/channel translation
* Enqueues messages into Postgres
* Enforces idempotency using `idempotency_key`
* Provides `/health` endpoint

(Implementation: )

---

### **Charon (Worker layer)**

* Continuously polls Postgres for queued messages
* Locks rows safely using `FOR UPDATE SKIP LOCKED`
* Dispatches messages to the appropriate adapter (`email`, `telegram`, etc.)
* Retries messages on failure
* Marks messages as `sent`, `failed`, or increments `attempts`

(Implementation: )

---

### **Oreiades (Core helpers)**

Provides:

* Database connections
* Message creation logic
* Idempotency enforcement
* Message state transitions
* Health checking
* Template resolution logic
* Centralized environment variable management

(Implementation: )

---

### **Adapters**

#### **Email Adapter (Gmail SMTP)**

* Renders HTML templates
* Sends mail via SMTP + TLS
* Supports custom subject and embedded variables

(Implementation: )

#### **Telegram Adapter (Bot API)**

* Renders MarkdownV2 templates with safe escaping
* Handles command-specific transformations (`/ping`, `/verify`, `/welcome`)
* Sends via Telegram’s Bot API
* Used for verification and notifications

(Implementation: )

---

# **Message Flow**

### **1. Upstream service sends a notification request**

```http
POST /messages
Content-Type: application/json

{
  "channel": "email",
  "to": "user@example.com",
  "subject": "password reset",
  "data": {
      "username": "Ben",
      "reset_link": "https://app/reset/123"
  },
  "idempotency_key": "reset:user123:token123"
}
```

Hermes validates, assigns the correct template, and inserts a queued row.

---

### **2. Charon processes and delivers**

Charon picks messages in FIFO order:

* Loads the row
* Selects correct adapter: `ADAPTERS[channel]`
* Renders template
* Sends message
* Updates message state (`sent`, `failed`, `attempts`)

---

# **Idempotency**

Hermes supports idempotent message creation:

* If a request includes an `idempotency_key`, Hermes will **return the same message row** on duplicate submissions rather than queueing multiple sends.
* Upstream services should reuse the same key for retries of the *same logical action*.

Example:

* `password_reset:user123:tokenXYZ`
  Double-clicks or network retries will not enqueue two emails.

---

# **Telegram Verification Workflow**

This service supports a full Telegram verification loop:

### **1. User starts chat with bot**

User runs:

```
/ping
```

Bot replies with a rendered template:

```
Hello Benjamin

This is your Telegram chat id:

123456789

Copy this chat id into the Prodigy website...
```

Chat ID is extracted by Hermes’s webhook handler and included in the message template.

### **2. User enters chat_id into the site**

Prodigy backend stores `(user_id, chat_id)` for verification.

### **3. Site instructs user to run `/verify`**

User returns to Telegram:

```
/verify
```

Hermes processes this via `/webhooks/telegram`, and can:

* Look up the chat_id in Prodigy's DB (future integration)
* Confirm verification
* Return a “Linked successfully” message

### **4. Verified template example**

**Telegram verified message:**

```
*Telegram verification complete*

Your chat id is now linked to your Prodigy account.

Account name    Benjamin
Email           ben@example.com

You will now receive notifications here.
```

Template resolution handled by Translator mapping in Hermes.

---

# **Templates**

Hermes ships with both Markdown (Telegram) and HTML (Email) templates.

### Telegram templates are in:

```
templates/telegram/*.md
```

Use `%%key%%` placeholders which are Markdown-safe.

### Email templates are in:

```
templates/email/*.html
```

Use `{{key}}` placeholders.

Both template systems are rendered inside their respective adapters.

---

# **Endpoints**

### **POST /messages**

Enqueue a message for processing.

### **POST /webhooks/telegram**

Receives Telegram Bot events and turns them into queue items.

### **GET /health**

Checks environment variables and SMTP configuration.

---

# **Running the Service**

### Run API (Hermes)

```bash
python hermes.py
```

### Run Worker (Charon)

```bash
python charon.py
```

### Environment Variables

* `DB_HOST`
* `DB_PORT`
* `DB_NAME`
* `DB_USER`
* `DB_PASSWORD`
* `EMAIL_SMTP_HOST`
* `EMAIL_SMTP_PORT`
* `EMAIL_USER`
* `EMAIL_APP_PASSWORD`
* `TELEGRAM_BOT_TOKEN`
* `TELEGRAM_WEBHOOK_SECRET`
* `MESSAGE_MAX_ATTEMPTS`

---

# **Why Hermes Exists**

Hermes isolates messaging logic from the rest of Prodigy:

* asynchronous delivery
* retry handling
* HTML/Markdown template rendering
* webhook handling
* idempotency
* channel-agnostic adapter model
* flexible expansion (e.g. Discord coming soon)

By centralizing all outbound notifications, Prodigy stays consistent, reliable, and easier to maintain.

---

# **Future Work**

* Discord Adapter
* Message auditing dashboard
* Delivery metrics
* Rate limiting / throttling
* Support for attachments
* Unified retry schedules
* Multi-language templates

---

# **Conclusion**

Hermes + Charon form a fully functional, extensible messaging service powering Prodigy’s notification system. The design emphasizes reliability, idempotency, clean separation of concerns, and simple adapter-based extension for new channels.

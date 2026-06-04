# Spec: assistant-template

## Purpose

A reusable monorepo template for rapid deployment of Telegram AI-assistants. The template provides separate bot and admin services, PostgreSQL database, and Docker Compose configuration. Designed for multi-project deployment on a single VPS with external Caddy reverse proxy.

## Requirements

### Requirement: Project shall be reusable for multiple independent assistants

The system SHALL be structured as a reusable monorepo template for Telegram AI-assistants.

#### Scenario: Developer creates a new assistant from template

- **WHEN** a fresh copy of the template is created and the developer fills `.env` and starts Docker Compose
- **THEN** the bot, admin service and PostgreSQL SHALL start as an independent project

#### Scenario: Multiple projects run on one VPS

- **WHEN** several assistant projects are deployed on the same VPS, each with its own `.env`
- **THEN** services SHALL NOT conflict by container names, database volumes or host ports

### Requirement: Project shall expose separate bot and admin services

The system SHALL run the Telegram bot and admin panel as separate Docker services.

#### Scenario: Start services

- **WHEN** `docker compose up -d --build` is executed from the `infra/` directory
- **THEN** services `bot`, `admin`, and `postgres` SHALL be started

### Requirement: Project shall use external Caddy

The system SHALL NOT run Caddy inside Docker Compose.

#### Scenario: Reverse proxy is configured

- **WHEN** host-level Caddy is installed on the VPS and developer configures Caddyfile
- **THEN** public domains SHALL reverse proxy to `127.0.0.1:${BOT_HOST_PORT}` and `127.0.0.1:${ADMIN_HOST_PORT}`

### Requirement: Host ports shall be configurable and safe for multi-project deployment

The system SHALL read host ports from `.env`.

Required variables:

```env
BOT_HOST_PORT=
ADMIN_HOST_PORT=
```

#### Scenario: Admin port is randomized

- **WHEN** a developer initializes a new project and executes the init script
- **THEN** the script SHALL generate a random free `ADMIN_HOST_PORT` and write it into `.env`

#### Scenario: Port binding is local only

- **WHEN** services are started and Docker publishes ports
- **THEN** ports SHALL be bound to `127.0.0.1`, not `0.0.0.0`

Example:

```yaml
ports:
  - "127.0.0.1:${ADMIN_HOST_PORT}:8080"
```

### Requirement: Template shall include deployment documentation

The system SHALL include README instructions for:

- local startup;
- VPS deployment;
- `.env` setup;
- port generation;
- Caddy configuration;
- migrations;
- Telegram bot token setup;
- admin login flow;
- how to enable censor;
- how to enable voice recognition;
- how to configure `ADMIN_TELEGRAM_CHAT_ID`.

#### Scenario: Developer reads README

- **WHEN** a fresh copy of the template is created and the developer opens the README
- **THEN** all sections listed above SHALL be present and actionable

### Requirement: Request pipeline shall support voice, censor and send_to_admin

The bot service SHALL process every incoming Telegram update through a defined pipeline.

Required pipeline order:

```text
Telegram update
→ normalize input
→ if voice/audio: STT pipeline (OpenAI primary, Aisha fallback)
→ message log
→ assemble prompt:
   core guardrails
   active system prompt
   active tools instruction
→ LangChain agent
→ tool calls if needed, including send_to_admin
→ draft response
→ if censor enabled: censor LLM pass
→ final response
→ send to Telegram
→ logs/traces/LangSmith
```

#### Scenario: Text message with censor enabled

- **WHEN** user sends a text message and censor is enabled
- **THEN** the censor LLM SHALL review the draft response
- **THEN** the final response SHALL be the censor output

#### Scenario: Voice message processed

- **WHEN** user sends a voice message and `VOICE_ENABLED=true`
- **THEN** the transcribed text SHALL be processed as a regular text message through the full pipeline

### Requirement: Bot service shall support polling and webhook modes

The bot service SHALL support two operation modes controlled by `BOT_MODE` env variable.

```env
BOT_MODE=polling
```

Supported values: `polling`, `webhook`.

#### Scenario: Polling mode

- **WHEN** `BOT_MODE=polling` and the bot service starts
- **THEN** the bot SHALL use Telegram long polling to receive updates

#### Scenario: Webhook mode

- **WHEN** `BOT_MODE=webhook` and the bot service starts
- **THEN** the bot SHALL register a Telegram webhook and listen via FastAPI HTTP endpoint

### Requirement: Bot service shall expose health endpoint

The bot service SHALL expose:

```http
GET /health
```

Expected response:

```json
{"status":"OK","service":"bot"}
```

#### Scenario: Health check

- **WHEN** the bot service is running and a GET request is sent to `/health`
- **THEN** the response SHALL be `{"status":"OK","service":"bot"}` with HTTP 200

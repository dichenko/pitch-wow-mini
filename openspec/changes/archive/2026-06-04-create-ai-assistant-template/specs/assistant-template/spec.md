# Spec Delta: assistant-template

## Capability

```text
assistant-template
```

## ADDED Requirements

### Requirement: Project shall be reusable for multiple independent assistants

The system SHALL be structured as a reusable monorepo template for Telegram AI-assistants.

#### Scenario: Developer creates a new assistant from template

- GIVEN a fresh copy of the template
- WHEN the developer fills `.env` and starts Docker Compose
- THEN the bot, admin service and PostgreSQL SHALL start as an independent project

#### Scenario: Multiple projects run on one VPS

- GIVEN several assistant projects deployed on the same VPS
- WHEN each project has its own `.env`
- THEN services SHALL NOT conflict by container names, database volumes or host ports

### Requirement: Project shall expose separate bot and admin services

The system SHALL run the Telegram bot and admin panel as separate Docker services.

#### Scenario: Start services

- GIVEN Docker Compose configuration
- WHEN `docker compose up -d --build` is executed
- THEN services `bot`, `admin`, and `postgres` SHALL be started

### Requirement: Project shall use external Caddy

The system SHALL NOT run Caddy inside Docker Compose.

#### Scenario: Reverse proxy is configured

- GIVEN host-level Caddy is already installed on the VPS
- WHEN developer configures Caddyfile
- THEN public domains SHALL reverse proxy to `127.0.0.1:${BOT_HOST_PORT}` and `127.0.0.1:${ADMIN_HOST_PORT}`

### Requirement: Host ports shall be configurable and safe for multi-project deployment

The system SHALL read host ports from `.env`.

Required variables:

```env
BOT_HOST_PORT=
ADMIN_HOST_PORT=
```

#### Scenario: Admin port is randomized

- GIVEN a developer initializes a new project
- WHEN the init script is executed
- THEN the script SHALL generate a random free `ADMIN_HOST_PORT`
- AND write it into `.env`

#### Scenario: Port binding is local only

- GIVEN services are started
- WHEN Docker publishes ports
- THEN ports SHALL be bound to `127.0.0.1`, not `0.0.0.0`

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

- GIVEN a fresh copy of the template
- WHEN the developer opens the README
- THEN all sections listed above SHALL be present and actionable

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

- GIVEN user sends a text message and censor is enabled
- WHEN the main agent produces a draft response
- THEN the censor LLM SHALL review the draft
- AND the final response SHALL be the censor output

#### Scenario: Voice message processed

- GIVEN user sends a voice message and `VOICE_ENABLED=true`
- WHEN STT pipeline returns transcribed text
- THEN the transcribed text SHALL be processed as a regular text message through the full pipeline

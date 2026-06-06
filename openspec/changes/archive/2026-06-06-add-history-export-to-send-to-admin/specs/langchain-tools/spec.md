## MODIFIED Requirements

### Requirement: Template shall include a mandatory `send_to_admin` tool

The system SHALL provide `send_to_admin` registered out of the box without additional developer configuration.

**LLM-facing signature:** `send_to_admin(comment: str)`. The LLM passes only `comment`. All Telegram user data is attached server-side: `tg_id`, `first_name`, `last_name`, `username`, `telegram_link` (derived from username), `language_code`, `trace_id`, timestamp.

After sending the notification message, the tool SHALL additionally generate and send a markdown file containing the user's full dialogue history.

#### Scenario: Agent calls `send_to_admin`

- **WHEN** the LangChain agent invokes `send_to_admin(comment="...")`
- **THEN** the tool SHALL attach all user fields server-side
- **THEN** the tool SHALL send a formatted notification to the admin chat
- **THEN** the tool SHALL send a `.md` file with the user's full dialogue history

#### Scenario: ADMIN_TELEGRAM_CHAT_ID is not configured

- **WHEN** `ADMIN_TELEGRAM_CHAT_ID` is empty and the agent invokes `send_to_admin`
- **THEN** the tool SHALL save the notification to `admin_notifications` table without breaking the conversation
- **THEN** return a success confirmation to the agent

#### Scenario: ADMIN_TELEGRAM_CHAT_ID is configured

- **WHEN** `ADMIN_TELEGRAM_CHAT_ID` is set and the agent invokes `send_to_admin`
- **THEN** the tool SHALL send the formatted message to that Telegram chat via Bot API
- **THEN** the tool SHALL send a `.md` file attachment with the user's full dialogue history
- **THEN** also save the notification record to `admin_notifications` with `delivered = TRUE`

#### Scenario: User has no username

- **WHEN** a Telegram user without a `username` invokes `send_to_admin`
- **THEN** `telegram_link` SHALL be `null` in the notification payload

#### Scenario: Tool is registered by default

- **WHEN** a new assistant project is created from the template and the bot starts
- **THEN** `send_to_admin` SHALL already be registered in the LangChain agent

#### Scenario: LLM does not generate user data

- **WHEN** the `send_to_admin` tool is invoked and the LLM constructs the tool call
- **THEN** the LLM SHALL only supply the `comment` argument
- **THEN** all user identity fields SHALL be injected server-side

#### Scenario: Tool call is logged

- **WHEN** `send_to_admin` is invoked and the tool completes
- **THEN** the call SHALL be logged to `tool_call_logs`
- **THEN** the notification record SHALL be persisted in `admin_notifications`

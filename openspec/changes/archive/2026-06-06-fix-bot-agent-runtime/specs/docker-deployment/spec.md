## MODIFIED Requirements

### Requirement: Bot and admin shall have healthchecks

Bot and admin services SHALL define Docker healthchecks.

Admin healthcheck SHALL call HTTP GET `http://localhost:8080/health`.

Bot healthcheck SHALL be mode-aware:

- In `BOT_MODE=webhook`, bot healthcheck SHALL call HTTP GET `http://localhost:8000/health`.
- In `BOT_MODE=polling`, bot healthcheck SHALL NOT require an HTTP listener on port 8000 and SHALL verify that the bot process is running.

#### Scenario: Webhook health status via Docker

- **WHEN** services are running with `BOT_MODE=webhook` and `docker ps` lists containers
- **THEN** bot and admin containers SHALL show healthy status
- **THEN** bot health SHALL depend on the FastAPI `/health` endpoint

#### Scenario: Polling health status via Docker

- **WHEN** services are running with `BOT_MODE=polling` and `docker ps` lists containers
- **THEN** bot and admin containers SHALL show healthy status
- **THEN** bot health SHALL NOT fail solely because `http://localhost:8000/health` is not listening

#### Scenario: Polling mode does not start HTTP server for Telegram updates

- **WHEN** the bot starts with `BOT_MODE=polling`
- **THEN** it SHALL start Telegram polling
- **THEN** it SHALL NOT require uvicorn/FastAPI to receive Telegram updates

# Spec Delta: docker-deployment

## Capability

```text
docker-deployment
```

## ADDED Requirements

### Requirement: Docker Compose shall run app services

Docker Compose SHALL include:

- `bot`
- `admin`
- `postgres`

Optional later:

- `worker`
- `redis`

#### Scenario: All services start

- GIVEN `docker compose up -d --build` is executed
- WHEN services initialize
- THEN `bot`, `admin`, and `postgres` SHALL be running

### Requirement: Services shall use project-specific container names implicitly

The system SHALL NOT hardcode global container names.

The system SHALL use Docker Compose project name from env or directory name for container isolation.

Required env:

```env
COMPOSE_PROJECT_NAME=
PROJECT_SLUG=
```

#### Scenario: Container names scoped to project

- GIVEN two projects with different `COMPOSE_PROJECT_NAME` values
- WHEN both are running on the same host
- THEN container names SHALL NOT collide

### Requirement: Postgres volume shall be project-specific

Volume name SHALL be scoped by Docker Compose project name.

Example:

```yaml
volumes:
  postgres_data:
```

The system SHALL NOT use global volume names like `postgres_data_global`.

#### Scenario: Volume isolated per project

- GIVEN two separate projects deployed on the same VPS
- WHEN each project starts PostgreSQL
- THEN each SHALL use its own Docker volume for data persistence

### Requirement: Compose shall bind only localhost ports

The system SHALL bind all published ports to `127.0.0.1` only.

Example:

```yaml
services:
  bot:
    ports:
      - "127.0.0.1:${BOT_HOST_PORT}:8000"

  admin:
    ports:
      - "127.0.0.1:${ADMIN_HOST_PORT}:8080"
```

#### Scenario: Ports not exposed externally

- GIVEN services are running
- WHEN a client connects from outside the host
- THEN the published ports SHALL NOT be reachable directly (only via Caddy reverse proxy)

### Requirement: Env example shall include all required variables

The `.env.example` file SHALL include all required environment variables for the template.

#### Scenario: Developer copies env example

- GIVEN a fresh template copy
- WHEN developer copies `.env.example` to `.env`
- THEN all required variables SHALL be present with sensible defaults or empty placeholders

### Requirement: Template shall include Caddyfile example

The template SHALL include a `Caddyfile.example` demonstrating host-level Caddy reverse proxy configuration.

Example:

```caddyfile
bot.example.com {
    reverse_proxy 127.0.0.1:18001
}

admin.example.com {
    reverse_proxy 127.0.0.1:18002
}
```

#### Scenario: Developer configures Caddy

- GIVEN a developer reads the Caddyfile example
- WHEN they substitute domain names and ports
- THEN the resulting Caddyfile SHALL correctly reverse proxy to the project's containers

### Requirement: Template shall include init script for ports

The template SHALL include a script at `scripts/init_project_env.py`.

Script responsibilities:

- copy `.env.example` to `.env` if `.env` does not exist;
- generate `PROJECT_SLUG` if missing;
- generate random free `BOT_HOST_PORT`;
- generate random free `ADMIN_HOST_PORT`;
- generate `SESSION_SECRET`;
- print Caddyfile snippet.

#### Scenario: Init script generates ports

- GIVEN a developer runs the init script
- WHEN the script completes
- THEN `.env` SHALL contain unique free `BOT_HOST_PORT` and `ADMIN_HOST_PORT` values

### Requirement: Bot Dockerfile shall include ffmpeg

The bot service Dockerfile SHALL install `ffmpeg` for voice audio normalization.

`ffmpeg` SHALL be available in the bot container at runtime.

#### Scenario: Voice audio processing

- GIVEN a voice message is received
- WHEN the bot downloads the audio file
- THEN `ffmpeg` SHALL be used to normalize the audio format before STT processing

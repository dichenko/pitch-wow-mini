# Spec: docker-deployment

## Purpose

Docker Compose infrastructure for running the AI assistant template. Defines bot, admin, and PostgreSQL services with project isolation, localhost-only port binding, health checks, and external Caddy reverse proxy configuration.

## Requirements

### Requirement: Docker Compose shall run app services

Docker Compose SHALL define three services: `bot`, `admin`, and `postgres`.

#### Scenario: All services start

- **WHEN** `docker compose up -d --build` is executed from the `infra/` directory
- **THEN** `bot`, `admin`, and `postgres` SHALL be running

### Requirement: Services shall use project-specific container names

The system SHALL use Docker Compose project name from env for container isolation. Container names are implicitly scoped by the project name; no global names are hardcoded.

Required env: `COMPOSE_PROJECT_NAME`, `PROJECT_SLUG`.

#### Scenario: Container names scoped to project

- **WHEN** two projects with different `COMPOSE_PROJECT_NAME` values are running on the same host
- **THEN** container names SHALL NOT collide

### Requirement: Postgres volume shall be project-specific

The volume `postgres_data` SHALL be scoped by the Docker Compose project name. The system SHALL NOT use global volume names.

#### Scenario: Volume isolated per project

- **WHEN** two separate projects are deployed on the same VPS and each starts PostgreSQL
- **THEN** each SHALL use its own Docker volume for data persistence

### Requirement: Compose shall bind only localhost ports

All published ports SHALL be bound to `127.0.0.1` only.

```yaml
ports:
  - "127.0.0.1:${BOT_HOST_PORT}:8000"
  - "127.0.0.1:${ADMIN_HOST_PORT}:8080"
```

#### Scenario: Ports not exposed externally

- **WHEN** services are running and a client connects from outside the host
- **THEN** the published ports SHALL NOT be reachable directly

### Requirement: Services shall depend on healthy PostgreSQL

Both `bot` and `admin` services SHALL define `depends_on` with `condition: service_healthy` for PostgreSQL.

PostgreSQL SHALL have a healthcheck using `pg_isready`.

#### Scenario: Bot waits for database

- **WHEN** the Docker Compose stack is started and PostgreSQL initializes
- **THEN** the bot and admin services SHALL only start after PostgreSQL passes its healthcheck

### Requirement: Services shall restart automatically

All three services SHALL have `restart: unless-stopped`.

#### Scenario: Service crashes

- **WHEN** a service exits unexpectedly
- **THEN** the container SHALL be automatically restarted

### Requirement: Bot and admin shall have healthchecks

Bot and admin services SHALL define Docker healthchecks that call their respective `/health` endpoints:

Bot: HTTP GET `http://localhost:8000/health`. Admin: HTTP GET `http://localhost:8080/health`.

#### Scenario: Health status via Docker

- **WHEN** services are running and `docker ps` lists containers
- **THEN** bot and admin containers SHALL show healthy status

### Requirement: Env example shall include all required variables

The `.env.example` file SHALL include all required environment variables with sensible defaults or empty placeholders.

#### Scenario: Developer copies env example

- **WHEN** a developer copies `.env.example` to `.env` from a fresh template copy
- **THEN** all required variables SHALL be present

### Requirement: Template shall include Caddyfile example

The template SHALL include an `infra/Caddyfile.example` demonstrating host-level Caddy reverse proxy configuration.

#### Scenario: Developer configures Caddy

- **WHEN** a developer reads the Caddyfile example and substitutes domain names and ports
- **THEN** the resulting Caddyfile SHALL correctly reverse proxy to the project's containers

### Requirement: Template shall include init script

The template SHALL include a script at `scripts/init_project_env.py`.

Script: copies `.env.example` to `.env` if missing, generates `PROJECT_SLUG`, `BOT_HOST_PORT`, `ADMIN_HOST_PORT`, `SESSION_SECRET`, prints Caddyfile snippet.

#### Scenario: Init script generates ports

- **WHEN** a developer runs the init script
- **THEN** `.env` SHALL contain unique free `BOT_HOST_PORT` and `ADMIN_HOST_PORT` values

### Requirement: Bot Dockerfile shall include ffmpeg

The bot service Dockerfile SHALL install `ffmpeg` for voice audio normalization. `ffmpeg` SHALL be available in the bot container at runtime.

#### Scenario: Voice audio processing

- **WHEN** a voice message is received and the bot downloads the audio file
- **THEN** `ffmpeg` SHALL be used to normalize the audio format before STT processing

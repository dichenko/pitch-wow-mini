## 1. Inactivity reporting

- [x] 1.1 Add incoming timestamps, inactivity review model and migration 008.
- [x] 1.2 Replace daily scheduling with full-history inactivity snapshots, summaries, retries and resumed-activity checks.
- [x] 1.3 Replace the Compose worker, defaults and deployment documentation.

## 2. Verification and delivery

- [x] 2.1 Cover the strict inactivity boundary, chronology, deduplication, retries and resumed chats with tests.
- [x] 2.2 Run tests, validate migration/OpenSpec and review the final diff.
- [x] 2.3 Prepare the master release, manual server commands and deployment status check.

Verification: PostgreSQL migration 007:008 compiled in offline mode; strict
OpenSpec and staged diff checks passed. The staged tests are also exercised from
a temporary snapshot so pre-existing user test changes are excluded. Deployment
uses migration-before-start and --remove-orphans to retire the daily worker.
The previously observed Actions blocker is checkout permissions for SSH_USER;
manual deployment commands run as the project owner without changing .env.

## 3. Summary timeout and compact report

- [x] 3.1 Increase summary generation and provider request timeouts to 300 seconds by default.
- [x] 3.2 Reduce the document to dialogue time, Russian summary and full correspondence, retaining a compact user/profile header.
- [x] 3.3 Add OpenAI summary fallback with the same five-minute timeout per attempt.
- [x] 3.4 Verify timeouts, reserve model and compact format, then prepare the tested commit for master.

Follow-up verification: 159 staged tests passed independently of unrelated local
test changes. Coverage includes 300-second worker/provider timeouts, reserve
OpenAI on initialization/generation/timeout/validation failures, identical-model
deduplication, both-model failure and compact reports from legacy snapshots.
Server inspection confirmed the reserve OpenAI key is configured. Retained logs
did not establish the cause of the previous unavailable-summary report.

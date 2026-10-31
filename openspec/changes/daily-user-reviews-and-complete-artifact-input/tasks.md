## 1. Complete artifact input

- [x] 1.1 Snapshot dialogue and the triggering message when enqueueing artifact jobs; preserve legacy fallback.
- [x] 1.2 Add regression coverage for the worker starting before the last turn is saved.

## 2. Daily user reviews

- [x] 2.1 Add the persistent review queue, migration and worker configuration.
- [x] 2.2 Implement Moscow cutoff scheduling, per-user snapshots, three-sentence reviews and Telegram file delivery with retry.
- [x] 2.3 Add tests for boundaries, multiple sessions/users, fallback summaries, restart deduplication and delivery retries.

## 3. Delivery

- [x] 3.1 Add the Compose worker and document configuration, operation and manual deployment.
- [x] 3.2 Validate migration and tests, inspect deployment configuration, commit and push to master.
- [x] 3.3 Check the resulting deployment run and report status or server commands.

Validation: 136 tests passed with test credentials and explicit expected Yandex
voice/speed settings; PostgreSQL migration 006:007 compiled in offline mode;
OpenSpec strict validation and diff checks passed. Implementation pushed as
01fa25e to master. Actions run 41170328907 authenticated over SSH but failed at
git checkout because the deployment user cannot create .git/index.lock. Server
deployment is left to the user using the documented root commands; server
permissions were not changed.

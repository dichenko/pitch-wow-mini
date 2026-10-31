## 1. Complete artifact input

- [x] 1.1 Snapshot dialogue and the triggering message when enqueueing artifact jobs; preserve legacy fallback.
- [x] 1.2 Add regression coverage for the worker starting before the last turn is saved.

## 2. Daily user reviews

- [x] 2.1 Add the persistent review queue, migration and worker configuration.
- [x] 2.2 Implement Moscow cutoff scheduling, per-user snapshots, three-sentence reviews and Telegram file delivery with retry.
- [x] 2.3 Add tests for boundaries, multiple sessions/users, fallback summaries, restart deduplication and delivery retries.

## 3. Delivery

- [x] 3.1 Add the Compose worker and document configuration, operation and manual deployment.
- [ ] 3.2 Validate migration and tests, inspect deployment configuration, commit and push to master.
- [ ] 3.3 Check the resulting deployment run and report status or server commands.

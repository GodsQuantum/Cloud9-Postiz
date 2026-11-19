# Current handoff

Updated: 2026-11-19.

## Deployed and verified

Source commit: ee134289c40424fb8dd98b4cee79852292898390, based on a47fdfae5df510a5096a1aefa4a9dc7d5d4fbeed. Both use official upstream Postiz 2.26.0. This change does not modify the database schema, volumes, credentials, or provider permissions.

The finalizer reads processingDetails before applying a thumbnail. It returns pending with the known video identifier until processingStatus is succeeded. Native workflows retain their durable scheduling; a known video ID bypasses upload-session probing. Terminal errors and the legacy blocking timeout preserve that ID and URL. Only the legacy blocking path adds a bounded ten-second delay between processing checks.

Official contract: https://developers.google.com/youtube/data/reference/rest/v3/thumbnails/set (Shorts thumbnail support introduced in the November 3, 2026 revision).

## Evidence

- Regression red: the unmodified runtime provider failed 14 of the original 16 behavior cases. A second red/green cycle using the actual native runInConcurrent method reproduced transient-error classification and added precise 429/5xx/network cases.
- Regression green: 21/21 behavioral tests pass, including processing wait, terminal failure, retry without a duplicate upload, permanent-error classification, token refresh, no-thumbnail posts, and the legacy deadline.
- The existing first-party local-media test passes; SSRF policy was not changed.
- Conditional application tested twice in an isolated source fixture: first applies and passes 21 cases; second detects equivalent behavior without another source commit.
- Public-source privacy, the eight patch hashes, shell syntax and git whitespace gates pass.
- Independent source review found no critical issue in identity preservation, error handling, native scheduling or conditional application.
- GitHub Actions run https://github.com/GodsQuantum/Cloud9-Postiz/actions/runs/44540215352 succeeded. It cloned the official stable release, applied the existing eight patch families, passed 21/21 tests on that fresh source, compiled frontend/backend/orchestrator, checked the built image and published an immutable candidate.

## Active image

Tag: ghcr.io/godsquantum/cloud9-postiz:upstream-2.26.0-sha-ee134289c404-run-44540215352

Digest: sha256:c836d2e3402826d6c6810a8d8f10c0ff4a15d40d9bce48d7a4c04681701460ff

The immutable image was downloaded and its local digest verified before rollout. At 2026-11-19 14:47:35 UTC, only the application service was recreated after publication edits had completed. The active image matches the digest above. The application is healthy with zero restarts, the frontend returns HTTP 200, and the backend public endpoint returns the expected HTTP 401 without credentials. Targeted startup logs contain no errors. The compiled YouTube provider includes the processing guard. No test upload was sent.

The six existing dependency containers retain the same identifiers, images and start timestamps. Only POSTIZ_IMAGE changed in the Compose environment file; its permissions and ownership were preserved and a dated rollback copy was retained. No manual migration or dependency recreation was performed. The preload left 37,419,089,920 bytes available on the deployment filesystem.

## Repeat rollout and rollback

After coordinating with in-flight publication edits, work in the existing Compose directory. Back up the environment file with its original permissions, change only POSTIZ_IMAGE to the verified local candidate, validate the Compose configuration, then recreate only the postiz service with --no-deps --no-build --pull never. Confirm the image reference, application health and targeted API/log checks. Keep the existing database, queue, Temporal services and all mounts.

The previous immutable tag remains ghcr.io/godsquantum/cloud9-postiz:upstream-2.26.0-sha-a47fdfae5df5-run-43502538125, with digest sha256:8b22d4f05a39e956de25b4188be74d91fefeaa37261b061b38a7080ea72aab41. Rollback changes only POSTIZ_IMAGE back to that tag and repeats the same targeted recreation; do not restore unrelated environment values or database state.

## Scope

Transient retries added by this change concern videos.list only. Image downloading and thumbnails.set retain the existing native error classification, which preserves the published identifier. The tests simulate YouTube responses and do not prove thumbnail permissions for a particular channel. This patch neither diagnoses nor bypasses a live authorization failure. No production posting or credential mutation was performed as a deployment test. An authenticated publication read and a future real YouTube thumbnail result remain separate end-to-end checks; the healthy deployment alone does not establish channel thumbnail authorization.

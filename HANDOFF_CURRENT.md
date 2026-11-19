# Current handoff

Updated: 2026-11-19.

## Ready for source review

Base: a47fdfae5df510a5096a1aefa4a9dc7d5d4fbeed, the existing upstream Postiz 2.26.0 patch set. This branch adds a conditional rebase to the existing YouTube patch family. An isolated immutable candidate build is being prepared through the existing GitHub Actions workflow. No live provider call or production deployment was performed.

The finalizer now reads processingDetails before applying the thumbnail. It returns pending with the known video identifier until processingStatus is succeeded. Native pending workflows retain their existing scheduling; known video identifiers bypass upload-session probing. Terminal errors and the legacy blocking timeout preserve the video identifier and URL. Only the legacy blocking path adds a bounded ten-second delay between processing checks.

Official contract: https://developers.google.com/youtube/data/reference/rest/v3/thumbnails/set (Shorts thumbnail support introduced in the November 3, 2026 revision).

## Verified

- Regression red: the unmodified runtime provider failed 14 of 16 behavior cases; two existing safeguards passed.
- Regression green: 21 of 21 cases pass against the rebased runtime provider, including processing wait, terminal processing failures, retry without duplicate upload, temporary API errors, token refresh, no-thumbnail posts, and legacy timeout.
- The error wrapper is extracted from the native social.abstract.ts source, not simulated. A second red/green cycle reproduced and corrected 429/5xx/network handling while preserving permanent errors.
- Existing first-party local media test passes; the SSRF policy was not changed.
- Conditional application tested twice in an isolated source fixture: first run applies the rebase and passes all 21 cases; second detects equivalent behavior and preserves the fixture commit unchanged.
- The upstream rewriter fails before writing if an expected source anchor changes. Behavioral checks run in CI before the image-build stage.

## Remaining

Independent review and the normal candidate image build/type-checking are in progress. Rollout remains a separate root-managed execution step. These tests stub the remote YouTube API and do not prove that a specific channel has thumbnail permissions. Same-origin thumbnail downloading still follows the existing SSRF-safe request path; this change does not diagnose or bypass a live permission or network failure.

## Candidate procedure

The existing candidate.yml workflow is dispatched on this feature branch. It resolves the current official stable release, applies the eight patch families, runs the source tests, builds and inspects the image on a GitHub runner, then publishes only an immutable GHCR tag. There is no latest-tag promotion and no deployment hook.

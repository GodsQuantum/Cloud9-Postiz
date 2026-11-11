#!/usr/bin/env bash
set -Eeuo pipefail
# Preserve only features not yet included in the upstream release.
PATCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../patches" && pwd)"
UPSTREAM_DIR="${1:?Need path to official Postiz checkout}"
cd "$UPSTREAM_DIR"
test -f Dockerfile.dev
test -f libraries/nestjs-libraries/src/integrations/social/tiktok.provider.ts
git config user.name "Cloud9 Postiz CI"
git config user.email "github-actions@users.noreply.github.com"
echo "UPSTREAM_POSTIZ_COMMIT=$(git rev-parse HEAD)"
apply_mail() {
  local file="$PATCH_ROOT/$1"
  test -s "$file"
  if ! git am -3 "$file";then
    echo "POSTIZ_PATCH_CONFLICT $1 — exact failing paths follow" >&2
    git am --show-current-patch=diff >/tmp/cloud9-postiz-conflict.diff || true
    git apply --check --verbose /tmp/cloud9-postiz-conflict.diff 2>&1 | head -80 || true
    exit 1
  fi
  echo "POSTIZ_PATCH_APPLIED $1"
}
if [[ ! -f libraries/nestjs-libraries/src/upload/s3.storage.ts ]];then
  apply_mail postiz-s3.patch
  apply_mail postiz-local-agent.patch
else
  echo POSTIZ_NATIVE_S3_DETECTED
  apply_mail postiz-local-agent.patch
fi
if grep -qs 'async creatorInfo(accessToken' libraries/nestjs-libraries/src/integrations/social/tiktok.provider.ts &&
   grep -qs 'privacy_level_options' apps/frontend/src/components/new-launch/providers/tiktok/tiktok.provider.tsx &&
   test -f 'apps/frontend/src/app/(public)/review/page.tsx';then
  echo POSTIZ_NATIVE_TIKTOK_AUDIT_DETECTED
else
  apply_mail postiz-tiktok-audit.patch
fi
if grep -qs 'disable_auto_auth=1' libraries/nestjs-libraries/src/integrations/social/tiktok.provider.ts;then
  echo POSTIZ_NATIVE_TIKTOK_ACCOUNT_CHOOSER_DETECTED
else
  apply_mail postiz-tiktok-multiaccount.patch
fi
if grep -qs 'ArrayMaxSize(1' libraries/nestjs-libraries/src/dtos/posts/providers-settings/reddit.dto.ts &&
   grep -qs 'fields.length >= 1' apps/frontend/src/components/new-launch/providers/reddit/reddit.provider.tsx;then
  echo POSTIZ_NATIVE_REDDIT_SAFETY_DETECTED
else
  apply_mail postiz-reddit-responsible-builder.patch
fi
if ! grep -Fqs 'cover_url=${encodeURIComponent(' libraries/nestjs-libraries/src/integrations/social/instagram.provider.ts ||
   ! grep -Fqs 'm.thumbnail' libraries/nestjs-libraries/src/integrations/social/instagram.provider.ts;then
  echo "UPSTREAM_INSTAGRAM_COVER_REGRESSION" >&2;exit 3
fi
if ! grep -Eq '^[[:space:]]+video_cover_timestamp_ms:' libraries/nestjs-libraries/src/integrations/social/tiktok.provider.ts;then
  echo "UPSTREAM_TIKTOK_COVER_REGRESSION" >&2;exit 4
fi
if grep -qs 'location_id?: string' libraries/nestjs-libraries/src/dtos/posts/providers-settings/instagram.dto.ts &&
   grep -qs '&location_id=' libraries/nestjs-libraries/src/integrations/social/instagram.provider.ts;then
  echo POSTIZ_NATIVE_INSTAGRAM_REEL_LOCATION_DETECTED
else
  apply_mail postiz-instagram-location.patch
fi
if grep -Rqs 'POSTIZ_LLM_BASE_URL' apps/backend/src libraries/nestjs-libraries/src &&
   grep -Rqs 'POSTIZ_IMAGE_BASE_URL' apps/backend/src libraries/nestjs-libraries/src &&
   grep -qs 'postizLlm.chat(postizLlmModel)' libraries/nestjs-libraries/src/chat/load.tools.service.ts;then
  echo POSTIZ_NATIVE_LLM_ORIGIN_DETECTED
else
  apply_mail postiz-omniroute.patch
fi
printf '\n# CLOUD9_ROOT_MODE_0755\nRUN chmod 0755 /\n' >> Dockerfile.dev
git diff --check
test -f libraries/nestjs-libraries/src/upload/s3.storage.ts
test -f libraries/nestjs-libraries/src/upload/s3.uploader.ts
test -f apps/frontend/src/helpers/upload.provider.ts
grep -Rqs 'POSTIZ_IMAGE_BASE_URL' libraries/nestjs-libraries/src
grep -Rqs 'POSTIZ_LOCAL_UPLOAD_CIDRS' apps/frontend/src
echo POSTIZ_SEVEN_PATCH_FAMILIES_CONDITIONAL_APPLY_PASS

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
apply_agent_patchset() {
  local tmp count n
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/mails"
  count="$(git mailsplit -o"$tmp/mails" "$PATCH_ROOT/postiz-local-agent.patch")"
  if [[ "$count" != 6 ]];then
    echo "AGENT_MAIL_COUNT_CHANGED=$count" >&2
    exit 1
  fi
  git mailinfo "$tmp/first.message" "$tmp/first.diff" < "$tmp/mails/0001" >/dev/null
  local opts=(
    --include=libraries/nestjs-libraries/src/chat/tools/local.media.path.ts
    --include=libraries/nestjs-libraries/src/chat/tools/next.posting.slot.tool.ts
    --include=libraries/nestjs-libraries/src/chat/tools/transcribe.local.media.tool.ts
    --include=libraries/nestjs-libraries/src/chat/tools/upload.local.media.tool.ts
  )
  git apply --check "${opts[@]}" "$tmp/first.diff"
  git apply "${opts[@]}" "$tmp/first.diff"
  python3 "$PATCH_ROOT/../scripts/rebase_local_agent_initial.py" "$PWD" "$tmp/first.diff"
  git add     libraries/nestjs-libraries/src/chat/load.tools.service.ts     libraries/nestjs-libraries/src/chat/tools/tool.list.ts     libraries/nestjs-libraries/src/chat/tools/local.media.path.ts     libraries/nestjs-libraries/src/chat/tools/next.posting.slot.tool.ts     libraries/nestjs-libraries/src/chat/tools/transcribe.local.media.tool.ts     libraries/nestjs-libraries/src/chat/tools/upload.local.media.tool.ts
  git commit --no-gpg-sign -m "feat: local media workflow rebased onto native Postiz agent tool list" -q
  for n in 0002 0003 0004 0005 0006;do
    git mailinfo "$tmp/message-$n" "$tmp/patch-$n" < "$tmp/mails/$n" >/dev/null
    case "$n" in
      0002)
        python3 "$PATCH_ROOT/../scripts/rebase_agent_followups.py" 2 "$PWD" "$tmp/patch-$n"
        ;;
      0003)
        git apply --check           --exclude=libraries/nestjs-libraries/src/chat/load.tools.service.ts           --exclude=libraries/nestjs-libraries/src/chat/tools/tool.list.ts           "$tmp/patch-$n"
        git apply           --exclude=libraries/nestjs-libraries/src/chat/load.tools.service.ts           --exclude=libraries/nestjs-libraries/src/chat/tools/tool.list.ts           "$tmp/patch-$n"
        python3 "$PATCH_ROOT/../scripts/rebase_agent_followups.py" 3 "$PWD" "$tmp/patch-$n"
        ;;
      0004)
        git apply --check "$tmp/patch-$n"
        git apply "$tmp/patch-$n"
        ;;
      0005)
        # The next mail removes all personal creator-copy instructions.
        # Keep only the upstream-safe post-list improvements here.
        git apply --check           --exclude=libraries/nestjs-libraries/src/chat/load.tools.service.ts           "$tmp/patch-$n"
        git apply           --exclude=libraries/nestjs-libraries/src/chat/load.tools.service.ts           "$tmp/patch-$n"
        ;;
      0006)
        python3 "$PATCH_ROOT/../scripts/rebase_agent_followups.py" 6 "$PWD" "$tmp/patch-$n"
        ;;
    esac
    git add -A
    git commit --no-gpg-sign -m "feat: rebase upstream Postiz agent enhancement $n" -q
    echo "POSTIZ_AGENT_STAGE_REBASED $n"
  done
  rm -rf "$tmp"
  echo POSTIZ_PATCH_APPLIED postiz-local-agent.patch
}
if [[ ! -f libraries/nestjs-libraries/src/upload/s3.storage.ts ]];then
  # The last historical S3 mail references old import ordering in three Next
  # layouts. Apply the first three upstream-compatible mails without change,
  # then apply its new helper and .env snippet and rebase only the specific
  # provider references rather than overwriting upstream layouts.
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/mails"
  count="$(git mailsplit -o"$tmp/mails" "$PATCH_ROOT/postiz-s3.patch")"
  if [[ "$count" != 4 ]];then
    echo "S3_MAIL_COUNT_CHANGED=$count" >&2
    exit 1
  fi
  for n in 0001 0002 0003;do
    git am -3 "$tmp/mails/$n"
  done
  git mailinfo "$tmp/final.message" "$tmp/final.diff" < "$tmp/mails/0004" >/dev/null
  git apply --check \
    --include=.env.example \
    --include=apps/frontend/src/helpers/upload.provider.ts \
    "$tmp/final.diff"
  git apply \
    --include=.env.example \
    --include=apps/frontend/src/helpers/upload.provider.ts \
    "$tmp/final.diff"
  python3 "$PATCH_ROOT/../scripts/rebase_local_upload_layouts.py" "$PWD"
  git add .env.example apps/frontend/src/helpers/upload.provider.ts \
    'apps/frontend/src/app/(app)/layout.tsx' \
    'apps/frontend/src/app/(extension)/layout.tsx' \
    'apps/frontend/src/app/(provider)/layout.tsx'
  git diff --cached --check
  git commit --no-gpg-sign -m "fix: version-aware local upload ingress for upstream layouts" -q
  rm -rf "$tmp"
  echo POSTIZ_PATCH_APPLIED postiz-s3.patch
  apply_agent_patchset
else
  echo POSTIZ_NATIVE_S3_DETECTED
  apply_agent_patchset
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

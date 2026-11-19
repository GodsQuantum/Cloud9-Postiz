#!/usr/bin/env python3
"""Rebase the thumbnail processing guard onto the native pending upload flow."""
from pathlib import Path
import sys

provider = Path(sys.argv[1]) / "libraries/nestjs-libraries/src/integrations/social/youtube.provider.ts"
source = provider.read_text()
if "YOUTUBE_THUMBNAIL_PROCESSING_V1" in source:
    print("POSTIZ_YOUTUBE_THUMBNAIL_PROCESSING_ALREADY_PRESENT")
    raise SystemExit(0)

# A changed upstream contract needs review; never partially rewrite the provider.
replacements = [
    (
        """  ): Promise<PendingCheckResponse> {
    let probe: { videoId: string } | { uploadedBytes: number };""",
        """  ): Promise<PendingCheckResponse> {
    // Once Google returned the video identifier, the upload session can expire.
    // Reuse the native finalizer for the idempotent thumbnail operation only.
    if (pendingData.videoId) {
      return pendingData.thumbnail
        ? { status: 'ready', pendingData }
        : {
            status: 'completed',
            postId: pendingData.videoId,
            releaseURL: `https://www.youtube.com/watch?v=${pendingData.videoId}`,
          };
    }

    let probe: { videoId: string } | { uploadedBytes: number };""",
    ),
    (
        """      try {
        await this.runInConcurrent(async () =>
          youtubeClient.thumbnails.set({""",
        """      try {
        // YOUTUBE_THUMBNAIL_PROCESSING_V1: Shorts thumbnails are supported by
        // the Data API, but are only applied after video processing succeeds.
        // Let the existing pending workflow schedule the next attempt.
        const { data } = await this.runInConcurrent(async () => {
          try {
            return await youtubeClient.videos.list({
              part: ['processingDetails'],
              id: [videoId],
            });
          } catch (err) {
            const status = (err as any)?.response?.status;
            const code = (err as any)?.code;
            if (
              status === 429 ||
              status >= 500 ||
              (!status &&
                ['ECONNRESET', 'ETIMEDOUT', 'ENOTFOUND', 'EAI_AGAIN', 'ECONNREFUSED', 'ERR_NETWORK'].includes(code))
            ) {
              // Keep transient processing checks out of the native terminal
              // error classifier; the pending workflow owns retries.
              return { data: { items: [] } };
            }
            throw err;
          }
        });
        const processingStatus =
          data.items?.[0]?.processingDetails?.processingStatus;
        if (processingStatus === 'failed' || processingStatus === 'terminated') {
          throw new BadBody(
            this.identifier,
            '{}',
            '{}',
            'The video was uploaded, but YouTube processing failed before its thumbnail could be applied'
          );
        }
        if (processingStatus !== 'succeeded') {
          return {
            status: 'pending',
            pendingData: { ...pendingData, videoId },
          };
        }

        await this.runInConcurrent(async () =>
          youtubeClient.thumbnails.set({""",
    ),
    (
        """      // is safe (no video exists until the upload completes and the abandoned
      // session just expires), timing the activity out is not.""",
        """      // is safe only while no video exists. Once uploaded, retain its id and
      // URL in PublishedWithError so a timeout cannot invite a duplicate post.""",
    ),
    (
        """        8 * 60 * 1000 - YoutubeProvider.YOUTUBE_UPLOAD_BATCH_MS
      ) {
        throw new BadBody(""",
        """        8 * 60 * 1000 - YoutubeProvider.YOUTUBE_UPLOAD_BATCH_MS
      ) {
        if (pendingData.videoId) {
          throw new PublishedWithError(
            this.identifier,
            pendingData.postDbId || response.id,
            pendingData.videoId,
            `https://www.youtube.com/watch?v=${pendingData.videoId}`,
            'The video was uploaded, but processing did not finish before the thumbnail deadline'
          );
        }
        throw new BadBody(""",
    ),
    (
        """      pendingData = finalize.pendingData;
    }
  }""",
        """      pendingData = finalize.pendingData;
      if (pendingData.videoId) {
        // Only the legacy blocking workflow needs this delay. New workflows
        // already use durable polling and must not start a separate timer.
        await new Promise((resolve) => setTimeout(resolve, 10_000));
      }
    }
  }""",
    ),
]
for old, new in replacements:
    if source.count(old) != 1:
        raise SystemExit("Unsupported upstream YouTube finalizer: " + old.splitlines()[0])
    source = source.replace(old, new)
provider.write_text(source)
print("POSTIZ_YOUTUBE_THUMBNAIL_PROCESSING_REBASED")

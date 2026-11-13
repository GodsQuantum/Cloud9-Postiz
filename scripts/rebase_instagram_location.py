#!/usr/bin/env python3
"""Extend exactly one upstream Instagram single-video publish URL, retaining its parameters."""
from pathlib import Path
import sys


def rebase(root: Path) -> None:
    path = root / "libraries/nestjs-libraries/src/integrations/social/instagram.provider.ts"
    s = path.read_text()
    before = """        const itemCollaborators =
          firstPost?.media?.length === 1 ? collaborators : ``;

"""
    location = """        const itemLocation =
          firstPost?.settings?.location_id &&
          !isStory &&
          firstPost?.media?.length === 1 &&
          hasExtension(m.path, 'mp4')
            ? `&location_id=${encodeURIComponent(firstPost.settings.location_id)}`
            : ``;

"""
    old = "${trialParams}${audioConfiguration}"
    new = "${trialParams}${itemLocation}${audioConfiguration}"
    if s.count(before) != 1 or s.count(old) != 1 or "const itemLocation =" in s:
        raise ValueError("Instagram upstream publish URL changed: manual semantic review required")
    path.write_text(s.replace(before, before + location).replace(old, new))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: rebase_instagram_location.py <upstream>")
    rebase(Path(sys.argv[1]))

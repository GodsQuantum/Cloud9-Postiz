#!/usr/bin/env python3
"""Expose public TikTok review/legal pages without losing upstream OAuth routes."""
from pathlib import Path
import sys
base=Path(sys.argv[1])
file=base/"apps/frontend/src/proxy.ts"
source=file.read_text()
marker="    nextUrl.pathname.startsWith('/oauth/authorize')"
assert source.count(marker)==1,("UPSTREAM_OAUTH_PROXY_ROUTE_CHANGED",source.count(marker))
assert "nextUrl.pathname === '/review'" not in source
source=source.replace(marker,marker+" ||\n"+
                      "    nextUrl.pathname === '/review' ||\n"+
                      "    nextUrl.pathname === '/privacy' ||\n"+
                      "    nextUrl.pathname === '/terms'")
assert source.count("nextUrl.pathname.startsWith('/oauth/authorize')")==1
file.write_text(source)
print("POSTIZ_PUBLIC_TIKTOK_PAGES_ALLOWED_KEEP_UPSTREAM_OAUTH",flush=True)

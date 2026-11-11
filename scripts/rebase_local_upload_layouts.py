#!/usr/bin/env python3
"""Preserve local-LAN/S3 request selection across upstream layout import reorderings.

Fail closed if an upstream layout no longer has the expected Postiz provider.
Never rewrite an entire upstream layout, only the four small semantic changes.
"""
from pathlib import Path
import re,sys
base=Path(sys.argv[1]).resolve()
paths=[
 "apps/frontend/src/app/(app)/layout.tsx",
 "apps/frontend/src/app/(extension)/layout.tsx",
 "apps/frontend/src/app/(provider)/layout.tsx",
]
for name in paths:
 file=base/name
 assert file.is_file(),name
 text=file.read_text()
 assert 'getRequestStorageProvider' not in text,("ALREADY_PRESENT",name)
 assert "VariableContextComponent" in text,("UPSTREAM_PROVIDER_MISSING",name)
 import_statement="import { getRequestStorageProvider } from '@gitroom/frontend/helpers/upload.provider';"
 # Append next to the context provider import rather than relying on exact
 # upstream import order (the old fourth mail patch anchored that order).
 matched=re.search(r"^import .*VariableContextComponent.*;$",text,re.M)
 assert matched is not None,("PROVIDER_IMPORT_CHANGED",name)
 text=text[:matched.end()]+"\n"+import_statement+text[matched.end():]
 fn=r"(export default async function AppLayout\([^\n]*\)\s*\{)"
 text,n=re.subn(fn,r"\1\n  const storageProvider = await getRequestStorageProvider();",text,count=1)
 assert n==1,("LAYOUT_FUNCTION_CHANGED",name)
 expr=r"storageProvider=\{\s*process\.env\.STORAGE_PROVIDER!\s+as\s+'local'\s*\|\s*'cloudflare'\s*\|\s*'s3'\s*\}"
 text,n=re.subn(expr,"storageProvider={storageProvider}",text,count=1)
 assert n==1,("ORIGINAL_STORAGE_PROVIDER_CHANGED",name)
 old="process.env.STORAGE_PROVIDER === 's3'"
 assert text.count(old)==1,("ORIGINAL_S3_CHECK_CHANGED",name,text.count(old))
 text=text.replace(old,"storageProvider === 's3'")
 file.write_text(text)
 print("POSTIZ_DYNAMIC_STORAGE_PROVIDER_REBASED",name,flush=True)

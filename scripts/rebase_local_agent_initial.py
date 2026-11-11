#!/usr/bin/env python3
"""Rebase first agent mail by stable semantics, not old Next source line offsets."""
from pathlib import Path
import re,sys
base=Path(sys.argv[1])
patch=Path(sys.argv[2]).read_text()
blocks={}
for chunk in re.split(r"(?=^diff --git a/)",patch,flags=re.M):
 if chunk.startswith("diff --git a/"):
  path=chunk.split(" b/",1)[0].split("a/",1)[1]
  blocks[path]=chunk
def added_lines(name):
 return [v[1:] for v in blocks[name].splitlines()
         if v.startswith("+") and not v.startswith("+++")]
def removed_lines(name):
 return [v[1:] for v in blocks[name].splitlines()
         if v.startswith("-") and not v.startswith("---")]
target="libraries/nestjs-libraries/src/chat/load.tools.service.ts"
added=added_lines(target)
removed=removed_lines(target)
assert len(added)==5 and len(removed)==1,("AGENT_PROMPT_HUNK_CHANGED",len(added),len(removed))
file=base/target
s=file.read_text()
assert s.count(removed[0])==1,"Upstream Postiz confirmation instruction changed"
s=s.replace(removed[0],"\n".join(added))
file.write_text(s)
print("POSTIZ_AGENT_PROMPT_ADDED_WITH_NATIVE_UPSTREAM_CONTEXT",flush=True)
target="libraries/nestjs-libraries/src/chat/tools/tool.list.ts"
added=added_lines(target)
assert len(added)==6,("AGENT_TOOLS_HUNK_CHANGED",added)
imports=[x for x in added if x.startswith("import ")]
classes=[x for x in added if x.lstrip().startswith(("UploadLocalMediaTool", "TranscribeLocalMediaTool", "NextPostingSlotTool"))]
assert len(imports)==len(classes)==3
file=base/target
s=file.read_text()
anchor="import { UploadWidgetStatusTool } from '@gitroom/nestjs-libraries/chat/tools/upload.widget.status.tool';"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+"\n"+"\n".join(imports))
anchor="  UploadWidgetStatusTool,"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+"\n"+"\n".join(classes))
file.write_text(s)
print("POSTIZ_AGENT_THREE_NEW_TOOL_REGISTRATIONS_REBASED",flush=True)

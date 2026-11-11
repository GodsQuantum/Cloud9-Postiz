#!/usr/bin/env python3
"""Apply only additive MCP agent prompt/tool changes against current upstream.

Handles four stable semantic anchors instead of matching outdated hunk context.
Never silently overwrite an upstream change.
"""
from pathlib import Path
import re,sys
stage=int(sys.argv[1])
base=Path(sys.argv[2])
text=Path(sys.argv[3]).read_text()
chunks={}
for blob in re.split(r"(?=^diff --git a/)",text,flags=re.M):
 if blob.startswith("diff --git a/"):
  path=blob.split(" b/",1)[0].split("a/",1)[1]
  chunks[path]=blob
def hunks(name):
 return re.split(r"(?=^@@)",chunks[name],flags=re.M)[1:]
def additions(chunk):
 return [line[1:] for line in chunk.splitlines()
         if line.startswith("+") and not line.startswith("+++")]
def replace_once(s,old,new,name):
 count=s.count(old)
 assert count==1,(name,"semantic source anchor changed",count)
 return s.replace(old,new)
load="libraries/nestjs-libraries/src/chat/load.tools.service.ts"
tools="libraries/nestjs-libraries/src/chat/tools/tool.list.ts"
if stage==2:
 values=additions(hunks(load)[0])
 assert len(values)==1 and "integrationList" in values[0]
 p=base/load
 s=p.read_text()
 anchor=next(x for x in s.splitlines() if "When the user asks for the next or best configured posting time" in x)
 p.write_text(replace_once(s,anchor,anchor+"\n"+values[0],load))
 print("POSTIZ_AGENT_FULL_INTEGRATION_RESULT_SCAN_REBASED")
elif stage==3:
 prompts=additions(hunks(load)[0])
 assert len(prompts)==4 and "YouTube Short" in prompts[0]
 p=base/load
 s=p.read_text()
 anchor=next(x for x in s.splitlines() if "When the user asks for the next or best configured posting time" in x)
 p.write_text(replace_once(s,anchor,anchor+"\n"+"\n".join(prompts),load))
 tool_hunks=hunks(tools)
 assert len(tool_hunks)==2
 imports=additions(tool_hunks[0])
 members=additions(tool_hunks[1])
 assert len(imports)==2 and len(members)==3
 p=base/tools
 s=p.read_text()
 anchor="import { UploadWidgetStatusTool } from '@gitroom/nestjs-libraries/chat/tools/upload.widget.status.tool';"
 s=replace_once(s,anchor,anchor+"\n"+"\n".join(imports),tools)
 anchor="  UploadWidgetStatusTool,"
 s=replace_once(s,anchor,anchor+"\n"+"\n".join(members),tools)
 p.write_text(s)
 print("POSTIZ_AGENT_ANALYTICS_AND_ADAPTIVE_SCHEDULING_REBASED")
elif stage==6:
 fragments=hunks(load)
 assert len(fragments)==4,("EDITORIAL_PROFILE_PATCH_CHANGED",len(fragments))
 imp=additions(fragments[0])
 helper=additions(fragments[1])
 decl=additions(fragments[2])
 editorial=additions(fragments[3])
 assert len(imp)==1 and "readFileSync" in imp[0]
 assert len(helper)>=11 and any("POSTIZ_AGENT_STYLE_PATH" in x for x in helper)
 assert len(decl)==1 and "editorialProfile" in decl[0]
 assert len(editorial)==7 and "editorialProfile" in editorial[-1]
 p=base/load
 s=p.read_text()
 s=replace_once(s,"import dayjs from 'dayjs';",
                "import dayjs from 'dayjs';\n"+imp[0],load)
 s=replace_once(s,"@Injectable()",
                "\n".join(helper)+"\n@Injectable()",load)
 ui="        const ui: string = requestContext.get('ui' as never);"
 s=replace_once(s,ui,ui+"\n"+decl[0],load)
 original=next(x for x in s.splitlines() if "If the user asks you to match or reference another connected account recent style" in x)
 s=replace_once(s,original,"\n".join(editorial),load)
 p.write_text(s)
 print("POSTIZ_AGENT_GENERIC_EXTERNAL_EDITORIAL_PROFILE_REBASED")
else:
 raise RuntimeError("Unexpected agent patch stage "+str(stage))

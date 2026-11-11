#!/usr/bin/env python3
"""Maintain local OpenAI-compatible agent routing without replacing its source.
Only stable provider and model expressions are changed; current prompt stays.
"""
from pathlib import Path
import sys,re
base=Path(sys.argv[1])
path=base/"libraries/nestjs-libraries/src/chat/load.tools.service.ts"
s=path.read_text()
old="import { openai } from '@ai-sdk/openai';"
new="import { createOpenAI } from '@ai-sdk/openai';"
assert s.count(old)==1,("UPSTREAM_LLM_IMPORT_CHANGED",s.count(old))
s=s.replace(old,new,1)
marker="export const AgentState = object({"
assert s.count(marker)==1,("UPSTREAM_AGENT_STATE_CHANGED",s.count(marker))
provider="""const postizLlm = createOpenAI({
  apiKey:
    process.env.POSTIZ_LLM_API_KEY ||
    process.env.OPENAI_API_KEY ||
    'sk-proj-',
  ...(process.env.POSTIZ_LLM_BASE_URL
    ? { baseURL: process.env.POSTIZ_LLM_BASE_URL }
    : {}),
});
const postizLlmModel = process.env.POSTIZ_LLM_MODEL || 'gpt-5.2';

"""
assert 'const postizLlm =' not in s
s=s.replace(marker,provider+marker,1)
original="model: openai('gpt-5.2'),"
assert s.count(original)==1,("UPSTREAM_AGENT_MODEL_CHANGED",s.count(original))
s=s.replace(original,'model: postizLlm.chat(postizLlmModel),',1)
assert 'POSTIZ_AGENT_STYLE_PATH' in s,("EDITORIAL_PROFILE_LOST",str(path))
assert 'TranscribeLocalMediaTool' in (base/"libraries/nestjs-libraries/src/chat/tools/tool.list.ts").read_text()
path.write_text(s)
print("POSTIZ_OMNIROUTE_COMPAT_LLM_MODEL_REBASED_WITH_EDITORIAL_PROFILE_PRESERVED",flush=True)

#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const args=process.argv.slice(2);
assert.equal(args.length,1,'Pass the upstream Postiz checkout');
const src=fs.readFileSync(path.join(args[0],'libraries/nestjs-libraries/src/integrations/social/youtube.provider.ts'),'utf8');
const prefix='  private youtubeFirstPartyUploadPath(input: string): string | null {';
const suffix='  private async youtubeMediaSize(path: string): Promise<number> {';
const start=src.indexOf(prefix),end=src.indexOf(suffix,start);
assert(start>=0&&end>start,'Expected patched first-party helper');
assert(src.includes('getSsrfSafeDispatcher()'),'SSRF default must stay active');
assert(src.includes('const local = this.youtubeFirstPartyUploadPath(path);'),'Both size/chunk methods use helper');
assert(src.split('const local = this.youtubeFirstPartyUploadPath(path);').length===3);
let helper=src.slice(start,end);
helper=helper.replace(prefix,'  youtubeFirstPartyUploadPath(input) {')
 .replace('let source: URL;','let source;')
 .replace('let frontend: URL;','let frontend;')
 .replace('let local: string;','let local;');
assert(!/:\s*(?:URL|string\s*\|\s*null)\b/.test(helper),'Unexpected TS type annotation');
class BadBody extends Error {constructor(_provider,_body,_payload,message){super(message)}}
const root=fs.mkdtempSync(path.join(os.tmpdir(),'postiz-firstparty-'));
try{
 const base=path.join(root,'uploads');
 fs.mkdirSync(path.join(base,'2026','11','10'),{recursive:true});
 const file=path.join(base,'2026','11','10','test.mp4');
 fs.writeFileSync(file,Buffer.from([0,1,2,3,4,5]));
 const outside=path.join(root,'outside.mp4');fs.writeFileSync(outside,Buffer.from([3]));
 fs.symlinkSync(outside,path.join(base,'escape.mp4'));
 const config={env:{FRONTEND_URL:'https://example.test',UPLOAD_DIRECTORY:base}};
 const Ctor=new Function('realpathSync','resolve','sep','statSync','BadBody','process',
   'return class Test { constructor(){this.identifier="youtube"}\n'+helper+'\n}')(
   fs.realpathSync,path.resolve,path.sep,fs.statSync,BadBody,config);
 const inst=new Ctor();
 const own='https://example.test/uploads/2026/11/10/test.mp4';
 assert.equal(inst.youtubeFirstPartyUploadPath(own),fs.realpathSync(file));
 for(const url of [
  'https://elsewhere.test/uploads/2026/11/10/test.mp4',
  'https://example.test/not-uploads/test.mp4',
  'https://example.test/uploads/2026/11/10/test.mp4?token=1',
  'https://user:pass@example.test/uploads/2026/11/10/test.mp4',
  'https://example.test/uploads/%2e%2e/outside.mp4'
 ]) assert.equal(inst.youtubeFirstPartyUploadPath(url),null,'Never map external or abnormal URL: '+url);
 assert.throws(()=>inst.youtubeFirstPartyUploadPath('https://example.test/uploads/escape.mp4'),BadBody);
 assert.throws(()=>inst.youtubeFirstPartyUploadPath('https://example.test/uploads/missing.mp4'),BadBody);
 assert.throws(()=>inst.youtubeFirstPartyUploadPath('https://example.test/uploads/%2fetc%2fpasswd'),BadBody);
 assert.throws(()=>inst.youtubeFirstPartyUploadPath('https://example.test/uploads/%00oops'),BadBody);
 assert.throws(()=>inst.youtubeFirstPartyUploadPath('https://example.test/uploads/%5Ctmp'),BadBody);
 assert.equal(config.env.UPLOAD_DIRECTORY,base);
 console.log('PASS: exact own-origin media mapped locally; external URLs remain guarded; traversal, symlink, missing files, encoded separators rejected');
}finally{fs.rmSync(root,{recursive:true,force:true})}

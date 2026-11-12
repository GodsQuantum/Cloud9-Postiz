#!/usr/bin/env python3
from pathlib import Path
import subprocess,re,hashlib,json,xml.etree.ElementTree as ET
base=Path(__file__).resolve().parent.parent
files=subprocess.check_output(['git','-C',str(base),'ls-files','-z']).decode().split(chr(0))
deny=[re.compile(v,re.I) for v in ['a'+'rezki','chou'+'gar','kech'+'idi','fe'+'lla',
 'arezkisugar',r'arezkichougar[.]com',r'home[.]arpa',
 r'@gmail[.]com',r'@hotmail[.]com',r'192[.]168[.](?!0[.]0/16)',
 r'-----BEGIN PRIVATE KEY',r'github_pat_[A-Za-z0-9_]{25,}',r'ghp_[A-Za-z0-9]{25,}',
 r'sk-[a-zA-Z0-9_-]{32,}',r'/home/'+'arezki',r'/srv/lxc']]
failed=[]
for name in files:
 if not name or name=='tests/privacy.py':continue
 file=base/name
 if not file.is_file() or file.stat().st_size>500000:continue
 if any(x.search(file.read_text(errors='replace')) for x in deny):failed.append(name)
assert not failed,('PUBLIC_SOURCE_PERSONAL_DATA_DETECTED',failed)
actual={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (base/'patches').glob('*.patch')}
expected=json.loads((base/'tests/patch-sha256.json').read_text())
assert len(actual)==len(expected)==8 and actual==expected
assert not any('reel-cover' in n or 'cover-frame' in n for n in actual)
assert all((base/n).is_file() for n in ['README.md','README.fr.md','README.zh-CN.md','LICENSE'])
assert 'GNU AFFERO GENERAL PUBLIC LICENSE' in (base/'LICENSE').read_text()
ET.parse(base/'docs/logo.svg');ET.parse(base/'docs/architecture.svg')
print('POSTIZ_PUBLIC_EIGHT_PATCHES_PRIVACY_LICENSE_TRANSLATIONS_DIAGRAMS_PASS')

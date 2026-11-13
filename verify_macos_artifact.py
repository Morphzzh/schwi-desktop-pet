"""Validate packaged Mac artifacts and write a path-free public test summary."""
import argparse,hashlib,json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--packages',type=Path,required=True)
parser.add_argument('--evidence',type=Path,required=True)
parser.add_argument('--arch',choices=['arm64','x86_64'],required=True)
parser.add_argument('--commit',required=True)
parser.add_argument('--run',required=True)
args=parser.parse_args()
build=json.loads((args.packages/'build-info.json').read_text(encoding='utf-8'))
assert build['version']=='1.0.3' and build['arch']==args.arch
stages=[]
for name in ['qa-macos','qa-macos-dmg','qa-macos-extracted']:
    root=args.evidence/name
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    gui=json.loads((root/'gui/smoke-test.json').read_text(encoding='utf-8'))
    integration=json.loads((root/'integration/packaged-integration.json').read_text(encoding='utf-8'))
    assert report['ok'] and report['arch']==args.arch and report['qt_platform']=='cocoa'
    assert report['ad_hoc_signature_verified']
    assert gui['ok'] and gui['version']=='1.0.3' and gui['machine']==args.arch
    assert len(gui['checks'])>=29 and integration['ok'] and len(integration['checks'])>=4
    stages.append({'stage':name,**report,'integration_checks':len(integration['checks'])})
filename=f'SchwiPet-1.0.3-macOS-{args.arch}.dmg'
dmg=args.packages/filename
digest=hashlib.sha256(dmg.read_bytes()).hexdigest()
expected=(args.packages/(filename+'.sha256')).read_text().split()
assert expected==[digest,filename]
result={'version':'1.0.3','arch':args.arch,'source_commit':args.commit,'workflow_run':args.run,
        'sha256':digest,'build':{k:v for k,v in build.items() if k!='app'},'checks':stages}
workaround=args.evidence/'qa-macos/runner-icon-service.json'
if workaround.exists():result['hosted_runner_workaround']=json.loads(workaround.read_text())
output=args.packages/f'SchwiPet-1.0.3-macOS-{args.arch}-verification.json'
output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':True,'dmg':str(dmg),'sha256':digest,'summary':str(output)}))

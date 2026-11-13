"""Work around actions/runner-images#14751 only inside an ephemeral CI VM."""
import json,os,platform,subprocess,sys
from pathlib import Path

if os.environ.get('GITHUB_ACTIONS')!='true' or sys.platform!='darwin':
    raise SystemExit('This script is only for GitHub-hosted macOS CI; never run it on an end-user computer.')
if platform.machine()!='x86_64' or not platform.mac_ver()[0].startswith('26.'):
    raise SystemExit(0)

service=f'gui/{os.getuid()}/com.apple.iconservices.iconservicesagent'
before=subprocess.run(['/bin/launchctl','print',service],capture_output=True,text=True,timeout=15)
interesting=('state =','successive crashes =','last terminating signal =','last exit code =','active count =')
status=[line.strip() for line in before.stdout.splitlines() if line.strip().startswith(interesting)]
# Hosted Intel macOS 26 can crash-loop this service on its virtual Metal GPU.
# NSWorkspace icon lookup then blocks forever. Unloading it makes the system
# fall back to generic icons; our bundled character artwork/icons are unchanged.
# https://github.com/actions/runner-images/issues/14751
unload=subprocess.run(['/bin/launchctl','bootout',service],capture_output=True,text=True,timeout=20)
disable=subprocess.run(['/bin/launchctl','disable',service],capture_output=True,text=True,timeout=15)
report={'ci_only':True,'issue':'https://github.com/actions/runner-images/issues/14751',
        'os':platform.mac_ver()[0],'arch':platform.machine(),'service':service,
        'status_before':status,'bootout_returncode':unload.returncode,
        'disable_returncode':disable.returncode,'disable_error':disable.stderr}
out=Path('qa-macos');out.mkdir(exist_ok=True)
(out/'runner-icon-service.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
assert disable.returncode==0,disable.stderr

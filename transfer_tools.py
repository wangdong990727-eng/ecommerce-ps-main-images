"""Portable package verification, safe installation and non-Photoshop checks."""
from pathlib import Path
import argparse, ast, datetime, hashlib, json, os, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parent
NAME = 'ecommerce-ps-main-images'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def verify():
    m = json.loads((ROOT/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    failures = []
    for name, expected in m['files'].items():
        p = (ROOT/name).resolve()
        if not p.is_relative_to(ROOT) or not p.is_file() or sha(p) != expected:
            failures.append(name)
    if failures:
        raise ValueError('Missing or modified package files: ' + ', '.join(failures))
    return {'status':'PASS', 'files':len(m['files']), 'version':m['version'],
            'meaning':'File integrity only; not visual acceptance or remote Photoshop verification.'}

def tree(p):
    return {f.relative_to(p).as_posix():sha(f) for f in p.rglob('*')
            if f.is_file() and '__pycache__' not in f.parts and f.suffix != '.pyc'}

def install(args):
    verify()
    skill_root = args.skills_root.expanduser().absolute()
    target = skill_root/NAME
    source = ROOT/NAME
    if target.exists() and tree(target) == tree(source):
        return {'status':'UNCHANGED','target':str(target)}
    if not args.apply:
        return {'status':'DRY_RUN','source':str(source),'target':str(target),
                'exists':target.exists(),'next':'Use --apply; add --replace only to back up and replace an existing different version.'}
    # Only this named skill may be replaced. Never alter global configuration.
    skill_root.mkdir(parents=True, exist_ok=True)
    if target.parent.resolve() != skill_root.resolve() or target.name != NAME:
        raise ValueError('Unexpected target path')
    if target.exists():
        if not args.replace:
            raise ValueError('Different skill already exists. No change. Review it, then use --apply --replace if intended.')
        is_link = target.is_symlink() or (hasattr(target,'is_junction') and target.is_junction())
        if is_link or target.resolve() != target.parent.resolve()/target.name:
            raise ValueError('Existing skill is a symlink/junction. No change. Ask the target assistant to back up and detach only this link first.')
        backup_root = skill_root.parent/'skill-transfer-backups'
        backup_root.mkdir(exist_ok=True)
        backup = backup_root/(NAME+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        if backup.parent.resolve() != backup_root.resolve() or backup.exists():
            raise ValueError('Unexpected backup target')
        target.rename(backup)
    else:
        backup = None
    try:
        shutil.copytree(source,target)
        if tree(target) != tree(source):
            raise ValueError('Installed file hashes differ; preserve both copies for inspection.')
    except Exception as exc:
        raise RuntimeError('Install failed. Previous version preserved at '+str(backup)+': '+str(exc)) from exc
    return {'status':'INSTALLED','target':str(target),'backup':str(backup) if backup else None,
            'next':'Open a new assistant chat, read SKILL.md and verify its version; actual Photoshop and product tests remain unrun.'}

def selftest(args):
    verify()
    skill = ROOT/NAME
    for f in skill.rglob('*.py'):
        ast.parse(f.read_text(encoding='utf-8-sig'), filename=str(f))
    for f in skill.rglob('*.json'):
        json.loads(f.read_text(encoding='utf-8-sig'))
    # Check only local Markdown file links, excluding internet and anchors.
    missing = []
    for f in skill.rglob('*.md'):
        import re
        for dest in re.findall(r'\]\(([^)]+)\)',f.read_text(encoding='utf-8')):
            if '://' in dest or dest.startswith('#'):
                continue
            path = dest.split('#')[0]
            if path and not (f.parent/path).exists():
                missing.append(str(f.relative_to(ROOT))+': '+dest)
    if missing:
        raise ValueError('Broken local references: '+repr(missing))
    out = args.output.expanduser().absolute()
    if out.exists():
        raise ValueError('Use a NEW selftest output directory; old evidence is never overwritten.')
    out.mkdir(parents=True)
    results=[]
    commands=[
        [sys.executable,str(skill/'scripts/project_tools.py'),'preflight','--out',str(out/'preflight.json')],
        [sys.executable,str(skill/'scripts/project_tools.py'),'init',str(out/'demo-project')],
        [sys.executable,str(skill/'scripts/render_layout.py'),str(skill/'templates/layout-spec.example.json'),
         '--out',str(out/'demo-layout.jsx'),'--output-dir',str(out/'rendered-demo')],
    ]
    for i,cmd in enumerate(commands):
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8',errors='replace',env={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'})
        (out/('command-'+str(i)+'.txt')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
        results.append({'step':i,'returncode':p.returncode})
        if p.returncode:
            raise RuntimeError('Selftest failed at step '+str(i)+'; inspect '+str(out))
    result={'technical_checks':'PASS','steps':results,'photoshop_executed':False,
            'product_visual_review':'NOT_RUN','other_machine_verified':False,
            'note':'Compiled JSX contains paths resolved on this machine. On the other machine run selftest again; never reuse this generated JSX.'}
    (out/'selftest-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('verify')
    s=sub.add_parser('selftest');s.add_argument('--output',type=Path,required=True)
    i=sub.add_parser('install');i.add_argument('--skills-root',type=Path,required=True)
    i.add_argument('--apply',action='store_true');i.add_argument('--replace',action='store_true')
    args=p.parse_args()
    try:
        result=verify() if args.command=='verify' else selftest(args) if args.command=='selftest' else install(args)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except Exception as exc:
        print(json.dumps({'status':'FAIL','error':str(exc)},ensure_ascii=False),file=sys.stderr);return 1
if __name__=='__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Inventory BEHZAD_AI project files and produce a report; does not modify source files."""
from pathlib import Path
import json, re, subprocess, datetime

ROOT = Path('/storage/emulated/0/BEHZAD_AI')
OUT = ROOT / 'reports'
OUT.mkdir(parents=True, exist_ok=True)
SKIP_DIRS = {'.git', '__pycache__', '.venv', 'venv', 'node_modules'}
PY_EXTS = {'.py'}
PATTERNS = {
 'todo': re.compile(r'\b(TODO|FIXME|XXX|HACK|NotImplemented)\b', re.I),
 'stub': re.compile(r'^\s*(pass\s*$|raise NotImplementedError|\.\.\.\s*$)', re.M),
 'empty_function': re.compile(r'^\s*def\s+\w+\([^)]*\)\s*:\s*\n\s*(pass|\.\.\.)\s*$', re.M),
}
def git(args):
    try:
        return subprocess.check_output(['git', *args], cwd=ROOT, stderr=subprocess.STDOUT, text=True, timeout=15).strip()
    except Exception as e:
        return f'(git unavailable: {e})'
def main():
    if not ROOT.exists():
        print(f'Project directory not found: {ROOT}'); return
    files=[]; findings=[]
    for p in ROOT.rglob('*'):
        if any(part in SKIP_DIRS for part in p.parts): continue
        if p.is_file():
            rel=str(p.relative_to(ROOT)); files.append({'path':rel,'bytes':p.stat().st_size})
            if p.suffix in PY_EXTS:
                try: src=p.read_text(encoding='utf-8', errors='replace')
                except Exception as e: src=''; findings.append({'file':rel,'kind':'read_error','detail':str(e)})
                for kind,pat in PATTERNS.items():
                    for m in pat.finditer(src):
                        line=src.count('\n',0,m.start())+1
                        findings.append({'file':rel,'line':line,'kind':kind,'detail':m.group(0).strip()[:180]})
                # Lightweight syntax check without importing/executing project code
                try: compile(src, rel, 'exec')
                except SyntaxError as e: findings.append({'file':rel,'line':e.lineno,'kind':'syntax_error','detail':e.msg})
    files.sort(key=lambda x:x['path'])
    report={'generated_at':datetime.datetime.now().isoformat(timespec='seconds'),'root':str(ROOT),
      'file_count':len(files),'python_count':sum(Path(x['path']).suffix=='.py' for x in files),
      'files':files,'findings':findings,
      'git_status':git(['status','--short']), 'git_branch':git(['branch','--show-current']),
      'git_remote':git(['remote','-v']), 'git_last_commit':git(['log','-1','--oneline'])}
    json_path=OUT/'project_inventory.json'; txt_path=OUT/'project_inventory.txt'
    json_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=[f"BEHZAD_AI inventory — {report['generated_at']}",f"Root: {ROOT}",f"Files: {report['file_count']} | Python: {report['python_count']}","",'GIT STATUS:',report['git_status'],'','BRANCH:',report['git_branch'],'','REMOTE:',report['git_remote'],'','LAST COMMIT:',report['git_last_commit'],'','FILES:']
    lines += [f"{x['path']} ({x['bytes']} bytes)" for x in files]
    lines += ['',f'FINDINGS ({len(findings)}):']
    lines += [f"{x.get('file')}:{x.get('line','?')} [{x['kind']}] {x['detail']}" for x in findings]
    txt_path.write_text('\n'.join(lines),encoding='utf-8')
    print('\n'.join(lines[:30])); print(f'\nFull reports saved:\n{txt_path}\n{json_path}')
if __name__=='__main__': main()

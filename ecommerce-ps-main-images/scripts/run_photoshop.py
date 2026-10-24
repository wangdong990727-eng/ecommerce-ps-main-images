"""Execute a task JSX through existing Windows Photoshop COM support.

Requires an already installed pywin32. No installation, account changes,
Photoshop restart or app quit. The JSX owns document safety and outputs.
"""
import argparse
import json
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jsx', type=Path)
    parser.add_argument('--status', type=Path, help='Expected NEW JSON status file from render_layout output')
    args = parser.parse_args()
    script = args.jsx.resolve()
    if not script.is_file() or script.suffix.lower() != '.jsx':
        parser.error('Pass an existing task .jsx file.')
    if args.status and args.status.exists():
        parser.error('Status file already exists; use a new render version, do not reuse stale status.')
    if os.name != 'nt':
        parser.error('This optional launcher is Windows-only. Use the current host Photoshop control or File > Scripts > Browse.')
    try:
        import win32com.client
    except ImportError:
        parser.error('pywin32 is not installed. No dependencies were installed. Use an existing compatible interpreter or Photoshop File > Scripts > Browse.')
    try:
        app = win32com.client.Dispatch('Photoshop.Application')
        print(json.dumps({'status':'running','photoshop_version':str(app.Version),'script':str(script)}),flush=True)
        app.DoJavaScriptFile(str(script))
        if not args.status:
            print(json.dumps({'status':'invoked','verification':'not_requested','note':'Invocation is not a completion check. Inspect the JSX output log.'}))
            return 0
        record = json.loads(args.status.read_text(encoding='utf-8-sig'))
        print(json.dumps(record,ensure_ascii=False))
        return 0 if record.get('status') == 'complete' else 1
    except Exception as exc:
        print(json.dumps({'status':'error','message':str(exc),'next':'Read the last task status and Photoshop dialog before retrying; no automatic restart performed.'},ensure_ascii=False),file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

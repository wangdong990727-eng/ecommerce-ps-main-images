"""Compile (do not execute) a native multi-colour PSD build or ID-based export job."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def relative_file(root, value):
    if not isinstance(value, str) or not value or ':' in value or value.startswith(('/', '\\')):
        raise ValueError('Source paths must be relative to the config directory')
    if '..' in value.replace('\\', '/').split('/'):
        raise ValueError('Parent traversal is not allowed')
    path = (root / value).resolve(strict=True)
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Source escapes config directory or is not a file')
    return path


def compile_job(config, output, operation):
    config = Path(config).resolve(strict=True)
    data = json.loads(config.read_text(encoding='utf-8-sig'))
    variants = data.get('variants', [])
    if not variants or not isinstance(variants, list):
        raise ValueError('At least one explicit colour variant is required')
    ids = []
    for v in variants:
        ident = v.get('id', '')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,48}', ident) or ident in ids:
            raise ValueError('Variant IDs must be unique safe ASCII names')
        ids.append(ident)
        if operation == 'build':
            source = relative_file(config.parent, v.get('source_psd'))
            if source.suffix.lower() != '.psd':
                raise ValueError('Initial shared build supports PSD inputs only')
            v['source_path'] = str(source)
            v['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        else:
            if not isinstance(v.get('group_id'), int) or isinstance(v.get('group_id'), bool) or v['group_id'] <= 0:
                raise ValueError('Export requires an inspected stable positive group_id for each colour')
        for key in ('min_text_layers', 'min_smart_objects'):
            v.setdefault(key, 1)
            if not isinstance(v[key], int) or isinstance(v[key], bool) or v[key] < 0:
                raise ValueError('Native layer minimums must be non-negative integers')
    if operation == 'export':
        if len({v['group_id'] for v in variants}) != len(variants):
            raise ValueError('Duplicate group IDs')
        source = relative_file(config.parent, data.get('source_psd'))
        if source.suffix.lower() not in ('.psd', '.psb'):
            raise ValueError('Shared export input must be PSD/PSB')
        data['source_path'] = str(source)
    initial = data.get('initial_visible', ids[0])
    if initial not in ids:
        raise ValueError('initial_visible must identify exactly one declared variant')
    out = Path(output).absolute()
    if out.exists():
        raise ValueError('Output job directory exists; choose a new version')
    out.mkdir(parents=True)
    data.update(operation=operation, output_dir=str(out), initial_visible=initial)
    here = Path(__file__).resolve().parent
    helpers = (here/'photoshop_helpers.jsxinc').read_text(encoding='utf-8-sig')
    engine = (here/'variant_engine.jsxinc').read_text(encoding='utf-8-sig')
    script = out/'run.jsx'
    script.write_text('#target photoshop\n'+helpers+'\n'+engine+'\nEV.run('+json.dumps(data, ensure_ascii=True)+');\n', encoding='utf-8-sig')
    (out/'compiled-job.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'jsx': str(script), 'status_file': str(out/'status.json'), 'photoshop_executed': False,
            'operation': operation, 'variants': ids}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=('build', 'export')); p.add_argument('config'); p.add_argument('--out', required=True)
    a = p.parse_args()
    try:
        print(json.dumps(compile_job(a.config, a.out, a.operation), ensure_ascii=False, indent=2)); return 0
    except Exception as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())

"""Snapshot sources, compare protected pixels and make review thumbnails.

No Photoshop control, generation, approval changes or automatic registration.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def new_output(path):
    path = Path(path)
    if path.exists():
        raise ValueError('Output exists; choose a new version: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write(path, data):
    new_output(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def snapshot(source, output):
    source = Path(source).resolve(strict=True)
    if not source.is_file():
        raise ValueError('Snapshot requires one actual file')
    output = Path(output).absolute()
    if output.exists():
        raise ValueError('Snapshot directory exists; never overwrite a snapshot')
    # The original file is not opened in Photoshop, saved, renamed or changed.
    output.mkdir(parents=True)
    target = output / source.name
    before = digest(source)
    shutil.copy2(source, target)
    if digest(target) != before or digest(source) != before:
        raise ValueError('Snapshot hash mismatch; preserve both files for inspection')
    result = {'source': str(source), 'copy': source.name, 'sha256': before,
              'meaning': 'Exact file snapshot only; visual/native-layer tests not performed.'}
    write(output / 'snapshot.json', result)
    return result


def protected_diff(master, candidate, mask, out, tolerance=0):
    from PIL import Image, ImageChops, ImageOps
    if not 0 <= tolerance <= 255:
        raise ValueError('Tolerance must be 0..255')
    master, candidate, mask = map(Path, (master, candidate, mask))
    # JPEG recompression confounds exact pixel protection. Use aligned PNG exports.
    for path in (master, candidate, mask):
        with Image.open(path) as image:
            if image.format != 'PNG':
                raise ValueError('Diff inputs must be aligned PNG files')
    with Image.open(master) as source:
        a = source.convert('RGBA')
    with Image.open(candidate) as source:
        b = source.convert('RGBA')
    with Image.open(mask) as source:
        m = source.copy()
    if a.size != b.size or a.size != m.size:
        raise ValueError('Canvas mismatch; no automatic resize, registration or crop')
    if m.mode not in ('1', 'L'):
        raise ValueError('Mask must be grayscale L/1, not RGB/RGBA')
    mask_l = m.convert('L')
    mask_histogram = mask_l.histogram()
    if any(mask_histogram[1:255]):
        raise ValueError('Mask must be binary: WHITE=allowed edit, BLACK=protected')
    protected = mask_histogram[0]
    if not protected:
        raise ValueError('No protected pixels; an all-white mask cannot prove protection')
    channels = ImageChops.difference(a, b).split()
    maximum = channels[0]
    for channel in channels[1:]:
        maximum = ImageChops.lighter(maximum, channel)
    protected_delta = ImageChops.multiply(maximum, ImageOps.invert(mask_l))
    histogram = protected_delta.histogram()
    changed = sum(histogram[tolerance+1:])
    max_delta = max(i for i, count in enumerate(histogram) if count)
    result = {'result': 'PASS' if changed == 0 else 'FAIL', 'protected_pixels': protected,
              'changed_protected_pixels': changed, 'max_channel_delta': max_delta,
              'tolerance': tolerance, 'size': a.size,
              'inputs': {str(p): digest(p) for p in (master, candidate, mask)},
              'meaning': 'Protected pixel invariance only; not person/product/wear acceptance.'}
    write(out, result)
    return result


def thumbnail(source, out, width=200):
    from PIL import Image, ImageOps
    if width < 1 or width > 1000:
        raise ValueError('Thumbnail width must be 1..1000')
    target = new_output(out)
    if target.suffix.lower() != '.png':
        raise ValueError('Review thumbnail output must be PNG')
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert('RGBA')
        height = max(1, round(image.height * width / image.width))
        image.resize((width, height), Image.Resampling.LANCZOS).save(target)
    return {'thumbnail': str(target), 'size': [width, height], 'review': 'NOT_RUN'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('snapshot'); s.add_argument('source'); s.add_argument('--out', required=True)
    d = sub.add_parser('protected-diff')
    for name in ('master', 'candidate', 'mask'): d.add_argument(name)
    d.add_argument('--out', required=True); d.add_argument('--tolerance', type=int, default=0)
    t = sub.add_parser('thumbnail'); t.add_argument('source'); t.add_argument('--out', required=True)
    t.add_argument('--width', type=int, default=200)
    a = p.parse_args()
    try:
        if a.command == 'snapshot': result = snapshot(a.source, a.out)
        elif a.command == 'protected-diff': result = protected_diff(a.master, a.candidate, a.mask, a.out, a.tolerance)
        else: result = thumbnail(a.source, a.out, a.width)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('result') == 'FAIL' else 0
    except Exception as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())

"""Deterministic outline SVG examples. Labels stay separate for native PS text."""
import argparse, html, json, re, sys
from pathlib import Path

SYMBOLS = {
 'keep_warm': '<path d="M67 30C69 48 87 51 85 70C84 85 74 94 62 94C47 94 39 85 40 72C41 62 48 55 52 50C51 64 54 65 57 68C66 61 62 45 67 30Z"/>',
 'anti_slip_palm': '<path d="M48 95L44 83L33 66Q30 60 35 58Q39 56 47 68L47 41Q47 34 53 34Q58 34 58 41L58 60L58 31Q58 25 64 25Q70 25 70 31L70 60L70 35Q70 29 76 29Q82 29 82 35L82 62L82 45Q82 39 87 39Q92 39 92 45L92 73Q92 87 82 95Z"/><circle cx="60" cy="74" r="1.5"/><circle cx="70" cy="74" r="1.5"/><circle cx="80" cy="74" r="1.5"/><circle cx="60" cy="84" r="1.5"/><circle cx="70" cy="84" r="1.5"/><circle cx="80" cy="84" r="1.5"/>',
 'touchscreen': '<rect x="35" y="25" width="45" height="70" rx="6"/><path d="M51 32H64M53 87H62M98 93L88 75L77 65Q73 61 70 65Q68 67 72 73L76 79M87 66Q96 66 99 74M85 57Q103 57 107 72"/>',
 'water_resistant': '<path d="M64 27C58 42 40 56 40 72C40 88 50 97 64 97C78 97 88 88 88 72C88 56 70 42 64 27Z"/><path d="M49 73Q49 85 61 88"/>',
 'windproof': '<path d="M29 48H83Q100 48 98 36Q95 25 84 30M27 63H96Q108 63 107 52M36 78H78Q94 78 93 90Q91 102 80 98"/>',
 'fleece_lined': '<path d="M37 43Q34 31 46 33Q51 23 60 32Q70 23 77 33Q91 29 89 43Q102 49 91 58Q98 70 86 74Q89 89 75 87Q66 102 57 89Q43 98 40 84Q25 85 32 70Q20 61 31 53Q23 43 37 43Z"/><path d="M49 52Q62 42 76 51M45 66Q60 57 82 65M50 79Q62 71 76 78"/>',
 'stretch_cuff': '<path d="M40 42H88V86H40ZM48 42V86M58 42V86M69 42V86M80 42V86M15 64H33M21 58L15 64L21 70M95 64H113M107 58L113 64L107 70"/>',
 'machine_washable': '<path d="M28 48L36 88H92L100 48M32 59Q43 51 54 59Q65 67 76 59Q87 51 98 59M45 29V42M64 25V40M83 29V42"/>',
}

def build(spec, output, demo=False):
    spec=Path(spec).resolve();data=json.loads(spec.read_text(encoding='utf-8-sig'))
    style=data['style'];colour=style['color'];stroke=style['stroke'];radius=style['corner_radius']
    if not re.fullmatch(r'#[0-9A-Fa-f]{6}',colour):raise ValueError('Use #RRGGBB')
    if isinstance(stroke,bool) or not isinstance(stroke,(int,float)) or not 1<=stroke<=8:raise ValueError('Stroke must be 1..8 design units')
    if isinstance(radius,bool) or not isinstance(radius,(int,float)) or not 0<=radius<=32:raise ValueError('Radius must be 0..32 design units')
    entries=data['features'];ids=[]
    for item in entries:
        ident=item['id']
        if ident not in SYMBOLS or ident in ids:raise ValueError('Unsupported or duplicate feature')
        ids.append(ident)
        if not demo:
            value=item.get('fact_source','');source=(spec.parent/value).resolve()
            if not value or ':' in value or '..' in Path(value).parts or not source.is_relative_to(spec.parent) or not source.is_file():
                raise ValueError('Actual product use requires an existing local fact_source per feature; this still needs semantic review')
    out=Path(output)
    if out.exists():raise ValueError('Output exists; choose a new version')
    out.mkdir(parents=True)
    cards=[]
    for item in entries:
        ident=item['id'];title=html.escape(item['label'])
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128" role="img"><title>{title}</title><g fill="none" stroke="{colour}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="8" width="112" height="112" rx="{radius}"/>{SYMBOLS[ident]}</g></svg>'
        (out/(ident+'.svg')).write_text(svg,encoding='utf-8')
        cards.append('<figure><img src="'+ident+'.svg"><figcaption>'+title+'</figcaption></figure>')
    (out/'preview.html').write_text('<!doctype html><html lang="en" translate="no"><meta name="google" content="notranslate"><meta charset="utf-8"><title>Outline icon review</title><style>body{font:16px sans-serif;background:#f7f5f0;padding:30px}main{display:flex;flex-wrap:wrap;gap:24px}figure{margin:0;padding:20px;background:white;text-align:center;width:190px}img{width:160px;height:160px}figcaption{margin-top:15px}</style><h1>'+('DEMO — not product claims' if demo else 'Icons — product facts and visual review still required')+'</h1><main class="notranslate" translate="no">'+''.join(cards)+'</main></html>',encoding='utf-8')
    result={'demo_only':demo,'style':style,'features':entries,'labels':'Separate native PS text; no advertising text rasterized into SVG','visual_review':'NOT_RUN','copyright_guarantee':False}
    (out/'icons.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('spec');p.add_argument('--out',required=True);p.add_argument('--demo',action='store_true');a=p.parse_args()
    try:print(json.dumps(build(a.spec,a.out,a.demo),ensure_ascii=False));raise SystemExit(0)
    except Exception as e:print(str(e),file=sys.stderr);raise SystemExit(2)

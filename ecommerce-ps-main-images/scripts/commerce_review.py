"""Non-exhaustive production-policy hints; never a legal or visual verdict."""
import json
import re
import unicodedata
from pathlib import Path


def load_rules():
    return json.loads((Path(__file__).resolve().parent.parent / 'references/commerce-rules.json').read_text(encoding='utf-8-sig'))


def normalize(text):
    value = unicodedata.normalize('NFKC', text)
    value = re.sub(r'[\u200b-\u200f\ufeff]', '', value)
    return re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', value)


def resolve_platform(value, rules=None):
    rules = rules or load_rules()
    if not isinstance(value, str):
        return None
    value = value.strip().casefold()
    for key, aliases in rules['platforms'].items():
        if value == key or value in [x.casefold() for x in aliases]:
            return key
    return None


def scan_text(text, platform=None, rules=None):
    rules = rules or load_rules()
    value = normalize(text)
    findings = []
    for rule in rules['rules']:
        matches = sorted({m.group() for m in re.finditer(rule['pattern'], value, re.I)})
        if matches:
            finding = {k: rule[k] for k in ['id', 'severity', 'basis', 'action']} | {'matches': matches}
            if rule['id'] == 'absolute_marketing' and all(m in {'最大', '最小', '最高', '最低'} for m in matches):
                spec_terms = re.findall(r'(最大|最小|最高|最低)(?:使用温度|保存温度|适用温度|适用头围|头围|尺寸|长度|宽度|高度|温度|承重|载重|容量|尺码|耐温)\s*[：:]?\s*[≤≥<>]?\s*\d', value)
                if set(matches).issubset(set(spec_terms)):
                    finding.update(severity='context_review', action='Possible factual specification limit: verify source and keep the value. Prefer a clear numeric limit without a marketing superlative; this is not automatically an illegal claim.')
            findings.append(finding)
    for key, aliases in rules['platforms'].items():
        if key == platform:
            continue
        matches = []
        for alias in aliases:
            pattern = re.escape(alias)
            if alias.isascii():
                pattern = r'(?<![a-z0-9])' + pattern + r'(?![a-z0-9])'
            if re.search(pattern, value, re.I):
                matches.append(alias)
        if matches:
            findings.append({'id': 'external_platform' if platform else 'platform_mention',
                             'severity': 'context_review', 'basis': 'user_cross_platform_policy',
                             'platform': key, 'matches': matches,
                             'action': 'No other-platform promotion or trade routing in production copy; verify context and actual target. A mention is not automatically an official-policy violation.'})
    return findings

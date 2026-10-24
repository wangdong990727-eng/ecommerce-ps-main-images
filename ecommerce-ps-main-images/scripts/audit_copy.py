#!/usr/bin/env python3
"""Read-only text inventory and ledger/layout/render consistency checks.

This is a review aid, not a semantic, product, legal or visual validator.
Only the explicitly requested output file is written.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from commerce_review import load_rules, resolve_platform, scan_text


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalized(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def audit(project, selected=None, platform=None):
    root = project.parent
    state = read(project)
    rules = load_rules()
    raw_platform = platform or state.get('platform') or state.get('scope', {}).get('platform')
    target_platform = resolve_platform(raw_platform, rules)
    results = []
    errors = []
    found = set()
    for page in state.get("pages", []):
        pid = page["id"]
        if selected and pid not in selected:
            continue
        found.add(pid)
        layout_path = root / page["layout"]
        layout = read(layout_path)
        text_layers = [x for x in layout["layers"] if x["type"] == "text"]
        ledger = page.get("copy", [])
        issues = []
        for label, rows in (("layout", text_layers), ("ledger", ledger)):
            ids = [x["id"] for x in rows]
            if len(ids) != len(set(ids)):
                issues.append({"type": "duplicate_id", "source": label})
        recorded = {x["id"]: x for x in ledger}
        planned = {x["id"]: x for x in text_layers}
        for tid in sorted(set(recorded) - set(planned)):
            issues.append({"type": "ledger_without_layout", "id": tid})
        evidence_path = None
        preview = page.get("preview")
        if preview:
            evidence_path = (root / preview).parent.parent / (layout["job_id"] + ".layers.json")
        rendered = []
        if evidence_path and evidence_path.is_file():
            evidence = read(evidence_path)
            rendered = [x for x in evidence.get("layers", []) if "text" in x and x.get("visible", True)]
            if evidence.get("job_id") != layout["job_id"]:
                issues.append({"type": "render_job_mismatch"})
            built_layout = evidence.get("build_sources", {}).get("layout", {})
            if built_layout.get("sha256") and built_layout["sha256"] != hashlib.sha256(layout_path.read_bytes()).hexdigest():
                issues.append({"type": "layout_changed_since_render"})
        inventory = []
        for layer in text_layers:
            tid = layer["id"]
            item = recorded.get(tid)
            if item is None:
                issues.append({"type": "unrecorded_text", "id": tid})
            elif normalized(item.get("final_text", "")) != normalized(layer["text"]):
                issues.append({"type": "ledger_layout_mismatch", "id": tid})
            matches = [x for x in rendered if x.get("name", "").split(" | ", 1)[0] == tid]
            if evidence_path and evidence_path.is_file():
                if len(matches) != 1:
                    issues.append({"type": "render_text_count", "id": tid, "count": len(matches)})
                elif normalized(matches[0]["text"]) != normalized(layer["text"]):
                    issues.append({"type": "stale_render_text", "id": tid})
            text = layer["text"]
            hints = []
            if re.search(r"恒温|蓄热|内热循环|升温|cyclic\s+warming|self[- ]heating|constant\s+temperature", text, re.I):
                hints.append("mechanism_or_performance: check source and linked languages/icons; not an automatic rejection")
            if re.search(r"\d+(?:\.\d+)?\s*(?:cm|mm|厘米|毫米)", text, re.I):
                hints.append("measurement: visually verify measured object, direction, endpoints and source")
            inventory.append({"id": tid, "text": text,
                              "reference_text": item.get("reference_text") if item else None,
                              "fact_sources": item.get("fact_sources", []) if item else [],
                              "hints": hints, "rendered": matches,
                              "commerce_findings": scan_text(text, target_platform, rules)})
        for row in rendered:
            if row.get("name", "").split(" | ", 1)[0] not in planned:
                issues.append({"type": "extra_rendered_text", "name": row.get("name"), "text": row["text"]})
        decorative = []
        if evidence_path and evidence_path.is_file():
            decorative = [{k: x[k] for k in ("name", "bounds") if k in x}
                          for x in read(evidence_path).get("layers", [])
                          if "text" not in x and x.get("visible", True)]
        results.append({"page_id": pid, "layout": str(layout_path),
                        "render_evidence": str(evidence_path) if evidence_path else None,
                        "render_check": "checked" if evidence_path and evidence_path.is_file() else "not_run",
                        "text_inventory": inventory, "nontext_layers_for_visual_review": decorative,
                        "consistency_issues": issues,
                        "semantic_review": "not_run", "visual_measurement_review": "not_run"})
        errors.extend({"page_id": pid, **x} for x in issues)
    for pid in sorted((set(selected) if selected else set()) - found):
        errors.append({"page_id": pid, "type": "unknown_page"})
    if not results:
        errors.append({"type": "no_pages"})
    return {"project": str(project), "technical_consistency": "FAIL" if errors else "PASS",
            "scope": "Ledger/layout and available rendered text only. Missing rendered evidence is not_run.",
            "semantic_or_visual_pass": False,
            "commerce_rules_version": rules['version'],
            "target_platform": target_platform,
            "platform_review": "target_known_rules_still_require_review" if target_platform else "platform_required",
            "commerce_findings_count": sum(len(t['commerce_findings']) for p in results for t in p['text_inventory']),
            "fonts_for_license_review": sorted({x.get('font') for p in results for x in read(Path(p['layout']))['layers'] if x.get('type') == 'text' and x.get('font')}),
            "font_license_review": "not_run; installed or named fonts do not prove free commercial permission",
            "review_required": "Read every language and actual image; link claims, icons and dimension endpoints. Hints are non-exhaustive.",
            "pages": results, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Project directory or project-state JSON")
    parser.add_argument("--pages", nargs="+", help="Stable page IDs; defaults to all pages")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--platform", help="Target platform name or alias; used for user-policy hints, not automatic legal approval")
    args = parser.parse_args()
    project = args.project.resolve()
    if project.is_dir():
        project /= "project-state.json"
    try:
        result = audit(project, set(args.pages) if args.pages else None, args.platform)
        output = args.out.resolve()
        if output.exists():
            parser.error("Output exists; use a new report version.")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"technical_consistency": result["technical_consistency"],
                          "pages": len(result["pages"]), "errors": len(result["errors"]),
                          "commerce_findings": result['commerce_findings_count'],
                          "target_platform": result['target_platform'],
                          "semantic_review": "not_run", "output": str(output)}, ensure_ascii=True))
        return 1 if result["errors"] else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Input error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

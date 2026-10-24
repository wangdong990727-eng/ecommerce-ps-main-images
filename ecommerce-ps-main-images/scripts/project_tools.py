#!/usr/bin/env python3
"""Portable project records and offline review for ecommerce-ps-main-images.

No Photoshop automation, network requests, installation or automatic approval.
The checks validate recorded evidence and files, never visual truth by themselves.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path, PureWindowsPath
import platform
import shutil
import struct
import sys
import uuid
from urllib.parse import quote

SCHEMA_VERSION = 5
KINDS = {"main", "sku", "detail"}
CHECK_NAMES = ("layout", "product", "copy", "technical")
CHECK_STATUSES = {"not_run", "pass", "fail", "blocked"}
PROJECT_STATUSES = {"planning", "in_progress", "pending_review", "approved", "manual_handoff", "delivered", "blocked"}
MODES = {"strict_replica", "adapt", "new_design"}


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def local_path(root, value):
    """Reject remote, absolute and escaping paths, including Windows paths on POSIX."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("必须填写项目内相对文件路径")
    value = value.replace("\\", "/")
    if ":" in value or value.startswith("/") or PureWindowsPath(value).is_absolute():
        raise ValueError("路径必须相对项目根目录，不接受绝对路径或 URL")
    if ".." in Path(value).parts:
        raise ValueError("路径不能含有 ..")
    root = Path(root).resolve()
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("路径或目录联接逃出了项目根目录")
    return path


def dimensions(path):
    """Pillow when installed; stdlib handles PNG/GIF/BMP/PSD and ordinary JPEG."""
    path = Path(path)
    if path.suffix.lower() not in {".psd", ".psb"} and importlib.util.find_spec("PIL"):
        try:
            from PIL import Image
            with Image.open(path) as image:
                width, height = image.size
                if image.getexif().get(274) in {5, 6, 7, 8}:
                    return height, width
                return width, height
        except Exception:
            pass
    try:
        with path.open("rb") as stream:
            header = stream.read(32)
            if header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR":
                return struct.unpack(">II", header[16:24])
            if header[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", header[6:10])
            if header[:2] == b"BM" and len(header) >= 26:
                width, height = struct.unpack("<ii", header[18:26])
                return abs(width), abs(height)
            if header[:4] == b"8BPS" and header[4:6] in (b"\x00\x01", b"\x00\x02"):
                height, width = struct.unpack(">II", header[14:22])
                return width, height
            if header[:2] == b"\xff\xd8":
                stream.seek(2)
                while stream.tell() < 4 * 1024 * 1024:
                    marker = stream.read(1)
                    if not marker:
                        break
                    if marker != b"\xff":
                        continue
                    while marker == b"\xff":
                        marker = stream.read(1)
                    if not marker or marker in (b"\xd9", b"\xda"):
                        break
                    if marker == b"\x00" or 0xD0 <= marker[0] <= 0xD7 or marker == b"\x01":
                        continue
                    length_bytes = stream.read(2)
                    if len(length_bytes) != 2:
                        break
                    length = struct.unpack(">H", length_bytes)[0]
                    if length < 2:
                        break
                    if marker[0] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        data = stream.read(5)
                        if len(data) == 5:
                            height, width = struct.unpack(">HH", data[1:5])
                            return width, height
                        break
                    stream.seek(length - 2, 1)
    except (OSError, ValueError, struct.error):
        pass
    if importlib.util.find_spec("PIL"):
        try:
            from PIL import Image
            with Image.open(path) as image:
                return image.size
        except Exception:
            pass
    return None


def check_project(project, stage="plan"):
    root = Path(project).resolve()
    result = {"schema_version": SCHEMA_VERSION, "stage": stage, "passed": False,
              "errors": [], "warnings": [], "limits": "仅核对记录、文件及证据链；不自动判断视觉相似、产品一致性或审批证据真伪。"}
    errors, warnings = result["errors"], result["warnings"]

    def fail(code, location, message):
        errors.append({"code": code, "location": location, "message": message})

    def file_check(value, location, required=True):
        if not value and not required:
            return None
        try:
            path = local_path(root, value)
        except ValueError as error:
            fail("invalid_path", location, str(error))
            return None
        if not path.is_file():
            fail("missing_file", location, "文件不存在：" + str(value))
            return None
        if path.stat().st_size == 0:
            fail("empty_file", location, "文件为空：" + str(value))
            return None
        return path

    def file_list(value, location, required=False):
        if not isinstance(value, list):
            fail("invalid_list", location, "必须是相对文件路径数组")
            return []
        if required and not value:
            fail("missing_evidence", location, "至少需要一份已保存的证据文件")
        return [file_check(item, f"{location}[{i}]") for i, item in enumerate(value)]

    try:
        state = read_json(root / "project-state.json")
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail("invalid_state", "project-state.json", str(error))
        return result
    if not isinstance(state, dict):
        fail("invalid_state", "project-state.json", "根节点必须是 JSON 对象")
        return result
    if state.get("schema_version") != SCHEMA_VERSION:
        fail("schema_version", "schema_version", "需要 schema_version=5")
    if state.get("mode") not in MODES:
        fail("mode", "mode", "需要 strict_replica / adapt / new_design")
    if state.get("status") not in PROJECT_STATUSES:
        fail("status", "status", "未知项目状态")
    if not isinstance(state.get("next_action"), str) or not state["next_action"].strip():
        fail("next_action", "next_action", "填写明确的下一步；完成时写完成后的归档状态")
    if not isinstance(state.get("issues"), list):
        fail("issues", "issues", "必须是问题数组；无问题用 []")
    for field in ("assets", "generation_jobs"):
        if not isinstance(state.get(field), list):
            fail("invalid_list", field, "必须是数组；没有时用 []")
    asset_map = {}
    for i, asset in enumerate(state.get("assets", []) if isinstance(state.get("assets"), list) else []):
        if not isinstance(asset, dict) or not isinstance(asset.get("id"), str):
            fail("asset_record", f"assets[{i}]", "素材需要唯一id及结构化记录")
            continue
        ident = asset["id"]
        if ident in asset_map:
            fail("duplicate_asset", f"assets[{i}]", "素材ID重复")
        asset_map[ident] = asset
        if "state" not in asset:
            warnings.append({"code":"legacy_asset", "location":f"assets[{i}]", "message":"旧素材记录未使用可恢复状态；不能作为新页面的已确认素材。"})
            continue
        if asset["state"] not in {"ASSET_REQUIRED", "READY", "REJECTED"}:
            fail("asset_state", f"assets[{i}]", "未知素材流程状态")
        file_list(asset.get("source_paths"), f"assets[{i}].source_paths", required=True)
        try:
            local_path(root, asset.get("path"))
        except ValueError as error:
            fail("asset_path", f"assets[{i}]", str(error))
        if asset["state"] == "READY":
            path = file_check(asset.get("path"), f"assets[{i}].path")
            if asset.get("review_result") != "PASS":
                fail("asset_review", f"assets[{i}]", "READY必须有本次PASS核验，文件存在不能代替商品通过")
            file_list(asset.get("evidence"), f"assets[{i}].evidence", required=True)
            if path and asset.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
                fail("asset_changed", f"assets[{i}]", "素材与已核验哈希不一致，需要重新检查")
        elif asset["state"] == "ASSET_REQUIRED":
            request = asset.get("request", {})
            if not isinstance(request, dict):
                request = {}
            file_check(request.get("prompt_path"), f"assets[{i}].request.prompt_path")
            file_list(request.get("reference_paths"), f"assets[{i}].request.reference_paths", required=True)
            if request.get("save_path") != asset.get("path"):
                fail("asset_return_path", f"assets[{i}]", "独立任务包的回填位置必须与素材path一致")
            if not asset.get("reason"):
                fail("asset_reason", f"assets[{i}]", "缺素材必须说明具体原因")
    profile = state.get("product_profile")
    if not isinstance(profile, dict):
        fail("product_profile", "product_profile", "缺少产品档案")
    else:
        if profile.get("type") not in {"earmuff", "glove", "other"}:
            fail("product_type", "product_profile.type", "填写 earmuff / glove / other")
        file_list(profile.get("fact_sources"), "product_profile.fact_sources", required=True)

    scope = state.get("scope")
    if not isinstance(scope, dict):
        fail("scope", "scope", "需要 kinds 和 expected_page_ids")
        scope = {}
    scope_kinds = scope.get("kinds")
    if not isinstance(scope_kinds, list) or not scope_kinds or any(k not in KINDS for k in scope_kinds):
        fail("scope_kinds", "scope.kinds", "使用 main / sku / detail 的非空数组")
        scope_kinds = []
    expected = scope.get("expected_page_ids")
    if not isinstance(expected, list) or not expected or any(not isinstance(i, str) or not i.strip() for i in expected):
        fail("empty_scope", "scope.expected_page_ids", "必须预先列出本次全部页面 ID")
        expected = []
    elif len(expected) != len(set(expected)):
        fail("duplicate_id", "scope.expected_page_ids", "页面 ID 不得重复")

    references = state.get("references")
    if not isinstance(references, list):
        fail("references", "references", "必须是参考数组")
        references = []
    if not references and state.get("mode") != "new_design":
        fail("empty_references", "references", "复刻或改编模式必须有同行参考")
    ref_map = {}
    for i, reference in enumerate(references):
        loc = f"references[{i}]"
        if not isinstance(reference, dict):
            fail("reference", loc, "参考必须是对象")
            continue
        ident = reference.get("id")
        if not isinstance(ident, str) or not ident.strip():
            fail("reference_id", loc, "缺少参考 ID")
        elif ident in ref_map:
            fail("duplicate_id", loc, "参考 ID 重复：" + ident)
        else:
            ref_map[ident] = reference
        if reference.get("kind") not in KINDS:
            fail("reference_kind", loc, "参考类型必须是 main / sku / detail")
        file_check(reference.get("path"), loc + ".path")

    pages = state.get("pages")
    if not isinstance(pages, list) or not pages:
        fail("empty_pages", "pages", "空计划不能通过；必须列出全部页面")
        pages = []
    seen_pages, used_refs, seen_kinds = set(), set(), set()
    detail_order = {r["id"]: i for i, r in enumerate(references)
                    if isinstance(r, dict) and isinstance(r.get("id"), str) and r.get("kind") == "detail"}
    last_detail = -1
    for i, page in enumerate(pages):
        loc = f"pages[{i}]"
        if not isinstance(page, dict):
            fail("page", loc, "页面必须是对象")
            continue
        ident = page.get("id")
        if not isinstance(ident, str) or not ident.strip():
            fail("page_id", loc, "缺少页面 ID")
        elif ident in seen_pages:
            fail("duplicate_id", loc, "页面 ID 重复：" + ident)
        else:
            seen_pages.add(ident)
        dependencies = page.get("asset_ids", [])
        if not isinstance(dependencies, list):
            fail("asset_dependencies", loc, "asset_ids必须是素材ID数组")
            dependencies = []
        for asset_id in dependencies:
            if asset_id not in asset_map:
                fail("unknown_asset", loc, "未知共享素材：" + str(asset_id))
            elif stage != "plan" and asset_map[asset_id].get("state") != "READY":
                fail("asset_not_ready", loc, "素材未通过或ASSET_REQUIRED：" + str(asset_id))
        if page.get("kind") not in KINDS or page.get("kind") not in scope_kinds:
            fail("page_kind", loc, "页面类型必须包含在 scope.kinds 内")
        else:
            seen_kinds.add(page["kind"])
        if not isinstance(page.get("version"), str) or not page["version"].strip():
            fail("version", loc, "需要非空页面版本；画面/文案改变后递增")
        ids = page.get("reference_ids")
        if not isinstance(ids, list) or any(not isinstance(r, str) for r in ids):
            fail("reference_ids", loc, "reference_ids 必须是字符串数组")
            ids = []
        if not ids and state.get("mode") != "new_design":
            fail("missing_reference", loc, "复刻/改编页必须映射到参考 ID")
        for ref_id in ids:
            if ref_id not in ref_map:
                fail("unknown_reference", loc, "未知参考 ID：" + ref_id)
            else:
                used_refs.add(ref_id)
                if ref_map[ref_id].get("kind") != page.get("kind"):
                    fail("reference_kind_mismatch", loc, "页面和参考类型不一致：" + ref_id)
            if state.get("mode") == "strict_replica" and page.get("kind") == "detail" and ref_id in detail_order:
                if detail_order[ref_id] < last_detail:
                    fail("reference_order", loc, "严格复刻的详情顺序倒退；不得先合并后段再回填前段")
                last_detail = max(last_detail, detail_order[ref_id])
        layout_path = file_check(page.get("layout"), loc + ".layout")
        preview = file_check(page.get("preview"), loc + ".preview", required=stage != "plan")
        if preview and (not dimensions(preview) or min(dimensions(preview)) <= 0):
            fail("unreadable_preview", loc + ".preview", "无法读取图片宽高；检查文件，特殊格式需 Pillow")
        psd = file_check(page.get("psd"), loc + ".psd", required=stage == "delivery")
        if psd:
            if psd.suffix.lower() not in {".psd", ".psb"}:
                fail("psd_extension", loc + ".psd", "编辑文件必须是 PSD 或 PSB")
            try:
                with psd.open("rb") as stream:
                    signature = stream.read(4)
                if signature != b"8BPS" or not dimensions(psd):
                    fail("psd_signature", loc + ".psd", "不是可识别的 Photoshop 文件头；还需实际重新打开核验")
                elif preview and dimensions(preview) and dimensions(psd) != dimensions(preview):
                    fail("export_geometry", loc, "PSD 与预览导出尺寸不一致")
            except OSError as error:
                fail("psd_read", loc + ".psd", str(error))

        copies = page.get("copy")
        if not isinstance(copies, list):
            fail("copy", loc + ".copy", "缺少逐条文案；无文字页面明确使用 []")
            copies = []
        copy_ids = set()
        for j, item in enumerate(copies):
            cloc = f"{loc}.copy[{j}]"
            if not isinstance(item, dict):
                fail("copy_item", cloc, "文案必须是对象")
                continue
            if not isinstance(item.get("id"), str) or not item["id"].strip() or item["id"] in copy_ids:
                fail("copy_id", cloc, "文案 ID 缺少或重复")
            else:
                copy_ids.add(item["id"])
            if not isinstance(item.get("reference_text"), str) or not isinstance(item.get("final_text"), str):
                fail("copy_text", cloc, "reference_text / final_text 必须是字符串，逐字保留换行")
            changed = item.get("reference_text") != item.get("final_text")
            if not isinstance(item.get("change_reason"), str):
                fail("change_reason", cloc, "change_reason 必须是字符串；未改使用空字符串")
            elif changed and not item["change_reason"].strip():
                fail("unexplained_copy_change", cloc, "文案变化必须说明必要原因")
            file_list(item.get("fact_sources"), cloc + ".fact_sources", required=changed and state.get("mode") == "strict_replica")

        # The common renderer exposes native text IDs; keep the copy ledger tied
        # to the data actually rendered. Custom PSD components still need review.
        if layout_path:
            try:
                layout = read_json(layout_path)
                if isinstance(layout, dict) and layout.get("schema_version") == "1.0":
                    layers = layout.get("layers", [])
                    if isinstance(layers, list):
                        rendered_text = {l.get("id"): l.get("text") for l in layers
                                         if isinstance(l, dict) and l.get("type") == "text"}
                        recorded_text = {c.get("id"): c.get("final_text") for c in copies
                                         if isinstance(c, dict) and isinstance(c.get("id"), str)}
                        normalize = lambda t: t.replace("\r\n", "\n").replace("\r", "\n") if isinstance(t, str) else t
                        if {k: normalize(v) for k, v in rendered_text.items()} != {k: normalize(v) for k, v in recorded_text.items()}:
                            fail("copy_layout_mismatch", loc, "文案记录的ID/最终文字与布局中的原生文字不一致")
            except (OSError, ValueError, TypeError) as error:
                fail("invalid_layout_json", loc + ".layout", str(error))

        checks = page.get("checks")
        if not isinstance(checks, dict):
            fail("missing_checks", loc + ".checks", "缺少四项核验记录")
            checks = {}
        all_pass = True
        for check_name in CHECK_NAMES:
            item = checks.get(check_name)
            check_loc = f"{loc}.checks.{check_name}"
            if not isinstance(item, dict):
                fail("missing_check", check_loc, "核验记录缺失；未做填 not_run")
                all_pass = False
                continue
            status = item.get("status")
            if status not in CHECK_STATUSES:
                fail("check_status", check_loc, "未知核验状态")
            if status != "pass":
                all_pass = False
            if not isinstance(item.get("issues"), list):
                fail("check_issues", check_loc, "issues 必须是数组")
            elif status == "pass" and item["issues"]:
                fail("pass_with_issues", check_loc, "仍有未解决问题不能记录 pass")
            elif status in {"fail", "blocked"} and not item["issues"]:
                fail("missing_failure_reason", check_loc, "失败/阻塞必须说明问题")
            file_list(item.get("evidence"), check_loc + ".evidence", required=status == "pass")
            if stage != "plan" and status != "pass":
                fail("check_not_pass", check_loc, "当前状态为 " + str(status) + "，不能声称已通过自检")
        approval = page.get("user_approval")
        if not isinstance(approval, dict):
            fail("missing_approval", loc, "缺少 user_approval；默认应为 pending")
            approval = {}
        approval_status = approval.get("status")
        if approval_status not in {"pending", "approved", "manual_handoff"}:
            fail("approval_status", loc, "审批状态只能是 pending / approved / manual_handoff")
        if not isinstance(approval.get("version"), str):
            fail("approval_version", loc, "审批版本必须是字符串；未审批可为空")
        file_list(approval.get("evidence"), loc + ".user_approval.evidence", required=approval_status in {"approved", "manual_handoff"})
        if approval_status in {"approved", "manual_handoff"} and approval.get("version") != page.get("version"):
            fail("stale_approval", loc, "审批版本与当前页面不一致；修改后需重置 pending")
        if approval_status == "approved" and not all_pass:
            fail("false_approved", loc, "仍有未通过的核验，不能记录为正式 approved")
        if stage == "delivery" and approval_status != "approved":
            fail("not_approved", loc, "正式交付需要当前版本 approved；manual_handoff 仅可交待人工修补包")

    if set(expected) != seen_pages:
        fail("scope_coverage", "pages", "页面与范围不一致；缺少 " + str(sorted(set(expected) - seen_pages)) + "；额外 " + str(sorted(seen_pages - set(expected))))
    if set(scope_kinds) != seen_kinds:
        fail("kind_coverage", "pages", "scope.kinds 中的每一类都必须有页面")
    if set(ref_map) != used_refs:
        fail("uncovered_references", "references", "存在尚未复刻/映射的参考：" + ", ".join(sorted(set(ref_map) - used_refs)))
    if state.get("status") in {"approved", "delivered"}:
        if any(not isinstance(p, dict) or not isinstance(p.get("user_approval"), dict) or p["user_approval"].get("status") != "approved" for p in pages):
            fail("false_project_status", "status", "项目声称通过/交付，但存在未批准页面")
    if stage == "delivery" and state.get("issues"):
        fail("open_project_issues", "issues", "仍有项目问题；正式交付前解决并把处理结果写入证据")
    if stage == "delivery" and state.get("status") not in {"approved", "delivered"}:
        fail("project_not_approved", "status", "正式交付前项目状态须与当前页面批准范围一致")
    if not importlib.util.find_spec("PIL"):
        warnings.append({"code": "no_pillow", "location": "environment", "message": "未安装 Pillow；仍可读常见 PNG/JPEG/GIF/BMP/PSD 宽高，特殊格式须转换或人工检查。脚本不会安装依赖。"})
    result["passed"] = not errors
    result["page_count"] = len(pages)
    result["reference_count"] = len(references)
    result["asset_required_ids"] = [k for k, v in asset_map.items() if v.get("state") == "ASSET_REQUIRED"]
    return result


def return_asset(project, asset_id, evidence, review):
    """Attach inspected material; preserve outputs and reset only dependent checks."""
    root = Path(project).resolve()
    state = read_json(root / "project-state.json")
    rows = [a for a in state.get("assets", []) if isinstance(a, dict) and a.get("id") == asset_id]
    if len(rows) != 1:
        raise ValueError("需要一个唯一素材ID")
    asset = rows[0]
    proof = local_path(root, evidence)
    material = local_path(root, asset.get("path"))
    if not proof.is_file() or not proof.stat().st_size:
        raise ValueError("保存逐图检查证据后再回填")
    if review == "PASS" and (not material.is_file() or not material.stat().st_size):
        raise ValueError("缺少真实素材，不能回填PASS")
    for value in asset.get("source_paths", []):
        if not local_path(root, value).is_file():
            raise ValueError("原始事实来源缺失")
    current_hash = hashlib.sha256(material.read_bytes()).hexdigest() if material.is_file() else ""
    affected = [p["id"] for p in state.get("pages", []) if asset_id in p.get("asset_ids", [])]
    if review == "PASS" and asset.get("state") == "READY" and asset.get("sha256") == current_hash and asset.get("evidence") == [evidence]:
        return {"result":"PASS", "asset_id":asset_id, "state":"READY", "affected_page_ids":affected, "outputs_modified":False, "no_op":True}
    snapshot = root / "evidence" / ("state-before-return-" + uuid.uuid4().hex + ".json")
    write_json(snapshot, state)
    asset.update(state="READY" if review == "PASS" else ("REJECTED" if review == "FAIL" else "ASSET_REQUIRED"), review_result=review, evidence=[evidence])
    asset["sha256"] = current_hash
    affected = []
    for page in state.get("pages", []):
        if asset_id in page.get("asset_ids", []):
            affected.append(page["id"])
            for key in ("layout", "product", "technical"):
                page["checks"][key] = {"status":"not_run", "evidence":[], "issues":[]}
            page["user_approval"] = {"status":"pending", "version":"", "evidence":[]}
    state["status"] = "in_progress" if review == "PASS" else "blocked"
    state["next_action"] = "只恢复素材 " + asset_id + " 的依赖页面：" + ", ".join(affected) + "；原PSD/JPG不自动重写，回填后重新检查。"
    write_json(root / "project-state.json", state)
    return {"result":review, "asset_id":asset_id, "state":asset["state"], "affected_page_ids":affected, "checkpoint":str(snapshot.relative_to(root)), "outputs_modified":False}


def init_project(project):
    root = Path(project).resolve()
    target = root / "project-state.json"
    if target.exists():
        raise ValueError("已存在 project-state.json；init 不覆盖现有记录")
    template = Path(__file__).resolve().parent.parent / "templates" / "task-plan.json"
    state = read_json(template)
    root.mkdir(parents=True, exist_ok=True)
    for name in ("references", "product", "layouts", "previews", "psd", "evidence"):
        (root / name).mkdir(exist_ok=True)
    write_json(target, state)
    return {"created": str(target), "status": "planning", "note": "模板不会自动获得通过或审批；先填实际材料和范围。"}


def preflight():
    candidates = []
    bases = []
    for name in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        value = os.environ.get(name)
        if value and value not in bases:
            bases.append(value)
    if os.name == "nt":
        # Read only: App Paths also covers installations outside Program Files.
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for view in (0, winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                    try:
                        with winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\App Paths\Photoshop.exe", 0, winreg.KEY_READ | view) as key:
                            executable = Path(winreg.QueryValueEx(key, "")[0].strip('"'))
                            if executable.is_file():
                                candidates.append(str(executable))
                    except OSError:
                        pass
        except ImportError:
            pass
        for base in bases:
            adobe = Path(base) / "Adobe"
            try:
                candidates.extend(str(p) for p in adobe.glob("Adobe Photoshop*/Photoshop.exe") if p.is_file())
            except OSError:
                pass
    elif sys.platform == "darwin":
        candidates.extend(str(p) for p in Path("/Applications").glob("Adobe Photoshop*/*.app") if p.is_dir())
    desktop = Path.home() / "Desktop"
    desktop_source = "home/Desktop fallback; existence checked"
    if os.name == "nt":
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                desktop = Path(os.path.expandvars(winreg.QueryValueEx(key, "Desktop")[0]))
            desktop_source = "Windows user Desktop registry value; read-only"
        except (OSError, ImportError):
            pass
    return {"checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "os": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
            "python": {"version": platform.python_version(), "executable": sys.executable},
            "pillow": {"available": importlib.util.find_spec("PIL") is not None, "required": False},
            "dependencies": {"pywin32_available": importlib.util.find_spec("win32com") is not None, "automatic_install":False},
            "fonts": {"status":"not_tested", "note":"PS首次小样的assertFonts检查实际PostScript名称；预检不启动PS。"},
            "desktop": {"path": str(desktop), "exists": desktop.is_dir(), "source": desktop_source},
            "photoshop": {"candidate_paths": sorted(set(candidates)), "searched_locations": (bases + ["Windows App Paths (read-only)"]) if os.name == "nt" else (["/Applications"] if sys.platform == "darwin" else bases),
                          "running_or_usable": "not_tested", "note": "候选路径不是可用性验证；自定义安装目录需另行提供。未启动 Photoshop。"},
            "image_generation": {"status": "not_tested", "note": "未探测账号、密钥或服务；由执行环境实际试跑一张后记录。"},
            "mutations": "仅按 --out 写本份报告；未安装依赖、启动应用或修改配置。"}


def report_project(project, output):
    root = Path(project).resolve()
    state = read_json(root / "project-state.json")
    if not isinstance(state, dict):
        raise ValueError("project-state.json 根节点必须是对象")
    out = Path(output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    assets = out.parent / (out.stem + ".assets")
    assets.mkdir(exist_ok=True)
    e = lambda value: html.escape(str(value), quote=True)
    copied = {}

    def copy_asset(value):
        try:
            source = local_path(root, value)
            if not source.is_file():
                return None
            key = str(source)
            if key not in copied:
                digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
                extension = source.suffix.lower()
                if len(extension) > 12 or not all(c.isalnum() or c == "." for c in extension):
                    extension = ".bin"
                target = assets / (digest + extension)
                if source != target.resolve():
                    shutil.copyfile(source, target)
                copied[key] = quote(assets.name) + "/" + quote(target.name)
            return copied[key]
        except (ValueError, OSError):
            return None

    def image_info(value):
        try:
            source = local_path(root, value)
        except ValueError:
            return None
        size = dimensions(source)
        if not size or min(size) <= 0:
            return None
        link = copy_asset(value)
        return {"url": link, "w": size[0], "h": size[1]} if link else None

    def image_html(info, label):
        if not info:
            return '<p class="missing">文件缺失或宽高无法读取</p>'
        return f'<a href="{e(info["url"])}" target="_blank" rel="noopener"><img src="{e(info["url"])}" alt="{e(label)}" loading="lazy"></a><small>{info["w"]} × {info["h"]}</small>'

    validation = check_project(root, "review")
    references = {r.get("id"): r for r in state.get("references", []) if isinstance(r, dict) and isinstance(r.get("id"), str)}
    pages_html = []
    for index, page in enumerate(state.get("pages", [])):
        if not isinstance(page, dict):
            continue
        page_id = page.get("id", f"page-{index + 1}")
        preview = image_info(page.get("preview"))
        refs = page.get("reference_ids", [])
        refs = refs if isinstance(refs, list) else []
        panels = []
        for ref_id in refs or [None]:
            ref = references.get(ref_id, {}) if isinstance(ref_id, str) else {}
            original = image_info(ref.get("path"))
            panels.append('<div class="pair"><figure><figcaption>参考 ' + e(ref_id or "无参考") + '</figcaption>' + image_html(original, "同行参考") + '</figure><figure><figcaption>当前结果</figcaption>' + image_html(preview, "当前结果") + '</figure></div>')
            if original and preview:
                different = abs(original["w"] / original["h"] - preview["w"] / preview["h"]) > 0.001 * original["w"] / original["h"]
                note = "宽高比不同：两图按同宽等比缩放、顶部对齐，不拉伸；空白/溢出反映原始差异。" if different else "同宽等比缩放、顶部对齐；滑块调整结果透明度。"
                ratio_height = max(original["h"] / original["w"], preview["h"] / preview["w"])
                panels.append(f'<details><summary>等比叠加检查</summary><p class="{"warning" if different else "hint"}">{e(note)}</p><label>结果透明度 <input class="opacity" type="range" min="0" max="100" value="50"><output>50%</output></label><div class="overlay-scroll"><div class="overlay" style="aspect-ratio:1/{ratio_height:.8f}"><img src="{e(original["url"])}" alt="参考底图"><img class="result-layer" src="{e(preview["url"])}" alt="结果叠加图" style="opacity:.5"></div></div></details>')
        copies = page.get("copy", [])
        rows = []
        for item in copies if isinstance(copies, list) else []:
            if isinstance(item, dict):
                changed = item.get("reference_text") != item.get("final_text")
                rows.append(f'<tr class="{"changed" if changed else ""}"><td>{e(item.get("id", ""))}</td><td class="verbatim">{e(item.get("reference_text", ""))}</td><td class="verbatim">{e(item.get("final_text", ""))}</td><td>{e(item.get("change_reason", ""))}</td></tr>')
        checks = page.get("checks", {})
        checks = checks if isinstance(checks, dict) else {}
        check_rows = []
        for name in CHECK_NAMES:
            item = checks.get(name, {})
            item = item if isinstance(item, dict) else {}
            links = []
            for proof in item.get("evidence", []) if isinstance(item.get("evidence"), list) else []:
                link = copy_asset(proof)
                links.append(f'<a href="{e(link)}" target="_blank" rel="noopener">{e(proof)}</a>' if link else e(proof) + "（缺失）")
            check_rows.append(f'<tr><td>{e(name)}</td><td>{e(item.get("status", "missing"))}</td><td>{"<br>".join(links)}</td><td>{e(json.dumps(item.get("issues", []), ensure_ascii=False))}</td></tr>')
        approval = page.get("user_approval", {})
        approval = approval if isinstance(approval, dict) else {}
        approval_links = []
        for proof in approval.get("evidence", []) if isinstance(approval.get("evidence"), list) else []:
            link = copy_asset(proof)
            approval_links.append(f'<a href="{e(link)}">{e(proof)}</a>' if link else e(proof) + "（缺失）")
        pages_html.append(f'<section id="page-{index}"><h2>{e(page_id)} · {e(page.get("kind", ""))} · {e(page.get("version", ""))}</h2><p>用户验收：<strong>{e(approval.get("status", "missing"))}</strong>；验收版本：{e(approval.get("version", ""))} {" / ".join(approval_links)}</p>{"".join(panels)}<h3>文案逐条对照</h3><table><thead><tr><th>ID</th><th>同行原文</th><th>当前文案</th><th>必要修改原因</th></tr></thead><tbody>{"".join(rows)}</tbody></table><h3>检查记录</h3><table><thead><tr><th>检查</th><th>状态</th><th>已存证据</th><th>未解决问题</th></tr></thead><tbody>{"".join(check_rows)}</tbody></table><p>版式记录：{e(page.get("layout", ""))}<br>PSD：{e(page.get("psd", ""))}（编辑源文件随项目文件夹携带）</p></section>')
    issue_html = "".join(f'<li><code>{e(item["location"])}</code>：{e(item["message"])}</li>' for item in validation["errors"])
    warning_html = "".join(f'<li>{e(item["message"])}</li>' for item in validation["warnings"])
    state_name = assets / "project-state.snapshot.json"
    write_json(state_name, state)
    write_json(assets / "review-check.json", validation)
    source_link = quote(assets.name) + "/project-state.snapshot.json"
    nav = " ".join(f'<a href="#page-{i}">{e(p.get("id", str(i + 1)))}</a>' for i, p in enumerate(state.get("pages", [])) if isinstance(p, dict))
    document = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>逐页复刻审阅</title><style>
*{box-sizing:border-box}body{margin:0;background:#edf0f3;color:#1c2530;font-family:system-ui,"Microsoft YaHei",sans-serif;line-height:1.65}header,main{max-width:1440px;margin:auto;padding:24px}header{background:#172538;color:#fff}header a{color:#b9dfff}h1{font-size:26px;margin:0 0 10px}h2{font-size:23px}h3{font-size:17px}section,.summary{background:white;border:1px solid #d6dfe7;border-radius:10px;padding:22px;margin:22px 0}nav{display:flex;gap:12px;flex-wrap:wrap}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start}figure{margin:0;min-width:0;background:#f5f6f8;border:1px solid #d7dce2;padding:8px}figcaption{font-weight:700;margin:4px 0 10px}figure img{display:block;width:100%;height:auto}figure small{display:block;color:#556473}details{margin:18px 0;border:1px solid #c8d3de;padding:12px}summary{cursor:pointer;font-weight:650}.overlay-scroll{max-height:1100px;overflow:auto;margin-top:10px;background:repeating-conic-gradient(#e6e6e6 0% 25%,white 0% 50%) 0/18px 18px}.overlay{position:relative;width:100%;overflow:hidden}.overlay img{position:absolute;top:0;left:0;width:100%;height:auto;display:block}.opacity{width:min(420px,55vw);vertical-align:middle}table{width:100%;border-collapse:collapse;table-layout:fixed;overflow-wrap:anywhere}td,th{border:1px solid #d6dce4;padding:9px;vertical-align:top;text-align:left}th{background:#eef3f7}.verbatim{white-space:pre-wrap}.changed{background:#fff7dc}.warning,.missing{color:#983e0a}.hint{color:#516171}.badge{font-weight:bold}a{color:#145895}code{overflow-wrap:anywhere}pre{white-space:pre-wrap}label{display:flex;gap:12px;align-items:center}@media(max-width:750px){header,main{padding:12px}.pair{gap:8px}section{padding:12px}td,th{padding:5px;font-size:12px}}
</style></head><body>'''
    document += f'<header><h1>逐页复刻审阅</h1><p>模式：{e(state.get("mode", ""))} · 项目状态：{e(state.get("status", ""))}</p><nav>{nav}</nav></header><main><div class="summary"><p class="badge">审阅记录检查：{"通过" if validation["passed"] else "未通过 / 待处理"}</p><p>{e(validation["limits"])}</p><p>可直接双击本 HTML；跨机携带本文件及相邻 <code>{e(assets.name)}</code> 文件夹。图片保持原宽高比；此报告不会修改验收状态。</p><p>下一步：{e(state.get("next_action", ""))}</p><ul>{issue_html}{warning_html}</ul><a href="{e(source_link)}">项目记录快照</a></div>{"".join(pages_html)}</main>'
    document += '''<script>document.querySelectorAll('.opacity').forEach(function(slider){slider.addEventListener('input',function(){var box=slider.closest('details');box.querySelector('.result-layer').style.opacity=Number(slider.value)/100;box.querySelector('output').textContent=slider.value+'%';});});</script></body></html>'''
    out.write_text(document, encoding="utf-8")
    return {"report": str(out), "assets": str(assets), "review_check_passed": validation["passed"], "note": "报告已生成；生成成功不等于自检或用户验收通过。"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="创建项目记录模板，不覆盖已有记录")
    init.add_argument("project")
    check = commands.add_parser("check", help="检查记录、文件及证据链；未通过返回 1")
    check.add_argument("project")
    check.add_argument("--stage", choices=("plan", "review", "delivery"), default="plan")
    check.add_argument("--json-out")
    report = commands.add_parser("report", help="生成可携带的离线 HTML 并排和等比叠加对照")
    report.add_argument("project")
    report.add_argument("--out", required=True)
    pre = commands.add_parser("preflight", help="只读检测环境，不启动 Photoshop 或安装软件")
    pre.add_argument("--out", required=True)
    attach = commands.add_parser("asset-return", help="按检查证据回填一张素材，保留原输出并恢复依赖页面")
    attach.add_argument("project")
    attach.add_argument("asset_id")
    attach.add_argument("--evidence", required=True)
    attach.add_argument("--review", choices=("PASS", "PARTIAL", "FAIL"), required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init_project(args.project)
        elif args.command == "check":
            result = check_project(args.project, args.stage)
            if args.json_out:
                write_json(args.json_out, result)
        elif args.command == "report":
            result = report_project(args.project, args.out)
        elif args.command == "asset-return":
            result = return_asset(args.project, args.asset_id, args.evidence, args.review)
        else:
            result = preflight()
            result["writable_output"] = {"path":str(Path(args.out).resolve().parent), "status":"PASS", "evidence":"This report was written to the requested output path."}
            write_json(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == "check" and not result["passed"] else 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

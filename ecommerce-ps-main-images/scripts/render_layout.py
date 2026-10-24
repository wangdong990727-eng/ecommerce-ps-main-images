"""Validate a measured layout, then compile portable native Photoshop JSX.

Python standard library only. This compiler does not generate images or infer
design. Execute the resulting JSX in Photoshop; compilation is not rendering.
"""
from __future__ import annotations

import argparse
import hashlib
import copy
import json
import math
import re
import sys
from pathlib import Path


class SpecError(ValueError):
    pass


def keys(value, allowed, required, where):
    if not isinstance(value, dict):
        raise SpecError(f"{where}: expected an object")
    unknown = set(value) - set(allowed)
    missing = set(required) - set(value)
    if unknown:
        raise SpecError(f"{where}: unsupported fields {sorted(unknown)}; implement and verify the technique, do not approximate silently")
    if missing:
        raise SpecError(f"{where}: missing fields {sorted(missing)}")


def number(value, where, lo=None, hi=None, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise SpecError(f"{where}: expected a finite number")
    if integer and value != int(value):
        raise SpecError(f"{where}: expected an integer")
    if lo is not None and value < lo or hi is not None and value > hi:
        raise SpecError(f"{where}: outside supported range {lo}..{hi}")
    return value


def string(value, where, allow_empty=False):
    if not isinstance(value, str) or (not value and not allow_empty) or "\x00" in value:
        raise SpecError(f"{where}: expected a string without NUL")
    return value


def color(value, where):
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise SpecError(f"{where}: use #RRGGBB")


def vector(value, count, where, positive_from=None):
    if not isinstance(value, list) or len(value) != count:
        raise SpecError(f"{where}: expected an array with {count} values")
    for i, item in enumerate(value):
        number(item, f"{where}[{i}]", 0.001 if positive_from is not None and i >= positive_from else -100000, 100000)


def enum(value, allowed, where):
    if value not in allowed:
        raise SpecError(f"{where}: expected one of {allowed}")


def checked_path(value, root, where, require_exists):
    string(value, where)
    p = Path(value).expanduser()
    p = (root / p).resolve() if not p.is_absolute() else p.resolve()
    if require_exists and not p.is_file():
        raise SpecError(f"{where}: file does not exist: {p}")
    return p.as_posix()


def validate_spec(raw, spec_path, skeleton=False):
    """Closed schema; return an isolated copy with resolved asset paths."""
    v = copy.deepcopy(raw)
    keys(v, {"schema_version", "job_id", "canvas", "layers", "reference"},
         {"schema_version", "job_id", "canvas", "layers"}, "spec")
    if v["schema_version"] != "1.0":
        raise SpecError("schema_version: only '1.0' is supported")
    if not isinstance(v["job_id"], str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", v["job_id"]):
        raise SpecError("job_id: use 1..80 ASCII letters/digits/underscore/hyphen, starting with a letter")
    if v["job_id"].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{x}" for x in range(1, 10)], *[f"LPT{x}" for x in range(1, 10)]}:
        raise SpecError("job_id: reserved filesystem name")
    root = Path(spec_path).resolve().parent
    cv = v["canvas"]
    keys(cv, {"width", "height", "resolution", "background"}, {"width", "height"}, "canvas")
    for field in ("width", "height"):
        number(cv[field], f"canvas.{field}", 1, 30000, True)
    cv.setdefault("resolution", 72)
    if cv["resolution"] != 72 or isinstance(cv["resolution"], bool):
        raise SpecError("canvas.resolution: this pixel renderer requires 72 ppi; do not silently rescale typography")
    cv.setdefault("background", "#FFFFFF")
    color(cv["background"], "canvas.background")
    if "reference" in v:
        ref = v["reference"]
        keys(ref, {"path", "size"}, {"path", "size"}, "reference")
        ref["path"] = checked_path(ref["path"], root, "reference.path", True)
        vector(ref["size"], 2, "reference.size", 0)
    if not isinstance(v["layers"], list) or not v["layers"]:
        raise SpecError("layers: expected a nonempty bottom-to-top array")
    if len(v["layers"]) > 2000:
        raise SpecError("layers: split this oversized job; maximum 2000 layers")
    ids = set()
    common = {"id", "type", "name", "opacity", "rotation", "stroke", "shadow"}
    kinds = {
        "text": {"text", "position", "box", "size", "font", "color", "align", "leading", "tracking"},
        "image": {"source", "box", "fit", "mask_box"},
        "rect": {"box", "color"},
    }
    needed = {"text": {"text", "font", "size", "color"}, "image": {"source", "box", "fit"}, "rect": {"box", "color"}}
    for i, layer in enumerate(v["layers"]):
        where = f"layers[{i}]"
        if not isinstance(layer, dict) or not isinstance(layer.get("type"), str) or layer.get("type") not in kinds:
            raise SpecError(f"{where}.type: only text/image/rect are implemented; unsupported techniques must be implemented and tested explicitly")
        kind = layer["type"]
        keys(layer, common | kinds[kind], {"id", "type"} | needed[kind], where)
        ident = string(layer["id"], where + ".id")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", ident) or ident in ids:
            raise SpecError(f"{where}.id: use a unique stable ASCII identifier")
        ids.add(ident)
        if "name" in layer:
            string(layer["name"], where + ".name")
        if "opacity" in layer:
            number(layer["opacity"], where + ".opacity", 0, 100)
        if "rotation" in layer:
            number(layer["rotation"], where + ".rotation", -360, 360)
        if "box" in layer:
            vector(layer["box"], 4, where + ".box", 2)
        if "color" in layer:
            color(layer["color"], where + ".color")
        if "stroke" in layer:
            st = layer["stroke"]
            keys(st, {"size", "color", "position"}, {"size", "color"}, where + ".stroke")
            number(st["size"], where + ".stroke.size", 0.1, 250)
            color(st["color"], where + ".stroke.color")
            enum(st.get("position", "outside"), ("outside", "inside", "center"), where + ".stroke.position")
        if "shadow" in layer:
            sh = layer["shadow"]
            keys(sh, {"color", "opacity", "angle", "distance", "blur", "spread"},
                 {"color", "opacity", "angle", "distance", "blur"}, where + ".shadow")
            color(sh["color"], where + ".shadow.color")
            for field, lo, hi in (("opacity", 0, 100), ("angle", -360, 360), ("distance", 0, 30000), ("blur", 0, 250), ("spread", 0, 100)):
                if field in sh:
                    number(sh[field], f"{where}.shadow.{field}", lo, hi)
        if kind == "text":
            string(layer["text"], where + ".text", True)
            string(layer["font"], where + ".font")
            number(layer["size"], where + ".size", 0.1, 1296)
            if ("position" in layer) == ("box" in layer):
                raise SpecError(f"{where}: text requires exactly one of position or box")
            if "position" in layer:
                vector(layer["position"], 2, where + ".position")
            enum(layer.get("align", "left"), ("left", "center", "right"), where + ".align")
            if "tracking" in layer:
                number(layer["tracking"], where + ".tracking", -1000, 10000, True)
            if "leading" in layer:
                number(layer["leading"], where + ".leading", 0.1, 1296)
        elif kind == "image":
            enum(layer["fit"], ("contain", "cover"), where + ".fit")
            layer["source"] = checked_path(layer["source"], root, where + ".source", not skeleton)
            if Path(layer["source"]).suffix.lower() not in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".psd", ".psb"}:
                raise SpecError(f"{where}.source: only PNG/JPEG/TIFF/PSD/PSB supported; convert with verified appearance first")
            if "mask_box" in layer:
                vector(layer["mask_box"], 4, where + ".mask_box", 2)
    return v


RUNNER = r'''
(function(){
var spec=__SPEC__, output=__OUTPUT__, skeleton=__SKELETON__, buildSources=__BUILD_SOURCES__;
var basename=spec.job_id+(skeleton?'_skeleton':''), root=new Folder(output);
EC.ensureFolder(root);
var statusPath=root.fsName+'/'+basename+'.status.json', evidencePath=root.fsName+'/'+basename+'.layers.json';
var reserved=[statusPath,evidencePath,root.fsName+'/PSD/'+basename+'.psd',root.fsName+'/JPG/'+basename+'.jpg'];
for(var q=0;q<reserved.length;q++)if(new File(reserved[q]).exists)throw Error('Output exists; choose a NEW job_id or output directory: '+reserved[q]);
var state=EC.begin(), before=[], owned=null, stage='preflight', steps=[], result=null;
for(var q=0;q<app.documents.length;q++)before.push({id:app.documents[q].id,saved:app.documents[q].saved});
function log(phase){stage=phase;steps.push(phase);EC.writeJson(statusPath,{status:'running',stage:stage,steps:steps,job_id:spec.job_id,skeleton:skeleton});}
function verifyExisting(){for(var i=0;i<before.length;i++){var found=false;for(var j=0;j<app.documents.length;j++)if(app.documents[j].id===before[i].id){found=true;if(app.documents[j].saved!==before[i].saved)throw Error('Existing document saved state changed');}if(!found)throw Error('Existing document missing');}}
try{
 log('fonts');EC.assertFonts(spec.layers);
 owned=app.documents.add(spec.canvas.width,spec.canvas.height,spec.canvas.resolution,basename,NewDocumentMode.RGB,DocumentFill.TRANSPARENT);
 EC.rect(owned,'CANVAS_BACKGROUND',0,0,spec.canvas.width,spec.canvas.height,spec.canvas.background);
 for(var i=0;i<spec.layers.length;i++){
  var v=spec.layers[i],l,b=v.box;log('layer:'+v.id);
  if(v.type==='text')l=EC.styledText(owned,v);
  else if(v.type==='rect'){
   l=EC.rect(owned,v.id+' | '+(v.name||v.id),b[0],b[1],b[2],b[3],v.color);
   if(v.rotation)l.rotate(v.rotation,AnchorPosition.MIDDLECENTER);
  }else if(v.type==='image'){
   if(skeleton)l=EC.rect(owned,v.id+' | SKELETON_IMAGE',b[0],b[1],b[2],b[3],'#DDE5ED');
   else{
    l=EC.placeEmbedded(owned,v.source,v.id+' | '+(v.name||v.id));
    EC.fit(l,b[0],b[1],b[2],b[3],v.fit==='cover');
    if(v.rotation)l.rotate(v.rotation,AnchorPosition.MIDDLECENTER);
   }
   EC.frameMask(owned,l,v.mask_box||b);
  }
  if(v.opacity!==undefined)l.opacity=v.opacity;
  EC.effects(owned,l,v);
 }
 if(typeof EC_afterLayout==='function'){log('project_components');EC_afterLayout(owned,spec);}
 log('save');result=EC.savePair(owned,root.fsName,basename);owned.close(SaveOptions.DONOTSAVECHANGES);owned=null;
 log('reopen');owned=app.open(new File(result.psd));
 if(owned.fullName.fsName.toLowerCase()!==new File(result.psd).fsName.toLowerCase())throw Error('Reopened PSD path mismatch');
 var evidence=[],textCount=0,smartCount=0,maskCount=0;
 for(var i=0;i<owned.layers.length;i++){
  var row=EC.layerEvidence(owned.layers[i]);evidence.push(row);
  if(owned.layers[i].kind===LayerKind.TEXT)textCount++;
  if(owned.layers[i].kind===LayerKind.SMARTOBJECT){smartCount++;if(row.linked)throw Error('Linked image must be embedded: '+row.name);}
  if(row.has_user_mask)maskCount++;
 }
 var expectedText=0,expectedImage=0;
 for(var i=0;i<spec.layers.length;i++){if(spec.layers[i].type==='text')expectedText++;if(spec.layers[i].type==='image')expectedImage++;}
 if(textCount!==expectedText||(!skeleton&&smartCount!==expectedImage)||maskCount!==expectedImage)throw Error('Reopened native layer counts mismatch');
 EC.writeJson(evidencePath,{job_id:spec.job_id,skeleton:skeleton,read_order:'top-to-bottom',source_spec:spec,build_sources:buildSources,output:result,layers:evidence,native_text_count:textCount,embedded_smart_count:smartCount,frame_mask_count:maskCount,visual_review:'not_run'});
 owned.close(SaveOptions.DONOTSAVECHANGES);owned=null;verifyExisting();
 EC.writeJson(statusPath,{status:'complete',stage:'verified_reopen',steps:steps,job_id:spec.job_id,skeleton:skeleton,output:result,evidence:evidencePath,existing_documents_preserved:before.length,visual_review:'not_run'});
}catch(e){EC.writeJson(statusPath,{status:'error',stage:stage,steps:steps,message:e.message,line:e.line||null,job_id:spec.job_id,partial_output:result});throw e;}
finally{if(owned)try{owned.close(SaveOptions.DONOTSAVECHANGES);}catch(ignore){}EC.end(state);}
})();
'''


def compile_layout(spec_path, out, output_dir=None, skeleton=False, components=None):
    spec_path, out = Path(spec_path).resolve(), Path(out).resolve()
    raw = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    spec = validate_spec(raw, spec_path, skeleton)
    destination = Path(output_dir).expanduser().resolve() if output_dir else spec_path.parent / "rendered"
    if out.exists():
        raise SpecError(f"JSX already exists; choose a new --out path: {out}")
    helper = Path(__file__).with_name("photoshop_helpers.jsxinc").read_text(encoding="utf-8-sig")
    component_code = ""
    sources = {"layout": {"name": spec_path.name, "sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest()},
               "helper_sha256": hashlib.sha256(Path(__file__).with_name("photoshop_helpers.jsxinc").read_bytes()).hexdigest(),
               "compiler_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "components": None}
    if components is not None:
        component_path = Path(components).resolve()
        if not component_path.is_file() or component_path.suffix.lower() != ".jsxinc":
            raise SpecError("--components must be an existing trusted project .jsxinc file")
        component_code = component_path.read_text(encoding="utf-8-sig")
        sources["components"] = {"name": component_path.name, "sha256": hashlib.sha256(component_path.read_bytes()).hexdigest()}
    # JSON encoding escapes quotes, backslashes, control characters and Unicode.
    # Input values are data literals only. No eval, Function or shell invocation.
    # Substitute once: a literal '__OUTPUT__' in reference copy must stay text.
    replacements = {
        "__SPEC__": json.dumps(spec, ensure_ascii=True, allow_nan=False),
        "__OUTPUT__": json.dumps(destination.as_posix(), ensure_ascii=True),
        "__SKELETON__": "true" if skeleton else "false",
        "__BUILD_SOURCES__": json.dumps(sources, ensure_ascii=True),
    }
    runner = re.sub(r"__SPEC__|__OUTPUT__|__SKELETON__|__BUILD_SOURCES__", lambda match: replacements[match.group()], RUNNER)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8-sig", newline="\n") as target:
        target.write("#target photoshop\n// Compiled layout; execute in Photoshop, not Python.\n")
        target.write(helper + "\n" + runner)
        # Components are explicit project source code, never inferred from JSON.
        # Function declarations are hoisted; no eval or runtime external include.
        if component_code:
            target.write("\n// Explicit project components\n" + component_code + "\n")
    return {"compiled": str(out), "output_dir": str(destination), "job_id": spec["job_id"],
            "layers": len(spec["layers"]), "skeleton": skeleton, "photoshop_executed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--skeleton", action="store_true", help="Replace image layers with masked placeholders; typography and geometry remain exact")
    parser.add_argument("--output-dir", type=Path, help="New render destination; default: spec directory/rendered")
    parser.add_argument("--components", type=Path, help="Trusted task-authored .jsxinc defining EC_afterLayout(document, spec); runs before save")
    args = parser.parse_args(argv)
    try:
        result = compile_layout(args.spec, args.out, args.output_dir, args.skeleton, args.components)
    except (SpecError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

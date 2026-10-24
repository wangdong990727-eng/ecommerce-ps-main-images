"""Owned synthetic Photoshop regression; never opens user product files."""
from pathlib import Path
import json,sys,hashlib,os
import win32com.client
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'ecommerce-ps-main-images'
sys.path.insert(0,str(S/'scripts'))
import psd_variants as pv
import asset_workflow as aw
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
OUT=args.output.absolute()
OUT.mkdir(parents=True,exist_ok=False)
print('PHOTOSHOP_START',flush=True)
app=win32com.client.Dispatch('Photoshop.Application')
before=[(app.Documents.Item(i).ID, bool(app.Documents.Item(i).Saved)) for i in range(1,app.Documents.Count+1)]
print('PHOTOSHOP_VERSION',app.Version,flush=True)
helper=(S/'scripts/photoshop_helpers.jsxinc').read_text(encoding='utf-8-sig')
fixture=r'''
(function(){var state=EC.begin(),owned=[],out=__OUT__,pattern=__PATTERN__;try{
 var font=null;for(var i=0;i<app.fonts.length;i++)if(/MicrosoftYaHei|NotoSansCJK|SourceHanSans/i.test(app.fonts[i].postScriptName)){font=app.fonts[i].postScriptName;break;}if(!font)throw Error('No tested Chinese font');
 var colours=['EEDCC4','806049'];for(var n=0;n<2;n++){
 var d=app.documents.add(400,500,72,'Owned fixture '+n,NewDocumentMode.RGB,DocumentFill.WHITE);owned.push(d);
 EC.rect(d,'Background',0,0,400,500,colours[n]);
 var l=EC.placeImage(d,pattern,'Product test smart object '+n+' 副本',50,140,300,250,false,0);EC.frameMask(d,l,[50,140,300,250]);
 EC.text(d,'Chinese editable','保暖耳罩',30,80,40,'202020',font);
 EC.text(d,'Variant text','COLOUR '+n,30,450,25,'202020','ArialMT');
 var hidden=EC.rect(d,'Hidden old candidate 副本',0,0,40,40,'FF0000');hidden.visible=false;
 var p=new PhotoshopSaveOptions();p.layers=true;p.embedColorProfile=true;d.saveAs(new File(out+'/colour-'+n+'.psd'),p,true,Extension.LOWERCASE);
 d.close(SaveOptions.DONOTSAVECHANGES);owned.pop();
 }EC.writeJson(out+'/fixture.json',{status:'complete',font:font});
 }finally{for(var i=owned.length-1;i>=0;i--)try{owned[i].close(SaveOptions.DONOTSAVECHANGES);}catch(e){}EC.end(state);}})();
'''
fixture=fixture.replace('__OUT__',json.dumps(str(OUT),ensure_ascii=True)).replace('__PATTERN__',json.dumps(str(S/'assets/demo-pattern.png'),ensure_ascii=True))
jsx=OUT/'fixture.jsx';jsx.write_text('#target photoshop\n'+helper+fixture,encoding='utf-8-sig')
app.DoJavaScriptFile(str(jsx))
assert json.loads((OUT/'fixture.json').read_text(encoding='utf-8-sig'))['status']=='complete'
cfg={'initial_visible':'cream','variants':[{'id':'cream','label':'Synthetic Cream','source_psd':'colour-0.psd'},{'id':'brown','label':'Synthetic Brown','source_psd':'colour-1.psd'}]}
p=OUT/'build.json';p.write_text(json.dumps(cfg),encoding='utf-8')
job=pv.compile_job(p,OUT/'build','build');app.DoJavaScriptFile(job['jsx'])
result=json.loads((OUT/'build/status.json').read_text(encoding='utf-8-sig'))
assert result['status']=='complete',result
assert len(result['variants'])==2
for v in result['variants']:
 assert v['inspection']['text']==2 and v['inspection']['smart']==1 and v['inspection']['linked']==0
 assert any(x['has_user_mask'] for x in v['inspection']['layers'])
 assert any(not x['visible'] and 'Hidden old' in x['name'] for x in v['inspection']['layers'])
# Reopen FROM A COPIED DELIVERY PATH, not the first build path.
delivery=OUT/'delivery';aw.snapshot(OUT/'build/shared-colours.psd',delivery)
shared=delivery/'shared-colours.psd';original_hash=aw.digest(shared)
export_cfg={'source_psd':'delivery/shared-colours.psd','initial_visible':'cream','variants':[{'id':v['id'],'group_id':v['group_id']} for v in result['variants']]}
p=OUT/'export.json';p.write_text(json.dumps(export_cfg),encoding='utf-8')
job=pv.compile_job(p,OUT/'export','export');app.DoJavaScriptFile(job['jsx'])
export=json.loads((OUT/'export/status.json').read_text(encoding='utf-8-sig'))
assert export['status']=='complete',export
for v in export['variants']:assert any(not x['visible'] and 'Hidden old' in x['name'] for x in v['inspection']['layers'])
assert aw.digest(shared)==original_hash
for v in export['variants']:aw.thumbnail(Path(v['jpg']),OUT/(v['id']+'-200.png'))
im0=Image.open(OUT/'export/JPG/cream.jpg').convert('RGB');im1=Image.open(OUT/'export/JPG/brown.jpg').convert('RGB')
assert im0.getpixel((390,10))!=im1.getpixel((390,10))

# Validate edits on a TEST COPY; keep the delivery PSD untouched.
cream=next(v for v in result['variants'] if v['id']=='cream')
text_id=next(x['id'] for x in cream['inspection']['layers'] if x['name']=='Chinese editable')
smart_id=next(x['id'] for x in cream['inspection']['layers'] if x['name'].startswith('Product test'))
with Image.open(S/'assets/demo-pattern.png') as im:replacement_size=im.size
replacement=OUT/'replacement.png';Image.new('RGB',replacement_size,(20,170,90)).save(replacement)
edit=r"""
(function(){var state=EC.begin(),d=null;try{d=app.open(new File(__SHARED__));
function find(p,id){for(var i=0;i<p.layers.length;i++){var l=p.layers[i];if(l.id===id)return l;if(l.typename==='LayerSet'){var f=find(l,id);if(f)return f;}}return null;}
var t=find(d,__TEXT__),im=find(d,__SMART__);if(!t||!im)throw Error('Missing current layer IDs');
t.textItem.contents='修改示例';EC.replaceImage(d,im,__REPLACEMENT__);
var groups=__GROUPS__;for(var a=0;a<groups.length;a++){for(var b=0;b<groups.length;b++)find(d,groups[b].group_id).visible=(a===b);
var jo=new JPEGSaveOptions();jo.quality=11;jo.embedColorProfile=true;d.saveAs(new File(__OUT__+'/edited-'+groups[a].id+'.jpg'),jo,true,Extension.LOWERCASE);}
var po=new PhotoshopSaveOptions();po.layers=true;d.saveAs(new File(__OUT__+'/editable-test.psd'),po,true,Extension.LOWERCASE);
EC.writeJson(__OUT__+'/edit-result.json',{text:t.textItem.contents,text_kind:String(t.kind),smart:EC.layerEvidence(im)});
}finally{if(d)d.close(SaveOptions.DONOTSAVECHANGES);EC.end(state);}})();
"""
for key,value in {'__SHARED__':str(shared),'__TEXT__':text_id,'__SMART__':smart_id,'__REPLACEMENT__':str(replacement),'__GROUPS__':export_cfg['variants'],'__OUT__':str(OUT)}.items():edit=edit.replace(key,json.dumps(value,ensure_ascii=True))
script=OUT/'edit-test.jsx';script.write_text('#target photoshop\n'+helper+edit,encoding='utf-8-sig');app.DoJavaScriptFile(str(script))
edit_result=json.loads((OUT/'edit-result.json').read_text(encoding='utf-8-sig'))
assert edit_result['text']=='修改示例' and edit_result['smart']['has_user_mask']
from PIL import ImageChops
for colour in ['cream','brown']:
    a=Image.open(OUT/('export/JPG/'+colour+'.jpg')).convert('RGB');b=Image.open(OUT/('edited-'+colour+'.jpg')).convert('RGB')
    changed=ImageChops.difference(a,b).getbbox() is not None
    assert changed==(colour=='cream'),(colour,changed)
assert aw.digest(shared)==original_hash

after=[(app.Documents.Item(i).ID,bool(app.Documents.Item(i).Saved)) for i in range(1,app.Documents.Count+1)]
assert before==after,(before,after)
summary={'status':'PASS','photoshop_version':str(app.Version),'fixture_type':'synthetic only, not real product',
 'native_layers_masks_and_visibility':'PASS','chinese_native_text':'PASS','shared_psd_build':'PASS',
 'delivery_path_reopen_id_export':'PASS','shared_original_hash_unchanged':True,'user_docs_preserved':before==after,
 'colour_jpgs_differ':'PASS','thumbnail_generation':'PASS','real_product_visual':'NOT_RUN',
 'native_text_and_image_replacement':'PASS','other_colour_unchanged_after_replacement':'PASS','other_machine':'NOT_RUN'}
(OUT/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False),flush=True)

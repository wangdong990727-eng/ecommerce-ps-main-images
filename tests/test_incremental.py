"""Technical regression only. Does not claim Photoshop or product acceptance."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'ecommerce-ps-main-images/scripts'
sys.path.insert(0,str(S))
import asset_workflow as aw
import psd_variants as pv
import render_layout as rl
import icon_badges as ib
import xml.etree.ElementTree as ET


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.r=Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def png(self,name,value=(20,30,40,255),size=(8,8),mode='RGBA'):
        p=self.r/name;Image.new(mode,size,value).save(p);return p
    def test_snapshot_is_exact_and_never_overwrites(self):
        p=self.r/'user.psd';p.write_bytes(b'USER-EDIT-CURRENT')
        result=aw.snapshot(p,self.r/'snapshot')
        self.assertEqual(aw.digest(p),result['sha256'])
        self.assertEqual((self.r/'snapshot/user.psd').read_bytes(),p.read_bytes())
        with self.assertRaises(ValueError):aw.snapshot(p,self.r/'snapshot')
    def test_diff_permits_only_declared_edit(self):
        a=self.png('a.png');b=self.png('b.png');m=self.png('mask.png',0,mode='L')
        with Image.open(b) as im:im.putpixel((0,0),(250,0,0,255));im.save(b)
        with Image.open(m) as im:im.putpixel((0,0),255);im.save(m)
        self.assertEqual(aw.protected_diff(a,b,m,self.r/'ok.json')['result'],'PASS')
    def test_diff_detects_face_or_product_change_outside_mask(self):
        a=self.png('a.png');b=self.png('b.png',(20,30,41,255));m=self.png('mask.png',0,mode='L')
        result=aw.protected_diff(a,b,m,self.r/'bad.json')
        self.assertEqual(result['result'],'FAIL');self.assertEqual(result['changed_protected_pixels'],64)
    def test_diff_detects_alpha_change(self):
        a=self.png('a.png');b=self.png('b.png',(20,30,40,254));m=self.png('m.png',0,mode='L')
        self.assertEqual(aw.protected_diff(a,b,m,self.r/'alpha.json')['result'],'FAIL')
    def test_diff_rejects_unregistered_canvas(self):
        a=self.png('a.png');b=self.png('b.png',size=(7,8));m=self.png('m.png',0,mode='L')
        with self.assertRaises(ValueError):aw.protected_diff(a,b,m,self.r/'mismatch.json')
    def test_diff_rejects_all_white_or_grey_mask(self):
        a=self.png('a.png');b=self.png('b.png')
        for value in (255,128):
            m=self.png('m.png',value,mode='L')
            with self.assertRaises(ValueError):aw.protected_diff(a,b,m,self.r/'invalid.json')
    def test_diff_rejects_jpeg(self):
        a=self.png('a.png');b=self.png('b.png');m=self.png('m.png',0,mode='L')
        j=self.r/'a.jpg';Image.open(a).convert('RGB').save(j)
        with self.assertRaises(ValueError):aw.protected_diff(j,b,m,self.r/'jpeg.json')
    def test_thumbnail_200_preserves_ratio_and_source(self):
        a=self.png('a.png',size=(300,450));h=aw.digest(a);out=self.r/'small.png'
        self.assertEqual(aw.thumbnail(a,out)['size'],[200,300]);self.assertEqual(h,aw.digest(a))
        with self.assertRaises(ValueError):aw.thumbnail(a,out)
    def config(self,data):
        p=self.r/'variants.json';p.write_text(json.dumps(data),encoding='utf-8');return p
    def test_export_compiles_ids_not_colour_names(self):
        (self.r/'shared.psd').write_bytes(b'fixture-not-a-real-psd')
        p=self.config({'source_psd':'shared.psd','variants':[{'id':'a','group_id':18},{'id':'b','group_id':31}]})
        result=pv.compile_job(p,self.r/'job','export')
        script=Path(result['jsx']).read_text(encoding='utf-8-sig')
        self.assertIn('groupById',script);self.assertIn('"group_id": 31',script)
        self.assertFalse(result['photoshop_executed'])
        with self.assertRaises(ValueError):pv.compile_job(p,self.r/'job','export')
    def test_export_rejects_duplicate_ids(self):
        (self.r/'shared.psd').write_bytes(b'fixture')
        p=self.config({'source_psd':'shared.psd','variants':[{'id':'a','group_id':9},{'id':'b','group_id':9}]})
        with self.assertRaises(ValueError):pv.compile_job(p,self.r/'job','export')
    def test_build_rejects_escaped_source(self):
        p=self.config({'variants':[{'id':'a','source_psd':'../private.psd'}]})
        with self.assertRaises(ValueError):pv.compile_job(p,self.r/'job','build')
    def test_variant_rejects_invalid_ids_and_visibility(self):
        (self.r/'a.psd').write_bytes(b'fixture')
        for data in ({'variants':[{'id':'../bad','source_psd':'a.psd'}]},
                     {'initial_visible':'absent','variants':[{'id':'a','source_psd':'a.psd'}]}):
            with self.assertRaises(ValueError):pv.compile_job(self.config(data),self.r/'job','build')
    def test_existing_layout_compiler_still_builds_native_job(self):
        p=ROOT/'ecommerce-ps-main-images/templates/layout-spec.example.json'
        result=rl.compile_layout(p,self.r/'old.jsx',self.r/'rendered')
        self.assertFalse(result['photoshop_executed'])
        self.assertEqual(result['layers'],4)
    def test_icons_share_grid_stroke_and_no_embedded_text(self):
        p=ROOT/'ecommerce-ps-main-images/templates/icon-theme.example.json'
        ib.build(p,self.r/'icons',demo=True)
        icons=list((self.r/'icons').glob('*.svg'));self.assertEqual(len(icons),8)
        for svg in icons:
            root=ET.fromstring(svg.read_text(encoding='utf-8'))
            self.assertEqual(root.attrib['viewBox'],'0 0 128 128')
            self.assertEqual(root.find('{http://www.w3.org/2000/svg}g').attrib['stroke-width'],'2')
            self.assertFalse(root.findall('.//{http://www.w3.org/2000/svg}text'))
    def test_icons_require_fact_sources_for_product_use(self):
        p=ROOT/'ecommerce-ps-main-images/templates/icon-theme.example.json'
        with self.assertRaises(ValueError):ib.build(p,self.r/'icons',demo=False)
    def test_icons_reject_unknown_features(self):
        p=self.config({'style':{'color':'#000000','stroke':2,'corner_radius':14},'features':[{'id':'guaranteed_heating','label':'HEAT'}]})
        with self.assertRaises(ValueError):ib.build(p,self.r/'icons',demo=True)


if __name__=='__main__':unittest.main()

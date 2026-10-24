#target photoshop
(function(){
var scriptDir=new File($.fileName).parent;
$.evalFile(new File(scriptDir.fsName+'/photoshop_helpers.jsxinc'));
var state=EC.begin(),before=[],owned=[],root=new Folder(Folder.temp.fsName+'/ecommerce-ps-smoke-'+new Date().getTime());
root.create();var log=new File(Folder.temp.fsName+'/ecommerce-skill-smoke-status.txt');log.encoding='UTF8';log.open('w');
function record(t){log.writeln(t);log.close();log.open('a');}
function forget(d){for(var k=owned.length-1;k>=0;k--)if(owned[k].id===d.id){owned.splice(k,1);break;}d.close(SaveOptions.DONOTSAVECHANGES);}
for(var i=0;i<app.documents.length;i++)before.push({id:app.documents[i].id,saved:app.documents[i].saved});
try{
 record('OUTPUT '+root.fsName);
 var source=app.documents.add(400,400,72,'Smoke source',NewDocumentMode.RGB,DocumentFill.WHITE);owned.push(source);
 EC.rect(source,'Source blue',40,40,320,320,'92B7CB');
 var po=new PhotoshopSaveOptions();po.layers=true;var sourcePath=root.fsName+'/source.psd';source.saveAs(new File(sourcePath),po,true,Extension.LOWERCASE);forget(source);
 var d=app.documents.add(1200,1600,72,'Smoke editable',NewDocumentMode.RGB,DocumentFill.WHITE);owned.push(d);
 EC.rect(d,'Background',0,0,1200,1600,'F6F0E9');
 var so=EC.placeImage(d,sourcePath,'Product embedded',120,320,960,960,false,0);
 d.activeLayer=so;d.selection.select([[140,340],[1060,340],[1060,1260],[140,1260]]);
 var a=new ActionDescriptor(),r=new ActionReference();a.putClass(charIDToTypeID('Nw  '),charIDToTypeID('Chnl'));r.putEnumerated(charIDToTypeID('Chnl'),charIDToTypeID('Chnl'),charIDToTypeID('Msk '));a.putReference(charIDToTypeID('At  '),r);a.putEnumerated(charIDToTypeID('Usng'),charIDToTypeID('UsrM'),charIDToTypeID('RvlS'));executeAction(charIDToTypeID('Mk  '),a,DialogModes.NO);d.selection.deselect();
 EC.text(d,'Title editable','EDITABLE TITLE',100,160,64,'29496E');
 EC.text(d,'Size editable','Length 27 cm',100,1450,44,'29496E');
 EC.groupLayers(d);var pair=EC.savePair(d,root.fsName,'before');forget(d);
 d=app.open(new File(pair.psd));owned.push(d);var texts=0,smarts=0,masks=0,sizeLayer=null;
 function walk(p){for(var j=0;j<p.layers.length;j++){var l=p.layers[j];if(l.typename==='LayerSet'){walk(l);continue;}if(l.kind===LayerKind.TEXT){texts++;if(l.name==='Size editable')sizeLayer=l;}if(l.kind===LayerKind.SMARTOBJECT){smarts++;var ref=new ActionReference();ref.putIdentifier(charIDToTypeID('Lyr '),l.id);var desc=executeActionGet(ref);if(desc.hasKey(stringIDToTypeID('hasUserMask'))&&desc.getBoolean(stringIDToTypeID('hasUserMask')))masks++;}}}
 walk(d);if(texts!==2||smarts!==1||masks!==1||!sizeLayer)throw Error('Native layer verification failed');
 sizeLayer.textItem.contents='Length 28 cm';EC.savePair(d,root.fsName,'after');forget(d);
 for(i=0;i<before.length;i++){var found=false;for(var j=0;j<app.documents.length;j++)if(app.documents[j].id===before[i].id){found=true;if(app.documents[j].saved!==before[i].saved)throw Error('Existing document saved state changed');}if(!found)throw Error('Existing document missing');}
 record('VERIFIED text='+texts+' embedded='+smarts+' masks='+masks+' edit=27_to_28 existing_docs='+before.length);
 record('COMPLETE');
}catch(e){record('ERROR '+e.message+' line '+e.line);}finally{for(var k=owned.length-1;k>=0;k--)try{owned[k].close(SaveOptions.DONOTSAVECHANGES);}catch(ig){}EC.end(state);log.close();}
})();

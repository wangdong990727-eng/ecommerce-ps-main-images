"""Diagnostic contact longboard; no source images are changed. Requires Pillow."""
import argparse,json,re
from pathlib import Path
from PIL import Image,ImageOps

def natural(path):
    return [int(v) if v.isdigit() else v.casefold() for v in re.split(r'(\d+)',path.name)]

def stitch(paths,width):
    if not paths:raise ValueError('No images matched; check directory and pattern')
    images=[];rows=[];y=0
    for p in paths:
        with Image.open(p) as src:
            im=ImageOps.exif_transpose(src).convert('RGB')
            native=im.size;h=round(im.height*width/im.width)
            im=im.resize((width,h),Image.Resampling.LANCZOS)
        images.append(im);rows.append({'file':str(p.resolve()),'native_size':native,'y':y,'height':h});y+=h
    board=Image.new('RGB',(width,y),'white')
    for im,row in zip(images,rows):board.paste(im,(0,row['y']))
    return board,rows

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--pattern',default='*.jpg');parser.add_argument('--width',type=int,default=750)
    parser.add_argument('--result',type=Path);parser.add_argument('--result-pattern',default='*.jpg')
    args=parser.parse_args()
    if args.width<1:parser.error('width must be positive')
    args.output.mkdir(parents=True,exist_ok=True)
    ref,rows=stitch(sorted(args.reference.glob(args.pattern),key=natural),args.width)
    ref.save(args.output/'reference_full.jpg',quality=95)
    data={'reference':rows,'width':args.width,'purpose':'whole-layout diagnostic; originals remain unchanged'}
    if args.result:
        result,other=stitch(sorted(args.result.glob(args.result_pattern),key=natural),args.width)
        result.save(args.output/'result_full.jpg',quality=95)
        # Equal widths, independent vertical lengths: do not stretch one page to force alignment.
        pair=Image.new('RGB',(args.width*2+24,max(ref.height,result.height)),'#eeeeee')
        pair.paste(ref,(0,0));pair.paste(result,(args.width+24,0))
        pair.save(args.output/'whole_comparison.jpg',quality=95);data['result']=other
        data['comparison_segments']=[]
        for i,y in enumerate(range(0,pair.height,2400),1):
            name=f'comparison_{i:02}.jpg'
            pair.crop((0,y,pair.width,min(y+2400,pair.height))).save(args.output/name,quality=95)
            data['comparison_segments'].append({'file':name,'y':y})
    (args.output/'stitch_index.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'reference_images':len(rows),'reference_size':ref.size,'result_images':len(data.get('result',[]))}))

if __name__=='__main__':main()

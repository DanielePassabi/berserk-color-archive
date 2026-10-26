"""Offline integrity, coverage, provenance and deploy-package validation."""
from pathlib import Path
import json,hashlib,re
from bs4 import BeautifulSoup
from PIL import Image
from import_archive import ROOT,original

def verify():
 c=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'));ui=json.loads((ROOT/'data/site-catalog.json').read_text(encoding='utf-8'))
 failures=[];checked=0
 for a in c['assets'].values():
  if a['status']!='downloaded':failures.append(a['id']+': '+a['status']);continue
  path=ROOT/a['path']
  if not path.exists() or path.stat().st_size!=a['bytes']:failures.append(a['id']+': size mismatch');continue
  if hashlib.file_digest(path.open('rb'),'sha256').hexdigest()!=a['sha256']:failures.append(a['id']+': checksum mismatch')
  side=json.loads(path.with_suffix(path.suffix+'.json').read_text(encoding='utf-8'))
  if not side.get('attribution') or not side.get('sources'):failures.append(a['id']+': missing provenance')
  checked+=1
 expected=set()
 for name,selector in [('art','.artGallery img'),('manga','li.gallerybox img, aside img')]:
  s=BeautifulSoup((ROOT/f'data/sources/{name}.html').read_text(encoding='utf-8'),'html.parser')
  for img in s.select(selector):
   a=img.find_parent('a');src=img.get('src','')
   if a and a.get('href','').startswith('/File:') and src.startswith('https://static.jojowiki.com/images/'):
    expected.add(original(src))
 actual={a['originalUrl']for a in c['assets'].values()}
 if expected!=actual:failures.append('Source coverage mismatch: '+str(len(expected-actual))+' missing; '+str(len(actual-expected))+' extra')
 for e in ui['entries']:
  if len(e['assetIds'])>1:failures.append(e['id']+': more than one main version')
  if any(aid not in ui['assets'] for aid in e['assetIds']):failures.append(e['id']+': missing asset reference')
 for a in ui['assets'].values():
  path=ROOT/'dist'/a['path']
  if not a['path'].startswith('assets/images/') or '..'in a['path']:failures.append('Invalid site asset path')
  if not path.exists():failures.append(a['id']+': missing packaged image');continue
  with Image.open(path) as im:
   if im.size!=(a['width'],a['height']):failures.append('Web dimensions mismatch')
   im.verify()
  if path.stat().st_size!=a['bytes'] or hashlib.file_digest(path.open('rb'),'sha256').hexdigest()!=a['sha256']:failures.append('Web integrity mismatch')
 html=BeautifulSoup((ROOT/'dist/index.html').read_text(encoding='utf-8'),'html.parser')
 for t in html.select('script[src],link[href]'):
  url=t.get('src') or t.get('href')
  if url.startswith(('http:','https:','//')):failures.append('External automatic dependency')
  elif not (ROOT/'dist'/url).exists():failures.append('Missing dependency '+url)
 if ui['defaultProgress']!=0:failures.append('New reader default is not zero')
 first={aid for e in ui['entries'] if e.get('chapter',{}) and e['chapter']['key']=='prologue-1' and e['section']=='chapters' for aid in e['assetIds']}
 if len(first)!=3:failures.append('First chapter should have 3 selected pages; got '+str(len(first)))
 total=sum(p.stat().st_size for p in (ROOT/'dist').rglob('*') if p.is_file())
 if total>=1_000_000_000:failures.append('Site exceeds 1 GB')
 report={'passed':not failures,'originalsChecked':checked,'sourceCoverageFiles':len(expected),'siteImagesChecked':len(ui['assets']),'firstChapterPages':len(first),'defaultProgress':ui['defaultProgress'],'packageBytes':total,'failures':failures}
 (ROOT/'reports/verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report,indent=2));return not failures
if __name__=='__main__':raise SystemExit(0 if verify() else 1)

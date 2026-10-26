"""Import Frosti's two galleries; sequential, resumable, originals only."""
from pathlib import Path
import re, json, hashlib, time, unicodedata, sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, unquote
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
UA='BerserkLocalArchive/1.0 (personal offline collection; sequential requests)'
ART='https://jojowiki.com/User:Fr0stiFusionZ/Berserk_Art_Gallery'
MANGA='https://jojowiki.com/User:Fr0stiFusionZ/Berserk_Gallery'
S=requests.Session(); S.headers.update({'User-Agent':UA})
last=0; policies={}
def get(url):
 global last
 host=urlsplit(url).netloc
 if host not in policies:
  r=S.get('https://'+host+'/robots.txt',timeout=45)
  if r.status_code not in (200,404,410): raise RuntimeError('Cannot establish robots policy '+str(r.status_code))
  rp=RobotFileParser();rp.parse(r.text.splitlines() if r.status_code==200 else [])
  policies[host]=rp
  (ROOT/'data/sources'/ (host+'-robots.txt')).write_text(r.text,encoding='utf-8')
 rp=policies[host]
 if not rp.can_fetch(UA,url):raise RuntimeError('Disallowed by robots.txt')
 delay=max(1.0,rp.crawl_delay(UA) or 0)
 rate=rp.request_rate(UA)
 if rate:delay=max(delay,rate.seconds/rate.requests)
 for attempt in range(3):
  time.sleep(max(0,delay-(time.monotonic()-last)))
  last=time.monotonic()
  r=S.get(url,timeout=(20,120))
  if r.status_code in (429,503):
   retry=r.headers.get('Retry-After','60')
   try: pause=float(retry)
   except ValueError:
    from email.utils import parsedate_to_datetime
    try:pause=max(0,(parsedate_to_datetime(retry)-datetime.now(timezone.utc)).total_seconds())
    except Exception:pause=60
   time.sleep(max(pause,30*(attempt+1)));continue
  r.raise_for_status();return r
 raise RuntimeError('Server asked to slow down; retries exhausted')
def clean(e):
 if not e:return ''
 e=BeautifulSoup(str(e),'html.parser')
 for t in e.select('sup.reference'):t.decompose()
 return re.sub(r'\s+',' ',e.get_text(' ',strip=True)).strip()
def slug(t):
 t=unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().lower()
 return re.sub('[^a-z0-9]+','-',t).strip('-')[:95] or 'illustration'
def original(src):
 if '/images/thumb/' in src:
  return src.replace('/images/thumb/','/images/',1).rsplit('/',1)[0]
 return src
def date_key(text):
 t=re.sub(r'\[.*?\]','',text).strip()
 t=re.split(r'(?:Date )?Revealed:',t)[0].strip()
 for fmt in ('%B %d, %Y','%B %d %Y','%b %d, %Y','%b, %d %Y','%B %Y','%b, %Y','%b %Y','%Y'):
  try:return datetime.strptime(t,fmt).strftime('%Y-%m-%d')
  except ValueError:pass
 y=re.search(r'(?:19|20)\d{2}',t)
 return (y.group()+'-01-01') if y else None
# Volume numbering follows the single Japanese tankobon / Italian Collection, not Maximum or Deluxe.
volume_map={}
vs=BeautifulSoup((ROOT/'data/sources/volumes.html').read_text(encoding='utf-8'),'html.parser').get_text(' ',strip=True)
for v,block in enumerate(vs.split('Book ID #')[1:],1):
 for ep in re.findall(r'\.\s*(\d{3}):',block):volume_map[int(ep)]=v
volume_map.update({n:43 for n in range(374,383)})
volume_map.pop(83,None)
# Recent volumes are documented separately in mapping-sources.json; unverified episodes remain unassigned.
def chapter(text):
 p=re.search(r'Prologue\s*(\d+)',text,re.I)
 r=re.search(r'REVENGE\s*(\d+)',text,re.I)
 e=re.search(r'Episode\s*:?\s*(\d+)',text,re.I)
 if p:
  n=int(p.group(1));return {'key':f'prologue-{n}','order':n,'volume':1,'label':['Il guerriero nero','Il marchio','Gli angeli custodi dei desideri (1)'][n-1] if n<=3 else f'Prologo {n}'}
 if r:
  n=int(r.group(1));v=2 if n<=5 else 3 if n<=9 else 4 if n<=14 else 5
  return {'key':f'revenge-{n}','order':n+3,'volume':v,'label':f"L’età dell’oro ({n-8})" if n>=9 else f'REVENGE {n}'}
 if e:
  n=int(e.group(1));return {'key':f'episode-{n:03}','order':n+19,'volume':volume_map.get(n),'label':f'Episodio {n:03}'}
 return None

def build():
 assets={};entries=[];missing=[]
 def add_image(img,entry,role):
  a=img.find_parent('a');href=a.get('href','') if a else ''
  if not href.startswith('/File:'):return
  src=img.get('src','')
  if not src.startswith('https://static.jojowiki.com/images/'):return
  url=original(src);name=unquote(urlsplit(url).path.rsplit('/',1)[-1]);aid=hashlib.sha256(url.encode()).hexdigest()[:16]
  if aid not in assets:
   ch=entry.get('chapter');year=(entry.get('sortDate') or 'undated')[:4]
   folder=f'chapters/volume-{ch["volume"]:02}/{ch["key"]}' if ch and ch.get('volume') else f'extras/{year}'
   ext=Path(name).suffix.lower()
   assets[aid]={'id':aid,'originalName':name,'originalUrl':url,'filePageUrl':urljoin(ART,href),'path':f'assets/originals/{folder}/{slug(Path(name).stem)}--{aid[:8]}{ext}','status':'pending','occurrences':[]}
  assets[aid]['occurrences'].append({'entryId':entry['id'],'role':role})
  if aid not in entry['assetIds']:entry['assetIds'].append(aid)
 for source,file in [(ART,'art.html'),(MANGA,'manga.html')]:
  s=BeautifulSoup((ROOT/'data/sources'/file).read_text(encoding='utf-8'),'html.parser')
  if source==ART:
   for idx,row in enumerate(s.select('.artGallery')):
    st=row.select_one('.artGallery-source')
    if not st:continue
    desc=clean(st);dt=clean(row.select_one('.artGallery-date'));ch=chapter(desc)
    # Episode association is retained for extras, but only actual pages enter chapter groups.
    ispage=bool(re.search(r'Intro Color|Color Page|Inside Illustration|Pages not in Volume',desc,re.I))
    other=bool(re.search(r'King Wolf|King of Wolves|Japan \(|Duranki|Giganto Maxia',desc,re.I)) and 'Berserk' not in desc
    entry={'id':f'art-{idx:04}','description':desc,'date':dt,'sortDate':date_key(dt),'dateApproximate':not bool(re.fullmatch(r'\w+ \d{1,2}, \d{4}',dt)), 'section':'other' if other else 'chapters' if ch and ispage else 'extras','chapter':ch,'sourcePage':source,'sourceLinks':[a['href'] for a in st.select('a[href]') if a['href'].startswith('http')],'assetIds':[]}
    for role,selector in [('artwork','.artGallery-image img'),('source-scan','.artGallery-image2 img')]:
     for img in row.select(selector):add_image(img,entry,role)
    for a in row.select('a.new'):
     missing.append({'entryId':entry['id'],'file':clean(a),'sourcePage':source,'reason':'File missing/red link in source gallery','url':urljoin(source,a.get('href',''))})
    entries.append(entry)
  else:
   for idx,box in enumerate(s.select('li.gallerybox')+s.select('aside')):
    desc=clean(box.select_one('.gallerytext'));heading=box.find_previous(['h2','h3']);section=clean(heading)
    if box.name=='aside':desc=clean(box.select_one('.pi-title'))
    imgs=box.select('img')
    if not imgs:continue
    # Captions are kept verbatim; uncertain publication dates are never invented.
    dateMatch=re.search(r'\(([^()]*\d{4}[^()]*)\)',desc)
    dt=dateMatch.group(1) if dateMatch else ''
    entry={'id':f'manga-{idx:04}','description':(section+' — '+desc).strip(' —'),'date':dt,'sortDate':date_key(dt),'dateApproximate':True,'section':'extras','chapter':None,'sourcePage':source,'sourceLinks':[],'assetIds':[]}
    for img in imgs:add_image(img,entry,'supplementary-gallery')
    entries.append(entry)
 out={'schemaVersion':1,'generatedAt':datetime.now(timezone.utc).isoformat(),'defaultProgress':19,'progressLabel':"L’età dell’oro 8 · Collection 5",'attribution':{'curator':'Fr0stiFusionZ / @Frosti811','credit':'Kentaro Miura / Hakusensha; dal 2022 Studio Gaga, supervisione Kouji Mori. Altri autori e staff secondo le fonti originali.','rights':'Opere protette: nessuna licenza di redistribuzione implicita. Crediti scansioni specifici nelle pagine fonte.','sourcePages':[ART,MANGA]},'entries':entries,'assets':assets,'missingSourceFiles':missing}
 oldpath=ROOT/'data/catalog.json'
 if oldpath.exists():
  old=json.loads(oldpath.read_text(encoding='utf-8'))
  for aid,a in assets.items():
   prior=old.get('assets',{}).get(aid)
   if prior and prior.get('status')=='downloaded' and (ROOT/prior['path']).exists():
    occurrences=a['occurrences'];a.update(prior);a['occurrences']=occurrences
 (ROOT/'data/catalog.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('CATALOG',len(entries),'entries',len(assets),'originals',len(missing),'missing source links',flush=True)
 return out

def atomic_text(path,text):
 tmp=path.with_suffix(path.suffix+'.tmp')
 tmp.write_text(text,encoding='utf-8');tmp.replace(path)

def save(catalog):
 atomic_text(ROOT/'data/catalog.json',json.dumps(catalog,ensure_ascii=False,indent=2))
 atomic_text(ROOT/'data/catalog.js','window.BERSERK_ARCHIVE = '+json.dumps(catalog,ensure_ascii=False)+';\n')
 failed=[a for a in catalog['assets'].values() if a['status']=='failed']
 stats={'totalOriginals':len(catalog['assets']),'downloaded':sum(a['status']=='downloaded' for a in catalog['assets'].values()),'failed':len(failed),'bytes':sum(a.get('bytes',0) for a in catalog['assets'].values()),'missingSourceLinks':len(catalog['missingSourceFiles'])}
 (ROOT/'reports/download-report.json').write_text(json.dumps({'stats':stats,'failures':failed,'missingSourceFiles':catalog['missingSourceFiles']},ensure_ascii=False,indent=2),encoding='utf-8')
 return stats

def download(c):
 for i,a in enumerate(c['assets'].values(),1):
  p=ROOT/a['path'];p.parent.mkdir(parents=True,exist_ok=True)
  if a['status']=='downloaded' and p.exists():continue
  try:
   r=get(a['originalUrl'])
   if not r.headers.get('Content-Type','').startswith('image/'):raise ValueError('Response is not an image')
   tmp=p.with_suffix(p.suffix+'.part');tmp.write_bytes(r.content)
   with Image.open(tmp) as im:
    width,height=im.size;fmt=im.format;im.verify()
   tmp.replace(p)
   a.update(status='downloaded',width=width,height=height,format=fmt,bytes=p.stat().st_size,sha256=hashlib.sha256(r.content).hexdigest(),downloadedAt=datetime.now(timezone.utc).isoformat(),contentType=r.headers.get('Content-Type'),etag=r.headers.get('ETag'),lastModified=r.headers.get('Last-Modified'))
   a.pop('error',None)
   p.with_suffix(p.suffix+'.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
  except Exception as e:
   a.update(status='failed',error=str(e));print('FAILED',i,a['originalName'],str(e),flush=True)
  if i%10==0:print('PROGRESS',i,len(c['assets']),save(c),flush=True)
 save(c)
 print('DONE',save(c),flush=True)
if __name__=='__main__':
 if '--build' in sys.argv:save(build())
 else:download(json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8')))

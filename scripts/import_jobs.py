#!/usr/bin/env python3
"""Free public Greenhouse and Lever feed importer; standard library only."""
import datetime as dt, html, json, os, re, time, urllib.parse, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'sources.json'; DEST=ROOT/'data'/'jobs.json'
UA='InternshipHQ/1.0 (personal noncommercial job tracker)'
KEYWORDS=re.compile(r'\b(intern(ship)?|summer analyst|summer associate|early career program)\b',re.I)
FIELDS=re.compile(r'finance|financial|account|audit|tax|bank|invest|consult|advisory|risk|underwrit|treasury|asset management|wealth|econom|valuation|fp&a|strategy|corporate development|capital market|credit|insurance|actuar',re.I)
YEARS=re.compile(r'\b(2027|2028)\b')
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=20) as r: return json.load(r)
def plain(s): return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s or ''))).strip()
def matched(title,description,config):
    title=plain(title); desc=plain(description)
    if not KEYWORDS.search(title): return False
    if not FIELDS.search(title+' '+desc[:2500]): return False
    years=YEARS.findall(title+' '+desc[:3000]); return bool(set(years)&set(config['years']))
def year(title,desc):
    m=YEARS.search(title) or YEARS.search(desc[:3000]); return m.group(1) if m else ''
def greenhouse(board):
    data=get('https://boards-api.greenhouse.io/v1/boards/'+urllib.parse.quote(board)+'/jobs?content=true')
    for j in data.get('jobs',[]):
        loc=(j.get('location') or {}).get('name','')
        yield {'company':'','role':j.get('title',''),'location':loc,'url':j.get('absolute_url',''), 'description':plain(j.get('content','')),'source':'Greenhouse'}
def lever(board):
    data=get('https://api.lever.co/v0/postings/'+urllib.parse.quote(board)+'?mode=json')
    for j in data:
        loc=(j.get('categories') or {}).get('location','')
        desc=plain(j.get('descriptionPlain') or j.get('description',''))
        yield {'company':'','role':j.get('text',''),'location':loc,'url':j.get('hostedUrl',''), 'description':desc,'source':'Lever'}
def main():
    cfg=json.loads(CONFIG.read_text()); existing=json.loads(DEST.read_text()) if DEST.exists() else []
    byurl={j['url'].rstrip('/').lower():j for j in existing if j.get('url')}
    today=dt.datetime.now(dt.timezone.utc).date().isoformat(); scanned=0; added=0; errors=[]
    for source in cfg.get('sources',[]):
        if not source.get('enabled',False): continue
        try:
            provider=source['provider'].lower(); board=source['board']; company=source['company']
            feed=greenhouse(board) if provider=='greenhouse' else lever(board) if provider=='lever' else []
            for item in feed:
                scanned+=1
                if not matched(item['role'],item['description'],cfg): continue
                url=item['url']; key=url.rstrip('/').lower()
                if not url.startswith('https://') or key in byurl: continue
                record={'id':'auto-'+str(abs_hash(url)), 'company':company,'role':item['role'],
                    'year':year(item['role'],item['description']),'location':item['location'],
                    'deadline':'Not listed','priority':'2','status':'Not applied', 'url':url,
                    'email':'','action':'','evidence':'','notes':'Auto-imported from a public employer job feed; verify eligibility and deadline.',
                    'source':item['source'],'verified':'Discovered '+today,'discovered':today}
                byurl[key]=record; added+=1
        except Exception as e:
            errors.append(f"{source.get('company','?')}: {type(e).__name__}: {str(e)[:160]}")
        time.sleep(.4)
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(sorted(byurl.values(),key=lambda j:(j.get('discovered',''),j.get('company','')),reverse=True),indent=2,ensure_ascii=False)+'\n')
    print(f'Scanned {scanned} postings; added {added}; total {len(byurl)}; errors {len(errors)}')
    for e in errors: print('WARNING',e)
    if errors and not scanned: print('No feeds could be read. Check configured board IDs and provider availability.')
def abs_hash(s):
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()[:16]
if __name__=='__main__': main()

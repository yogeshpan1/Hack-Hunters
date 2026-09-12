"""Rebuild the college catalogue from the supplied CSV and PDF tables.

Install pymupdf only when rebuilding this checked-in data file. It is not needed
by the application. PDF page numbers refer to file pages, not printed folios.
"""
import csv
import json
import re
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
UG = 'ICK UG Brochure 2026.pdf'
PG = 'ICK PG Brochure.pdf'
UG_PROGRAMMES = [
    (99, 'BSc (Hons) Computing', 'Computing', ''),
    (101, 'BSc (Hons) Computing with Artificial Intelligence', 'Computing', ''),
    (103, 'BSc (Hons) Computer Networking and IT Security', 'Computing', ''),
    (105, 'BSc (Hons) Multimedia Technologies', 'Computing', ''),
    (107, 'BA (Hons) Business Administration — International Business', 'Business', 'International Business'),
    (109, 'BA (Hons) Business Administration — Events and Tourism Management', 'Business', 'Events and Tourism Management'),
    (111, 'BA (Hons) Business Administration — Advertising and Marketing', 'Business', 'Advertising and Marketing'),
    (113, 'BA (Hons) Business Administration — Digital Business Management', 'Business', 'Digital Business Management'),
    (115, 'BA (Hons) Accounting and Finance', 'Business', ''),
]
PG_PROGRAMMES = [
    (39, 'MBA', 'International Business Management'), (40, 'MBA', 'Project Management'),
    (43, 'MBA', 'Advertising and Marketing'), (44, 'MBA', 'Digital Media'),
    (47, 'MBA', 'Events and Tourism'), (48, 'MBA', 'Cyber Security'),
    (55, 'MSc IT and Applied Security', 'Data Analytics'),
    (56, 'MSc IT and Applied Security', 'Artificial Intelligence'),
    (59, 'MSc IT and Applied Security', 'Software Engineering'),
    (60, 'MSc IT and Applied Security', 'DevOps Engineering'),
    (63, 'MSc IT and Applied Security', 'Cyber Threat Intelligence'),
]

def nearby(words, y, tolerance=5):
    return sorted([w for w in words if abs(w[1]-y)<tolerance],key=lambda w:w[0])

def ug_curriculum(page):
    words=page.get_text('words')
    years=[]
    for w in words:
        if w[4]=='Year':
            row=nearby(words,w[1]); number=next(x[4] for x in row if x[4] in ['1','2','3'])
            years.append((w[1],int(number)))
    entries=[]
    for word in words:
        if not re.fullmatch(r'[A-Z]{2}[0-9][A-Z0-9]{3,4}',word[4]): continue
        row=nearby(words,word[1])
        credits=[w for w in row if w[4] in ['15','30','60'] and w[0]>word[2]]
        if not credits: raise ValueError(f'Missing credit value for {word[4]}')
        credit=max(credits,key=lambda w:w[0])
        name=' '.join(w[4] for w in row if word[2]<w[0]<credit[0])
        year=max((y for y in years if y[0]<word[1]),key=lambda y:y[0])[1]
        if not name: raise ValueError(f'Missing module title for {word[4]}')
        entries.append({'code':word[4],'name':name,'year':year,'credits':int(credit[4])})
    return sorted(entries,key=lambda x:(x['year'],next(w[1] for w in words if w[4]==x['code'])))

def pg_curriculum(page, award):
    words=page.get_text('words');semesters=[]
    for word in words:
        if word[4]=='Semester':
            numbers=[w for w in nearby(words,word[1]) if w[4] in ['1','2','3','4'] and w[0]>word[2] and w[0]-word[2]<30]
            if numbers: semesters.append((word[1],int(numbers[0][4])))
    end_y=min([w[1] for w in words if w[4]=='Career']+[page.rect.height])
    bullets=sorted([w for w in words if w[4]=='•' and semesters and min(y for y,_ in semesters)<w[1]<end_y],key=lambda w:w[1])
    entries=[]
    for i,bullet in enumerate(bullets):
        semester=max((x for x in semesters if x[0]<bullet[1]),key=lambda x:x[0])[1]
        later=[x[0] for x in semesters if x[0]>bullet[1]]
        end=min(([bullets[i+1][1]] if i+1<len(bullets) else [])+later+[bullet[1]+35])
        credit_words=[w for w in nearby(words,bullet[1],5) if w[4] in ['10','20','60'] and w[0]>bullet[0]+150]
        credit=max(credit_words,key=lambda w:w[0]) if credit_words else None
        right=credit[0]-3 if credit else page.rect.width*.86
        selected=sorted([w for w in words if bullet[0]+5<w[0]<right and bullet[1]-3<=w[1]<end-3],key=lambda w:(round(w[1]/3),w[0]))
        name=' '.join(w[4] for w in selected)
        if not name or name.startswith('Career'): continue
        entries.append({'code':None,'name':name,'semester':semester,'credits':int(credit[4]) if credit else None,'optional_group':'Choose one final-semester route' if award=='MBA' and semester==4 else None})
    return entries

def main():
    programmes=[]
    with pymupdf.open(ROOT/UG) as doc:
        for page,name,department,specialization in UG_PROGRAMMES:
            programmes.append({'id':len(programmes)+1,'name':name,'department':department,'award':name.split(' — ')[0],'level':'Undergraduate','specialization':specialization,'curriculum':ug_curriculum(doc[page-1]),'source':f'{UG} · PDF page {page}'})
    with pymupdf.open(ROOT/PG) as doc:
        for page,award,specialization in PG_PROGRAMMES:
            programmes.append({'id':len(programmes)+1,'name':f'{award} — {specialization}','department':'Business' if award=='MBA' else 'Computing','award':award,'level':'Postgraduate','specialization':specialization,'curriculum':pg_curriculum(doc[page-1],award),'source':f'{PG} · PDF page {page}'})
    rooms=[]
    with (ROOT/'Class Details.csv').open(encoding='utf-8-sig',newline='') as source:
        # The first two supplied headers differ only by case. Positional parsing
        # preserves both the descriptive room name and its scheduling code.
        rows=csv.reader(source);next(rows)
        for display_name,code,building,capacity in rows:
            lab=building.strip().lower()=='skill' or code.upper().startswith('LAB-')
            rooms.append({'id':len(rooms)+1,'name':code.strip(),'display_name':display_name.strip(),'building':building.strip(),'capacity':int(capacity),'kind':'Lab' if lab else 'Classroom','equipment':['AC','Projector']+(['Computers'] if building.strip().lower()=='skill' else []),'pc_count':int(capacity) if building.strip().lower()=='skill' else 0,'source':'Class Details.csv; Skill Block PCs and all-room AC/projector confirmed by user','unavailable':[],'active':True})
    data={'programmes':programmes,'rooms':rooms,'notes':['Programme catalogue entries are published curriculum, not current teaching allocations.','PG brochure does not supply module codes; these remain null.','Impact Block LAB rooms are classified as labs by their supplied codes, but their PC counts are unconfirmed and remain 0.','MBA final-semester routes are alternatives, not simultaneous required modules.','Credit figures are transcribed as printed; programme administrators should confirm apparent brochure discrepancies before using them for credit audits.']}
    output=ROOT/'backend/data/college_catalog.json'
    output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{len(rooms)} rooms, {sum(r["capacity"] for r in rooms)} seats, {len(programmes)} programme paths, {sum(len(p["curriculum"]) for p in programmes)} curriculum entries')
    for p in programmes: print(p['source'],len(p['curriculum']),p['name'])

if __name__=='__main__': main()

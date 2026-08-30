# -*- coding: utf-8 -*-
"""
인천·안산 행사 모으기
실행할 때마다 원본 사이트를 새로 읽어서 행사목록.html 을 다시 만든다.

수집처
  1. 인천문화포털 IQ   https://ifac.or.kr
  2. 안산문화재단 공연  https://www.ansanart.com
  3. 안산문화재단 기획전시
  4. 안산문화재단 교육/행사(신청형)
"""
import re, os, sys, json, html, time, webbrowser, urllib.request
from datetime import date, datetime, timezone, timedelta
from collections import Counter

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9"}
KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
TODAY = NOW.date()
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "index.html")


def log(*a):
    print(*a, flush=True)


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read().decode('utf-8', 'ignore')
        except Exception as e:
            if i == tries - 1:
                log("  ! 실패:", url, e)
                return ""
            time.sleep(1.5)


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'(?s)<[^>]+>', ' ', s))).strip()


def lines_of(h):
    h = re.sub(r'(?s)<(script|style|head)\b.*?</\1>', ' ', h)
    h = re.sub(r'(?i)<(br|/p|/div|/li|/h[1-6]|/dd|/dt|/td|/tr|/a|/span)\s*/?>', '\n', h)
    h = re.sub(r'(?s)<[^>]+>', '\n', h)
    h = html.unescape(h)
    return [re.sub(r'\s+', ' ', l).strip() for l in h.split('\n') if l.strip()]


def parse_price(raw):
    """(정가, 최저가, 원문) — 정가는 맨 처음 나온 금액, 최저가는 할인 포함 최솟값"""
    s = (raw or "").strip()
    if not s:
        return (None, None, "정보없음")
    flat = s.replace(',', '').replace(' ', '')
    paid = '유료' in flat
    nums = []
    for m in re.finditer(r'(\d+(?:\.\d+)?)(만원|천원|원)', flat):
        v = float(m.group(1))
        u = m.group(2)
        if u == '만원':
            v *= 10000
        elif u == '천원':
            v *= 1000
        nums.append(int(v))
    pos = [n for n in nums if n > 0]
    if pos:
        return (pos[0], min(pos), s)
    if nums and not paid:
        return (0, 0, "무료" if s == '0원' else s)
    if re.search(r'무료|free|초대', flat, re.I) and not paid:
        return (0, 0, "무료")
    return (None, None, s)


def bucket(w):
    if w is None:
        return "확인필요"
    if w == 0:
        return "무료"
    if w <= 10000:
        return "1만원 이하"
    if w <= 30000:
        return "1~3만원"
    return "3만원 초과"


def d(s):
    m = re.search(r'(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})', s or "")
    if not m:
        return None
    try:
        return date(*map(int, m.groups()))
    except Exception:
        return None


SKIP = re.compile(r'<label|공모|채용|합격자|심사결과|대관\s*(공고|신청|안내|중단|불가)'
                  r'|입찰|용역|기간제|근로자|위원\s*모집|평가\s*결과|정기대관|사칭')
items = []


def add(**k):
    if not k.get('title') or SKIP.search(k['title']):
        return False
    if k.get('end') and k['end'] < str(TODAY):
        return False
    items.append(k)
    return True


def field(body, lbl, limit=25):
    for i, l in enumerate(body[:limit]):
        if l == lbl and i + 1 < len(body):
            return body[i + 1]
    return ''


def tit_chunks(h):
    out = []
    for c in h.split('<p class="tit">')[1:]:
        head = c.split('</p>')[0]
        cm = re.search(r'(?s)<span class="cat[^"]*">(.*?)</span>', head)
        cat = clean(cm.group(1)) if cm else ''
        t = re.sub(r'(?s)<span class="cat[^"]*">.*?</span>', '', head)
        t = re.sub(r'</?a[^>]*>', '', t)
        out.append((re.sub(r'\s+', ' ', html.unescape(t)).strip(), cat, head,
                    lines_of(c.split('</p>', 1)[1] if '</p>' in c else c)))
    return out


# ============ 1. 인천문화포털 IQ ============
def collect_incheon():
    B = "https://ifac.or.kr"
    LIST = B + "/culturalInfo/cuturalEvents/performanceSrch/list.do?key=m2501152621396&pageIndex=%d"
    VIEW = B + "/culturalInfo/cuturalEvents/performanceSrch/view.do?key=m2501152621396&eventSn="
    sns, dead = [], 0
    # 목록은 '끝나는 날 빠른 순'이라 지난 행사 페이지가 나오면 멈춘다
    for p in range(1, 12):
        h = get(LIST % p)
        f = re.findall(r"goView\('(\d+)'\)", h)
        if not f:
            break
        ends = re.findall(r'~\s*(\d{4}\.\d{2}\.\d{2})', h)
        future = [e for e in ends if d(e) and d(e) >= TODAY]
        for s in f:
            if s not in sns:
                sns.append(s)
        log("  인천 목록 %d쪽 (%d건, 예정 %d건)" % (p, len(f), len(future)))
        if ends and not future:
            dead += 1
            if dead >= 1:
                break
    n = 0
    for i, sn in enumerate(sns, 1):
        u = VIEW + sn
        h = get(u)
        m = re.search(r'(?s)<div class="info">(.*?)</ul>', h or "")
        if not m:
            continue
        blk = m.group(1)
        tm = re.search(r'(?s)<h6>(.*?)</h6>', blk)
        title = clean(tm.group(1)) if tm else ""
        F = {clean(a): clean(b) for a, b in re.findall(r'(?s)<b>(.*?)</b>\s*<span>(.*?)</span>', blk)}
        ds = re.findall(r'\d{4}[.\-]\d{1,2}[.\-]\d{1,2}', F.get('기간', ''))
        sd = d(ds[0]) if ds else None
        ed = d(ds[-1]) if len(ds) > 1 else sd
        w, wm, pl = parse_price(F.get('공연가격', ''))
        if add(city="인천", title=title, kind=F.get('구분', '') or '행사', cat=F.get('분류', ''),
               place=F.get('장소', ''), start=str(sd) if sd else "", end=str(ed) if ed else "",
               time=F.get('시간', ''), age=F.get('관람연령', ''), host=F.get('주최', ''),
               tel=F.get('문의', ''), price_won=w, price_min=wm, price_raw=pl,
               bucket=bucket(w), url=u, source="인천문화포털 IQ", status=""):
            n += 1
        if i % 20 == 0:
            log("  인천 상세 %d/%d" % (i, len(sns)))
    log("  → 인천 %d건" % n)


# ============ 2~4. 안산문화재단 ============
def collect_ansan():
    AN = "https://www.ansanart.com"
    n = 0

    SHOW = AN + "/lay2/program/S1T10C334/show/intro.do"
    for title, cat, head, body in tit_chunks(get(SHOW)):
        hm = re.search(r'href="(view\.do\?sh_no=\d+)', head)
        href = AN + "/lay2/program/S1T10C334/show/" + hm.group(1) if hm else SHOW
        dts = [l for l in body[:20] if re.match(r'^\d{4}-\d{2}-\d{2}', l)]
        sd = d(dts[0]) if dts else None
        ed = d(dts[-1]) if len(dts) > 1 else sd
        pa = field(body, '장소 및 연령')
        w, wm, pl = parse_price(field(body, '가격정보'))
        if add(city="안산", title=title, kind="공연", cat=cat or "공연",
               place=pa.split('/')[0].strip(), start=str(sd) if sd else "",
               end=str(ed) if ed else "", time='',
               age=pa.split('/')[1].strip()[:60] if '/' in pa else '',
               host="안산문화재단", tel=field(body, '문의정보'), price_won=w, price_min=wm,
               price_raw=pl, bucket=bucket(w), url=href, source="안산문화재단", status=""):
            n += 1

    EXH = AN + "/lay1/program/S1T200C28/exhibit/intro.do"
    for title, cat, head, body in tit_chunks(get(EXH)):
        dts = [l for l in body[:15] if re.match(r'^\d{4}-\d{2}-\d{2}', l)]
        rng = dts[0] if dts else field(body, '날짜')
        ds = re.findall(r'\d{4}-\d{2}-\d{2}', rng)
        sd = d(ds[0]) if ds else None
        ed = d(ds[-1]) if len(ds) > 1 else sd
        if add(city="안산", title=title, kind="전시", cat=cat or "전시", place=field(body, '장소'),
               start=str(sd) if sd else "", end=str(ed) if ed else "", time='', age='',
               host="안산문화재단", tel=field(body, '문의정보'), price_won=None, price_min=None,
               price_raw="관람료 확인 필요", bucket="확인필요", url=EXH,
               source="안산문화재단", status=""):
            n += 1

    EDU = AN + "/lay2/program/S1T32C336/np_edu/intro.do"
    L = lines_of(get(EDU))
    for i, l in enumerate(L):
        if l != '수강료':
            continue
        fee = L[i + 1] if i + 1 < len(L) else ''
        status = ''
        for s in L[i + 2:i + 8]:
            if s in ('모집중', '신청마감', '접수예정', '대기접수'):
                status = s
                break
        back = L[max(0, i - 24):i]
        ds = re.findall(r'\d{4}-\d{2}-\d{2}', field(back, '기간', 99))
        sd = d(ds[0]) if ds else None
        ed = d(ds[-1]) if len(ds) > 1 else sd
        title = ''
        for j, s in enumerate(back):
            if s == '기간':
                title = back[j - 1] if j > 0 else ''
                break
        title = re.sub(r'^\[\s*개\s*인\s*\]|^\[\s*단\s*체\s*\]', '', title).strip()
        w, wm, pl = parse_price(fee)
        if add(city="안산", title=title, kind="교육/체험", cat="교육·행사",
               place=field(back, '장소', 99), start=str(sd) if sd else "",
               end=str(ed) if ed else "", time=field(back, '시간', 99),
               age=field(back, '연령', 99), host="안산문화재단", tel='', price_won=w,
               price_min=wm, price_raw=pl, bucket=bucket(w), url=EDU,
               source="안산문화재단 교육/행사", status=status):
            n += 1
    log("  → 안산 %d건" % n)


# ============ HTML ============
def render(data):
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\u003c').replace('>', '\u003e')
    return TEMPLATE.replace('/*__DATA__*/null', payload)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>인천·안산 행사판</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@500;700&family=IBM+Plex+Sans+KR:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root{
  --paper:#F2F5F4; --card:#FFFFFF; --card2:#FAFBFB;
  --ink:#12201E; --ink2:#3A4A47; --muted:#667874; --line:#D7E0DD;
  --incheon:#0E7A86; --incheon-bg:#E2F1F2;
  --ansan:#AB4E1B; --ansan-bg:#F7E9DF;
  --free:#146F4A; --free-bg:#DFF0E6;
  --warn:#8A6410; --warn-bg:#F6EBD3;
  --hot:#9C2F2F; --hot-bg:#F6E2E1;
  --grey-bg:#E8EDEC;
  --focus:#0E7A86;
  --shadow:0 1px 2px rgba(18,32,30,.05),0 6px 18px rgba(18,32,30,.05);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#0D1513; --card:#151F1D; --card2:#1A2523;
    --ink:#E6EEEB; --ink2:#B6C5C1; --muted:#879995; --line:#26332F;
    --incheon:#4FC3CD; --incheon-bg:#10312F;
    --ansan:#E89A63; --ansan-bg:#332115;
    --free:#5FCB93; --free-bg:#0F2C20;
    --warn:#E0B75F; --warn-bg:#2E2513;
    --hot:#EE8C87; --hot-bg:#331B1A;
    --grey-bg:#1F2A28;
    --focus:#4FC3CD;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 6px 18px rgba(0,0,0,.25);
  }
}
:root[data-theme="dark"]{
  --paper:#0D1513; --card:#151F1D; --card2:#1A2523;
  --ink:#E6EEEB; --ink2:#B6C5C1; --muted:#879995; --line:#26332F;
  --incheon:#4FC3CD; --incheon-bg:#10312F;
  --ansan:#E89A63; --ansan-bg:#332115;
  --free:#5FCB93; --free-bg:#0F2C20;
  --warn:#E0B75F; --warn-bg:#2E2513;
  --hot:#EE8C87; --hot-bg:#331B1A;
  --grey-bg:#1F2A28;
  --focus:#4FC3CD;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 6px 18px rgba(0,0,0,.25);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"IBM Plex Sans KR","Malgun Gothic",system-ui,sans-serif;
  font-size:15px; line-height:1.6;
}
.wrap{max-width:940px;margin:0 auto;padding:0 18px 72px}

/* ---- header ---- */
header{padding:38px 0 22px}
.eyebrow{
  font-family:"IBM Plex Mono",monospace; font-size:11.5px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--muted); margin:0 0 10px
}
h1{
  font-family:"Hahmlet","Nanum Myeongjo",serif; font-weight:700;
  font-size:clamp(30px,6vw,44px); line-height:1.15; margin:0 0 10px;
  letter-spacing:-.01em; text-wrap:balance;
}
.lede{margin:0;color:var(--ink2);max-width:60ch}
.lede b{color:var(--ink);font-weight:600}

/* ---- stat strip ---- */
.stats{
  display:flex;flex-wrap:wrap;gap:0;margin:22px 0 0;
  border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--card)
}
.stat{flex:1 1 116px;padding:12px 14px;border-right:1px solid var(--line)}
.stat:last-child{border-right:0}
.stat .n{font-family:"IBM Plex Mono",monospace;font-weight:600;font-size:21px;
  font-variant-numeric:tabular-nums;display:block;line-height:1.2}
.stat .k{font-size:11.5px;color:var(--muted);letter-spacing:.02em}
.stat.free .n{color:var(--free)}
.stat.ic .n{color:var(--incheon)}
.stat.an .n{color:var(--ansan)}

/* ---- toolbar ---- */
.bar{
  position:sticky;top:0;z-index:20;background:var(--paper);
  padding:14px 0 12px;margin-top:24px;border-bottom:1px solid var(--line)
}
.searchrow{display:flex;gap:8px;align-items:center}
input[type=search]{
  flex:1;min-width:0;font:inherit;color:var(--ink);background:var(--card);
  border:1px solid var(--line);border-radius:9px;padding:9px 12px
}
input[type=search]::placeholder{color:var(--muted)}
select{
  font:inherit;font-size:13.5px;color:var(--ink);background:var(--card);
  border:1px solid var(--line);border-radius:9px;padding:9px 10px
}
:is(input,select,button,a):focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px;align-items:center}
.chips .lbl{
  font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted);margin-right:2px
}
.chip{
  font:inherit;font-size:13px;cursor:pointer;border:1px solid var(--line);
  background:var(--card);color:var(--ink2);border-radius:99px;padding:5px 11px;
  transition:background .12s,border-color .12s,color .12s
}
.chip:hover{border-color:var(--ink2)}
.chip[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.chip.free[aria-pressed="true"]{background:var(--free);border-color:var(--free);color:#fff}
.chip.ic[aria-pressed="true"]{background:var(--incheon);border-color:var(--incheon);color:#fff}
.chip.an[aria-pressed="true"]{background:var(--ansan);border-color:var(--ansan);color:#fff}
.count{margin-left:auto;font-family:"IBM Plex Mono",monospace;font-size:12px;
  color:var(--muted);font-variant-numeric:tabular-nums}

/* ---- list ---- */
ul.list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:9px}
.grouphead{
  font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.13em;
  text-transform:uppercase;color:var(--muted);margin:22px 0 2px;
  display:flex;align-items:center;gap:10px
}
.grouphead::after{content:"";flex:1;height:1px;background:var(--line)}
.row{
  display:grid;grid-template-columns:78px 1fr auto;gap:14px;align-items:start;
  background:var(--card);border:1px solid var(--line);border-radius:11px;
  padding:14px 15px;box-shadow:var(--shadow);
  border-left:3px solid var(--line);
}
.row.ic{border-left-color:var(--incheon)}
.row.an{border-left-color:var(--ansan)}
.when{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;line-height:1.35}
.when .md{font-size:15px;font-weight:600;display:block}
.when .yr{font-size:11px;color:var(--muted);display:block}
.when .dday{
  display:inline-block;margin-top:5px;font-size:10.5px;font-weight:600;
  padding:1px 6px;border-radius:5px;background:var(--grey-bg);color:var(--muted)
}
.when .dday.soon{background:var(--hot-bg);color:var(--hot)}
.when .dday.now{background:var(--free-bg);color:var(--free)}
.main .t{margin:0 0 4px;font-size:15.5px;font-weight:600;line-height:1.4}
.main .t a{color:inherit;text-decoration:none;background-image:linear-gradient(var(--line),var(--line));
  background-size:100% 1px;background-position:0 100%;background-repeat:no-repeat}
.main .t a:hover{color:var(--incheon);background-image:linear-gradient(currentColor,currentColor)}
.meta{font-size:12.5px;color:var(--muted);display:flex;flex-wrap:wrap;gap:4px 9px}
.meta .city{font-weight:600}
.meta .city.ic{color:var(--incheon)}
.meta .city.an{color:var(--ansan)}
.price{text-align:right;min-width:92px}
.tag{
  display:inline-block;font-family:"IBM Plex Mono",monospace;font-weight:600;
  font-size:13px;font-variant-numeric:tabular-nums;padding:4px 9px;border-radius:7px;
  background:var(--grey-bg);color:var(--ink2);white-space:nowrap
}
.tag.b0{background:var(--free-bg);color:var(--free)}
.tag.b1{background:var(--incheon-bg);color:var(--incheon)}
.tag.b2{background:var(--warn-bg);color:var(--warn)}
.tag.b3{background:var(--hot-bg);color:var(--hot)}
.sub{font-size:11px;color:var(--muted);margin-top:4px;line-height:1.4}
.status{display:inline-block;font-size:10.5px;padding:1px 6px;border-radius:5px;
  margin-top:5px;background:var(--grey-bg);color:var(--muted)}
.status.open{background:var(--free-bg);color:var(--free)}
.empty{padding:44px 4px;color:var(--muted);text-align:center}

/* ---- footer ---- */
footer{margin-top:44px;padding-top:20px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--muted)}
footer a{color:var(--incheon)}
footer h2{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.13em;
  text-transform:uppercase;color:var(--muted);margin:0 0 8px;font-weight:500}
footer ul{margin:0 0 16px;padding-left:17px}
footer li{margin-bottom:3px}

@media (max-width:600px){
  .row{grid-template-columns:62px 1fr;gap:11px}
  .price{grid-column:2;text-align:left;margin-top:2px}
  .stat{flex:1 1 33%}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <p class="eyebrow" id="stamp"></p>
  <h1>인천·안산 행사판</h1>
  <p class="lede">지금 신청하거나 보러 갈 수 있는 행사만 모았어. <b>참가비 기준</b>으로 갈라놨고, 이미 끝난 건 빠져 있어.</p>
  <div class="stats" id="stats"></div>
</header>

<div class="bar">
  <div class="searchrow">
    <input type="search" id="q" placeholder="행사 이름 · 장소로 찾기" aria-label="검색">
    <select id="sort" aria-label="정렬">
      <option value="end">마감 임박순</option>
      <option value="start">시작 빠른순</option>
      <option value="cheap">싼 순</option>
      <option value="price">비싼 순</option>
    </select>
  </div>
  <div class="chips" id="cityChips"><span class="lbl">지역</span></div>
  <div class="chips" id="priceChips"><span class="lbl">참가비</span></div>
  <div class="chips" id="kindChips"><span class="lbl">종류</span><span class="count" id="count"></span></div>
</div>

<ul class="list" id="list"></ul>

<footer>
  <h2>어디서 긁어왔나</h2>
  <ul>
    <li><a href="https://ifac.or.kr/culturalInfo/cuturalEvents/performanceSrch/list.do?key=m2501152621396" target="_blank" rel="noopener">인천문화포털 IQ — 문화행사</a></li>
    <li><a href="https://www.ansanart.com/lay2/program/S1T10C334/show/intro.do" target="_blank" rel="noopener">안산문화재단 — 공연안내</a></li>
    <li><a href="https://www.ansanart.com/lay1/program/S1T200C28/exhibit/intro.do" target="_blank" rel="noopener">안산문화재단 — 기획전시</a></li>
    <li><a href="https://www.ansanart.com/lay2/program/S1T32C336/np_edu/intro.do" target="_blank" rel="noopener">안산문화재단 — 교육/행사</a></li>
  </ul>
  <h2>읽는 법</h2>
  <ul>
    <li>가격은 <b>정가</b> 기준으로 분류했어. 할인가가 따로 있으면 밑에 작게 적어놨어.</li>
    <li>“확인필요”는 원본에 값이 안 적힌 것들이야. 대부분 무료 전시지만 제목을 눌러서 확인해.</li>
    <li>이 페이지는 <b>6시간마다 자동으로</b> 다시 긁어. 맨 위 시각이 마지막으로 확인한 때야.</li>
    <li>PC에서 지금 당장 새로 긁고 싶으면 <b>행사찾기.bat</b> 을 실행하면 돼.</li>
  </ul>
</footer>
</div>

<script id="data" type="application/json">/*__DATA__*/null</script>
<script>
(function(){
  var D = JSON.parse(document.getElementById('data').textContent);
  var ITEMS = D.items, TODAY = D.today;
  document.getElementById('stamp').textContent = D.generated + ' 기준 · ' + ITEMS.length + '건';

  var BUCKETS = ['무료','1만원 이하','1~3만원','3만원 초과','확인필요'];
  var BCLASS = {'무료':'b0','1만원 이하':'b1','1~3만원':'b2','3만원 초과':'b3','확인필요':''};
  var KINDS = [];
  ITEMS.forEach(function(i){ var k = norm(i.kind); if(KINDS.indexOf(k)<0) KINDS.push(k); });
  function norm(k){
    if(!k) return '기타';
    if(/공연|음악|연극|콘서트/.test(k)) return '공연';
    if(/전시/.test(k)) return '전시';
    if(/교육|체험|강좌/.test(k)) return '교육·체험';
    if(/축제|행사/.test(k)) return '축제·행사';
    if(/영화/.test(k)) return '영화';
    return '기타';
  }
  KINDS.sort();

  var S = {city:'전체', price:'전체', kind:'전체', q:'', sort:'end'};
  try{ var saved = JSON.parse(localStorage.getItem('haengsa')||'{}');
       Object.keys(saved).forEach(function(k){ if(k in S) S[k]=saved[k]; }); }catch(e){}
  function save(){ try{ localStorage.setItem('haengsa', JSON.stringify(S)); }catch(e){} }

  function mkChips(box, key, vals, cls){
    vals.forEach(function(v){
      var b = document.createElement('button');
      b.type='button'; b.className='chip'+(cls&&cls[v]?' '+cls[v]:'');
      b.textContent = v; b.setAttribute('aria-pressed', S[key]===v);
      b.onclick = function(){ S[key]=v; save(); paint(); };
      box.appendChild(b);
    });
  }
  var cityBox=document.getElementById('cityChips'), priceBox=document.getElementById('priceChips'), kindBox=document.getElementById('kindChips');
  mkChips(cityBox,'city',['전체','인천','안산'],{'인천':'ic','안산':'an'});
  mkChips(priceBox,'price',['전체'].concat(BUCKETS),{'무료':'free'});
  var kindTail = document.getElementById('count');
  mkChips(kindBox,'kind',['전체'].concat(KINDS));
  kindBox.appendChild(kindTail);

  var q=document.getElementById('q'); q.value=S.q;
  q.oninput=function(){ S.q=q.value; save(); paint(); };
  var sortSel=document.getElementById('sort'); sortSel.value=S.sort;
  sortSel.onchange=function(){ S.sort=sortSel.value; save(); paint(); };

  function won(n){ return n.toLocaleString('ko-KR')+'원'; }
  function dday(endStr){
    if(!endStr) return null;
    var a=new Date(TODAY+'T00:00'), b=new Date(endStr+'T00:00');
    return Math.round((b-a)/86400000);
  }
  function fmt(s){
    if(!s) return {md:'날짜미정', yr:''};
    var p=s.split('-');
    return {md:p[1]+'/'+p[2], yr:p[0]};
  }

  function stats(){
    var box=document.getElementById('stats');
    var free=ITEMS.filter(function(i){return i.bucket==='무료';}).length;
    var ic=ITEMS.filter(function(i){return i.city==='인천';}).length;
    var an=ITEMS.filter(function(i){return i.city==='안산';}).length;
    var wk=ITEMS.filter(function(i){var d=dday(i.end); return d!==null && d>=0 && d<=7;}).length;
    var rows=[['전체',ITEMS.length,''],['무료',free,'free'],['인천',ic,'ic'],['안산',an,'an'],['7일 내 마감',wk,'']];
    box.innerHTML = rows.map(function(r){
      return '<div class="stat '+r[2]+'"><span class="n">'+r[1]+'</span><span class="k">'+r[0]+'</span></div>';
    }).join('');
  }

  function paint(){
    [[cityBox,'city'],[priceBox,'price'],[kindBox,'kind']].forEach(function(p){
      p[0].querySelectorAll('.chip').forEach(function(b){
        b.setAttribute('aria-pressed', b.textContent===S[p[1]]);
      });
    });
    var qq=S.q.trim().toLowerCase();
    var out=ITEMS.filter(function(i){
      if(S.city!=='전체' && i.city!==S.city) return false;
      if(S.price!=='전체' && i.bucket!==S.price) return false;
      if(S.kind!=='전체' && norm(i.kind)!==S.kind) return false;
      if(qq && (i.title+' '+i.place+' '+i.host).toLowerCase().indexOf(qq)<0) return false;
      return true;
    });
    var big=99999999;
    out.sort(function(a,b){
      if(S.sort==='end') return (a.end||'9999').localeCompare(b.end||'9999');
      if(S.sort==='start') return (a.start||'9999').localeCompare(b.start||'9999');
      var pa=a.price_won==null?big:a.price_won, pb=b.price_won==null?big:b.price_won;
      return S.sort==='cheap' ? pa-pb : (pb===big?-1:pa===big?1:pb-pa);
    });
    document.getElementById('count').textContent = out.length+' / '+ITEMS.length+'건';

    var L=document.getElementById('list');
    if(!out.length){ L.innerHTML='<li class="empty">조건에 맞는 행사가 없어. 필터를 풀어봐.</li>'; return; }
    L.innerHTML = out.map(function(i){
      var cc=i.city==='인천'?'ic':'an';
      var running = i.start && i.start<=TODAY && (!i.end || i.end>=TODAY);
      var key = running ? (i.end||i.start) : (i.start||i.end);
      var f=fmt(key), ddTxt='', ddCls='';
      if(running){
        var de=dday(i.end);
        if(de===0){ddTxt='오늘 마감';ddCls='soon';}
        else if(de!==null && de<=7){ddTxt='D-'+de+' 마감';ddCls='soon';}
        else {ddTxt='진행중';ddCls='now';}
      }else{
        var dsx=dday(i.start);
        if(dsx!==null && dsx>=0) ddTxt = dsx===0 ? '오늘 시작' : 'D-'+dsx;
      }
      var tag = i.bucket==='무료' ? '무료'
              : i.bucket==='확인필요' ? '확인필요'
              : won(i.price_won);
      var sub='';
      if(i.price_min!=null && i.price_won!=null && i.price_min<i.price_won) sub='할인 시 '+won(i.price_min)+'부터';
      else if(i.bucket==='확인필요' && i.price_raw && i.price_raw!=='정보없음') sub=i.price_raw.slice(0,26);
      var st = i.status ? '<span class="status'+(i.status==='모집중'?' open':'')+'">'+i.status+'</span>' : '';
      var range = i.start && i.end && i.start!==i.end ? (i.start.slice(5).replace('-','.')+'~'+i.end.slice(5).replace('-','.')) : '';
      return '<li class="row '+cc+'">'
        +'<div class="when"><span class="md">'+f.md+'</span><span class="yr">'+f.yr+'</span>'
        + (ddTxt?'<span class="dday '+ddCls+'">'+ddTxt+'</span>':'') +'</div>'
        +'<div class="main"><p class="t"><a href="'+i.url+'" target="_blank" rel="noopener">'+esc(i.title)+'</a></p>'
        +'<div class="meta"><span class="city '+cc+'">'+i.city+'</span>'
        + (i.place?'<span>'+esc(i.place)+'</span>':'')
        + (range?'<span>'+range+'</span>':'')
        + '<span>'+norm(i.kind)+'</span></div>'+st+'</div>'
        +'<div class="price"><span class="tag '+BCLASS[i.bucket]+'">'+tag+'</span>'
        + (sub?'<div class="sub">'+esc(sub)+'</div>':'') +'</div>'
      +'</li>';
    }).join('');
  }
  function esc(s){ return String(s).replace(/[&<>"]/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

  stats(); paint();
})();
</script>
</body>
</html>
"""


def main():
    log("인천·안산 행사 모으는 중...\n")
    log("[1/2] 인천문화포털")
    collect_incheon()
    log("[2/2] 안산문화재단")
    collect_ansan()

    seen, out = set(), []
    for it in items:
        k = (it['city'], it['title'], it['start'])
        if k in seen or not it['title']:
            continue
        seen.add(k)
        out.append(it)
    out.sort(key=lambda x: (x['end'] or '9999', x['start'] or ''))

    data = {"generated": NOW.strftime('%Y-%m-%d %H:%M'),
            "today": str(TODAY), "items": out}
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(render(data))

    c = Counter(i['bucket'] for i in out)
    log("\n총 %d건  (무료 %d · 1만원이하 %d · 1~3만원 %d · 3만원초과 %d · 확인필요 %d)"
        % (len(out), c['무료'], c['1만원 이하'], c['1~3만원'], c['3만원 초과'], c['확인필요']))
    log("저장: " + OUT)
    if '--no-open' not in sys.argv:
        webbrowser.open('file:///' + OUT.replace('\\', '/'))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("\n오류가 났어. 위 내용을 복사해서 알려줘. (엔터를 누르면 닫힘)")

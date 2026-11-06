"""output/ 아래 글을 모아 동작하는 블로그 사이트를 만든다. 글 읽기는 이 파일, 화면은 theme.py가 맡는다.

디자인은 솔트웨어 홈페이지(saltware.co.kr)를 따른다.
베이지 톤온톤이 바탕이고, 검정은 버튼 같은 작은 포인트에만 쓴다. 영문 대문자 라벨, 넓은 여백, 인사이트 메가 메뉴.

만드는 파일
- index.html                     인사이트 첫 화면 (대표 글, 시리즈 필터, 검색, 태그, 더 보기, 뉴스레터)
- output/<슬러그>/preview.html    글 페이지 (목차, 읽기 진행 막대, 링크 복사, 이전/다음 글, 관련 글)
- contact.html                   문의하기

사용법: py -3 scripts/build_site.py
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CATS = [
    ("spoon", "데이터 한 스푼", "DATA SPOON", "데이터 용어 하나를 일상의 비유로 쉽게 풉니다."),
    ("note", "데이터 노트", "DATA NOTE", "기업이 AI와 데이터를 쓰다 부딪히는 문제를 한 편씩 짚습니다."),
    ("case", "고객 사례", "CUSTOMER STORY", "고객사와 함께 한 도입 과정과 달라진 점을 정리합니다."),
    ("guide", "솔루션 가이드", "SOLUTION GUIDE", "솔트웨어의 다섯 사업 영역을 문제, 동작 방식, 도입 단계, 자주 묻는 질문까지 자세히 풉니다."),
]
CAT_BY_NAME = {name: key for key, name, _, _ in CATS}
EYEBROW = {key: eb for key, _, eb, _ in CATS}


# ---------- 글 읽기 ----------

def split_front_matter(text):
    meta = {}
    if text.startswith("---"):
        _, head, body = text.split("---", 2)
        for line in head.strip().splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
        return meta, body.strip()
    return meta, text.strip()


def slugify_heading(text, used):
    base = re.sub(r"[^\w가-힣]+", "-", text).strip("-").lower() or "section"
    slug, n = base, 2
    while slug in used:
        slug, n = f"{base}-{n}", n + 1
    used.add(slug)
    return slug


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[확인 필요:([^\]]*)\]", r'<span class="todo">[확인 필요:\1]</span>', text)
    text = re.sub(r"(https?://[^\s<]+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', text)
    return text


def body_to_html(body):
    """본문 마크다운을 HTML로 바꾸고 (html, 목차, 해시태그)를 돌려준다."""
    out, toc, tags, used = [], [], [], set()
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        lines = block.splitlines()
        img = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", block)
        if img:
            out.append(f'<figure><img src="{img.group(2)}" alt="{html.escape(img.group(1))}" loading="lazy"></figure>')
        elif block.startswith("## "):
            title = block[3:].strip()
            sid = slugify_heading(title, used)
            toc.append((sid, title))
            out.append(f'<h2 id="{sid}">{inline(title)}</h2>')
        elif block.startswith("#") and not block.startswith("# "):
            tags = [t.lstrip("#") for t in block.split()]
        elif all(l.startswith("- ") for l in lines):
            out.append("<ul>" + "".join(f"<li>{inline(l[2:])}</li>" for l in lines) + "</ul>")
        elif len(lines) > 1 and all(l.startswith("- ") for l in lines[1:]):
            out.append(f'<div class="refs"><p>{inline(lines[0])}</p><ul>'
                       + "".join(f"<li>{inline(l[2:])}</li>" for l in lines[1:]) + "</ul></div>")
        elif block.startswith("**") and lines[0].count("**") >= 2 and len(lines) == 1 and block.index("**", 2) < 80:
            out.append(f'<p class="lead">{inline(block)}</p>')
        else:
            out.append("<p>" + "<br>".join(inline(l) for l in lines) + "</p>")
    return "\n".join(out), toc, tags


def load_posts():
    posts = []
    for draft in (ROOT / "output").glob("*/draft.md"):
        text = draft.read_text(encoding="utf-8")
        if "[IMAGE:" in text:
            print("건너뜀 (이미지 작업 전):", draft.parent.name)
            continue
        meta, body = split_front_matter(text)
        body_html, toc, tags = body_to_html(body)
        plain = re.sub(r"<[^>]+>", "", body_html)
        series = meta.get("series", "")
        title = meta.get("title", "")
        posts.append({
            "slug": draft.parent.name,
            "title": title,
            "short": re.sub(r"^\[[^\]]+\]\s*", "", title),
            "series": series,
            "cat": CAT_BY_NAME.get(series, "spoon"),
            "author": meta.get("author", ""),
            "date": meta.get("date", ""),
            "summary": meta.get("summary", ""),
            "tags": tags,
            "minutes": max(1, round(len(plain) / 500)),
            "body_html": body_html,
            "toc": toc,
            "points": [x.strip() for x in meta.get("points", "").split("|") if x.strip()],
            "highlight": meta.get("highlight", ""),
            "cover": meta.get("cover", "") or re.sub(r"^\[[^\]]+\]\s*", "", title).split()[0],
        })
    return sorted(posts, key=lambda p: (p["date"], p["slug"]), reverse=True)


def load_upcoming():
    path = ROOT / "guide" / "upcoming.md"
    items = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"- \[(.+?)\]\s*(.+)", line.strip())
            if m:
                items.append({"series": m.group(1), "title": m.group(2)})
    return items


def esc(s):
    return html.escape(s or "")


# ---------- 공통 조각 ----------

FONT = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">'

# 솔트웨어 홈페이지 tokens.css의 색과 간격
BASE_CSS = """
:root{--bg:#F4F2EA;--band:#F8F6F1;--card:#FFFFFF;--line:#E3DFD3;--line2:#DEDACD;--ink:#141413;--ink2:#45423C;
--muted:#6B675F;--faint:#87837A;--dot:#F49F20;--dot-deep:#E8811A;--accent:#895118;--accent-bg:#FFF3E2;
--dark:#141413;--dark2:#292723;--deep:#E9E5DA;--deep2:#DEDACD;--on-dark:#F2EFE8;--on-dark-muted:#BAB5AA;--wrap:1200px;--ease:cubic-bezier(.2,.7,.2,1)}
*{box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:'Pretendard Variable',Pretendard,-apple-system,'Malgun Gothic',sans-serif;
letter-spacing:-0.01em;-webkit-font-smoothing:antialiased;word-break:keep-all}
a{color:inherit;text-decoration:none}
img{display:block;max-width:100%}
button,input,select,textarea{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--dot-deep);outline-offset:3px;border-radius:6px}
.wrap{max-width:var(--wrap);margin:0 auto;padding:0 40px}
.eyebrow{font-size:12.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.dot{color:var(--dot)}
.arrow:after{content:"→";margin-left:6px;transition:transform .2s var(--ease);display:inline-block}
a:hover .arrow:after,.arrow:hover:after{transform:translateX(4px)}

/* 머리글 */
header.top{position:sticky;top:0;z-index:40;background:rgba(244,242,234,.9);backdrop-filter:saturate(1.4) blur(12px);border-bottom:1px solid var(--line)}
.nav{max-width:var(--wrap);margin:0 auto;padding:0 40px;height:76px;display:flex;align-items:center;gap:56px}
.logo{display:flex;align-items:center;gap:10px;font-weight:800;font-size:27px;letter-spacing:-0.045em;color:var(--ink)}
.logo i{width:22px;height:22px;flex:none;background:radial-gradient(circle,var(--dot) 4.6px,transparent 5px) 0 0/11px 11px}
.logo small{font-size:13px;font-weight:600;letter-spacing:.12em;color:var(--muted);margin-left:4px;padding-left:12px;border-left:1px solid var(--line2);text-transform:uppercase}
.menu{display:flex;gap:38px;height:100%}
.menu>div,.menu>a{display:flex;align-items:center;height:100%}
.menu .lnk{font-size:16.5px;font-weight:600;color:var(--ink2);position:relative;padding:8px 0;cursor:pointer;background:none;border:0}
.menu .lnk.on{color:var(--accent)}
.menu .lnk.on:after,.menu .lnk:hover:after{content:"";position:absolute;left:0;right:0;bottom:2px;height:2px;background:var(--accent)}
.menu .lnk:hover{color:var(--ink)}
.tools{margin-left:auto;display:flex;gap:10px;align-items:center}
.icon-btn{width:44px;height:44px;border-radius:50%;border:1px solid var(--line2);background:transparent;display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--ink)}
.icon-btn:hover{background:var(--card)}
.pill{display:inline-flex;align-items:center;gap:8px;height:48px;padding:0 24px;border-radius:980px;background:var(--dark);color:var(--on-dark);font-weight:700;font-size:15.5px;border:0;cursor:pointer;white-space:nowrap;transition:background .2s}
.pill:hover{background:#000}
.pill .spark{color:var(--dot)}
.pill.orange{background:var(--dot);color:var(--ink)}
.pill.orange:hover{background:var(--dot-deep)}
.pill.line{background:transparent;color:var(--ink);border:1px solid var(--line2)}
.pill.line:hover{background:var(--card)}
.burger{display:none}

/* 메가 메뉴 */
.mega{position:absolute;left:0;right:0;top:76px;background:var(--band);border-bottom:1px solid var(--line);box-shadow:0 30px 60px -30px rgba(41,37,28,.25);
opacity:0;visibility:hidden;transform:translateY(-6px);transition:opacity .2s,transform .2s var(--ease),visibility .2s}
.has-mega:hover .mega,.has-mega:focus-within .mega,.mega.open{opacity:1;visibility:visible;transform:none}
.mega-in{max-width:var(--wrap);margin:0 auto;padding:56px 40px 64px;display:grid;grid-template-columns:1.1fr 1fr 1fr 1.3fr;gap:48px}
.mega h3{font-size:32px;letter-spacing:-0.035em;margin:14px 0 16px}
.mega .desc{color:var(--muted);font-size:16px;line-height:1.75;margin:0 0 28px}
.mega .all{font-weight:700;color:var(--accent);font-size:16px}
.mega h4{font-size:17px;margin:0 0 22px;letter-spacing:-0.02em}
.mega .item{display:block;padding:0 0 22px 14px}
.mega .item b{display:block;font-size:16.5px;font-weight:500;color:var(--ink);margin-bottom:6px}
.mega .item span{display:block;color:var(--muted);font-size:14.5px;line-height:1.6}
.mega .item:hover b{color:var(--accent)}
.mega .feat img{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:16px;border:1px solid var(--line)}
.mega .feat .eyebrow{margin:20px 0 10px}
.mega .feat b{font-size:17px;line-height:1.5;display:block}
.mega .feat b:after{content:" ↗";color:var(--faint);font-weight:400}

/* 바닥글 */
footer.bottom{background:var(--deep);color:var(--muted);margin-top:120px;border-top:1px solid var(--line)}
.foot{max-width:var(--wrap);margin:0 auto;padding:72px 40px 56px;display:grid;grid-template-columns:1.4fr repeat(3,1fr);gap:40px;font-size:14.5px}
.foot .logo{color:var(--ink)}
.foot p{line-height:1.7;margin:20px 0 0;max-width:340px}
.foot b{display:block;color:var(--ink);font-size:14px;letter-spacing:.1em;text-transform:uppercase;margin-bottom:18px}
.foot a{display:block;margin:10px 0}
.foot a:hover{color:var(--accent)}
.copy{max-width:var(--wrap);margin:0 auto;padding:22px 40px 40px;border-top:1px solid var(--deep2);font-size:13px;color:var(--faint)}
.toast{position:fixed;left:50%;bottom:32px;transform:translateX(-50%) translateY(16px);background:var(--dark);color:var(--on-dark);padding:13px 22px;border-radius:980px;font-size:14.5px;opacity:0;transition:.25s;pointer-events:none;z-index:60}
.toast.show{opacity:1;transform:translateX(-50%)}
.todo{color:#B1362E;font-weight:700}

@media (max-width:1080px){.mega-in{grid-template-columns:1fr 1fr}.mega .feat{display:none}}
@media (max-width:900px){
 .wrap,.nav,.foot,.copy{padding-left:20px;padding-right:20px}
 .nav{height:64px;gap:16px}.logo{font-size:23px}.logo small{display:none}
 .burger{display:flex}.tools .pill{display:none}
 header.top{backdrop-filter:none;-webkit-backdrop-filter:none;background:var(--bg)}
 .menu{position:fixed;top:64px;left:0;right:0;height:calc(100dvh - 64px);z-index:39;background:var(--bg);flex-direction:column;gap:0;padding:12px 20px 40px;overflow-y:auto;display:none;border-top:1px solid var(--line)}
 .menu.open{display:flex}
 .menu>div,.menu>a{height:auto}
 .menu .lnk{font-size:22px;font-weight:700;padding:18px 0;width:100%;text-align:left;border-bottom:1px solid var(--line)}
 .menu .lnk:after{display:none}
 .mega{display:none}
 .menu .m-cta{margin-top:28px;flex:none;align-self:flex-start;height:52px;padding:0 26px}
 .menu .lnk{flex:none}
 .foot{grid-template-columns:1fr 1fr}
}
@media (min-width:901px){.menu .m-cta{display:none}}
"""

BASE_JS = """
function toast(m){var t=document.querySelector('.toast');t.textContent=m;t.classList.add('show');clearTimeout(t._h);t._h=setTimeout(function(){t.classList.remove('show')},2200)}
(function(){var b=document.querySelector('.burger'),m=document.querySelector('.menu'),MENU_ICON=b.innerHTML;
b.addEventListener('click',function(){var o=m.classList.toggle('open');b.setAttribute('aria-expanded',o);b.setAttribute('aria-label',o?'메뉴 닫기':'메뉴 열기');b.innerHTML=o?'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 6l12 12M18 6 6 18"/></svg>':MENU_ICON;document.body.style.overflow=o?'hidden':''});
addEventListener('resize',function(){if(innerWidth>900&&m.classList.contains('open')){b.click()}});
document.addEventListener('keydown',function(e){if(e.key==='Escape'){document.activeElement&&document.activeElement.blur()}})})();
"""

ICON_SEARCH = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>'
ICON_MENU = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'


def header(base, active, latest):
    items = "".join(
        f'<a class="item" href="{base}index.html?cat={k}"><b>{n}</b><span>{d}</span></a>' for k, n, _, d in CATS[:2])
    feat = ""
    if latest:
        feat = (f'<a class="feat" href="{base}output/{latest["slug"]}/preview.html">'
                f'<img src="{base}output/{latest["slug"]}/images/thumbnail.png" alt="">'
                f'<div class="eyebrow">LATEST · {EYEBROW[latest["cat"]]}</div><b>{esc(latest["short"])}</b></a>')
    mega = f"""<div class="mega" role="region" aria-label="인사이트 메뉴"><div class="mega-in">
<div><div class="eyebrow">INSIGHTS</div><h3>인사이트</h3><p class="desc">흩어진 데이터를 연결하고 AI가 일하게 만드는 과정을, 솔트웨어가 현장에서 겪은 그대로 씁니다.</p><a class="all arrow" href="{base}index.html">인사이트 전체 보기</a></div>
<div><h4>콘텐츠 · 시리즈</h4>{items}</div>
<div><h4>사례 · 소식</h4><a class="item" href="{base}index.html?cat=case"><b>고객 사례</b><span>{CATS[2][3]}</span></a>
<a class="item" href="{base}index.html#newsletter"><b>뉴스레터</b><span>새 글과 세미나 소식을 한 달에 한 번 보내 드립니다.</span></a></div>
<div>{feat}</div></div></div>"""
    cat_links = "".join(
        f'<a class="lnk{" on" if active == k else ""}" href="{base}index.html?cat={k}" data-cat="{k}">{n}</a>' for k, n, _, _ in CATS)
    return f"""<header class="top"><div class="nav">
<a class="logo" href="{base}index.html" aria-label="솔트웨어 블로그 홈"><i></i>saltware<small>Insights</small></a>
<nav class="menu" aria-label="주요 메뉴">
<div class="has-mega"><a class="lnk{" on" if active == "all" else ""}" href="{base}index.html" data-cat="all">인사이트</a>{mega}</div>
{cat_links}
<a class="pill m-cta" href="{base}contact.html"><span class="spark">✦</span>문의하기</a>
</nav>
<div class="tools">
<a class="icon-btn search-btn" href="{base}index.html?focus=search" aria-label="검색">{ICON_SEARCH}</a>
<a class="pill" href="{base}contact.html"><span class="spark">✦</span>문의하기</a>
<button class="icon-btn burger" aria-label="메뉴 열기" aria-expanded="false">{ICON_MENU}</button>
</div></div></header>"""


def footer(base):
    cats = "".join(f'<a href="{base}index.html?cat={k}">{n}</a>' for k, n, _, _ in CATS)
    return f"""<footer class="bottom"><div class="foot">
<div><a class="logo" href="{base}index.html"><i></i>saltware</a><p>Connect Any Data. Understand with AI. Act with Agents. 솔트웨어 인사이트 블로그 시안입니다.</p></div>
<div><b>Insights</b>{cats}</div>
<div><b>Saltware</b><a href="https://www.saltware.co.kr" target="_blank" rel="noopener">회사 홈페이지</a><a href="https://www.youtube.com/@saltware_youtube" target="_blank" rel="noopener">유튜브</a><a href="https://fitcloud.github.io/" target="_blank" rel="noopener">기술 블로그</a></div>
<div><b>Contact</b><a href="{base}contact.html">문의하기</a><a href="{base}index.html#newsletter">뉴스레터 구독</a></div>
</div><div class="copy">이 사이트는 블로그 기획 과제로 만든 시안입니다. 문의와 구독 폼은 실제로 전송되지 않습니다.</div></footer>
<div class="toast" role="status"></div>"""


def page(title, base, active, css, body, js, latest):
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
{FONT}
<style>{BASE_CSS}{css}</style></head><body>
{header(base, active, latest)}
{body}
{footer(base)}
<script>{BASE_JS}{js}</script>
</body></html>
"""


# ---------- 첫 화면 ----------

HOME_CSS = """
.head{padding:88px 0 40px}
.head h1{font-size:clamp(40px,5.4vw,68px);line-height:1.08;letter-spacing:-0.04em;margin:18px 0 0;font-weight:800}
.head h1 span{color:var(--muted)}
.hero{display:grid;grid-template-columns:1.55fr 1fr;gap:56px;align-items:center}
.hero .im{position:relative;border-radius:28px;overflow:hidden;background:var(--deep);aspect-ratio:16/9;border:1px solid var(--line)}
.hero img{width:100%;height:100%;object-fit:cover;transition:transform 1.2s var(--ease)}
.hero:hover img{transform:scale(1.03)}
.hero .tx{display:flex;flex-direction:column;align-items:flex-start}
.hero .eyebrow{color:var(--accent)}
.hero h2{font-size:clamp(24px,2.5vw,34px);line-height:1.32;letter-spacing:-0.035em;margin:16px 0 0}
.hero:hover h2{text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:6px}
.hero p{margin:16px 0 0;color:var(--muted);font-size:16.5px;line-height:1.7}
.hero .by{margin-top:22px;font-size:14px;color:var(--faint)}
.hero .go{margin-top:32px;width:56px;height:56px;border-radius:50%;background:var(--dark);color:var(--on-dark);display:flex;align-items:center;justify-content:center;font-size:20px;transition:transform .25s var(--ease)}
.hero:hover .go{transform:rotate(-45deg)}
.intro{display:grid;grid-template-columns:1fr 1.6fr;gap:40px;align-items:end;padding:88px 0 28px;border-bottom:1px solid var(--line)}
.intro p{margin:0;color:var(--muted);font-size:16px;line-height:1.75;max-width:360px}
.filter{display:flex;justify-content:flex-end;gap:28px;flex-wrap:wrap;align-items:center}
.tabs{display:flex;gap:26px;flex-wrap:wrap}
.tab{background:none;border:0;padding:6px 0;font-size:15px;font-weight:700;color:var(--faint);cursor:pointer;position:relative}
.tab:hover{color:var(--ink)}
.tab.on{color:var(--accent)}
.tab.on:after{content:"";position:absolute;left:0;right:0;bottom:-2px;height:2px;background:var(--accent)}
.tab sup{font-size:11px;font-weight:600;margin-left:3px;color:var(--faint)}
.search{display:flex;align-items:center;gap:10px;border-bottom:1.5px solid var(--ink);padding:6px 2px;width:240px}
.search input{border:0;outline:0;background:transparent;flex:1;font-size:15px;min-width:0}
.search input::placeholder{color:var(--faint)}
.search button{border:0;background:none;cursor:pointer;color:var(--faint);display:none;padding:0}
.state{display:flex;gap:12px;align-items:center;min-height:56px;color:var(--muted);font-size:14.5px}
.chip{display:inline-flex;align-items:center;gap:8px;background:var(--dark);color:var(--on-dark);border-radius:980px;padding:7px 14px;font-size:13.5px;font-weight:600;border:0;cursor:pointer}
.catdesc{margin:0}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:56px 28px}
.card{display:flex;flex-direction:column}
.card .im{border-radius:20px;overflow:hidden;background:var(--deep);aspect-ratio:16/9;border:1px solid var(--line)}
.card img{width:100%;height:100%;object-fit:cover;transition:transform .9s var(--ease)}
.card:hover img{transform:scale(1.05)}
.card .eyebrow{color:var(--accent);margin:22px 0 10px;font-size:12px}
.card h3{font-size:21px;line-height:1.42;letter-spacing:-0.03em;margin:0;font-weight:700}
.card:hover h3{text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:5px}
.card .sum{color:var(--muted);font-size:15px;line-height:1.65;margin:12px 0 0;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.meta-row{display:flex;gap:10px;align-items:center;margin-top:16px;font-size:13.5px;color:var(--faint);flex-wrap:wrap}
.meta-row button{background:none;border:0;padding:0;color:var(--muted);cursor:pointer;font-size:13.5px}
.meta-row button:hover{color:var(--accent)}
.meta-row i{width:3px;height:3px;border-radius:50%;background:var(--line2)}
.empty{grid-column:1/-1;padding:96px 0;text-align:center;color:var(--muted)}
.empty b{display:block;font-size:22px;color:var(--ink);margin-bottom:10px;letter-spacing:-0.03em}
.more{display:flex;justify-content:center;margin-top:64px}
.soon{margin-top:120px;display:grid;grid-template-columns:1fr 2fr;gap:40px;border-top:1px solid var(--line);padding-top:40px}
.soon h2{font-size:28px;letter-spacing:-0.035em;margin:14px 0 0}
.soon ol{list-style:none;margin:0;padding:0;counter-reset:s}
.soon li{counter-increment:s;display:grid;grid-template-columns:64px 1fr auto;gap:16px;align-items:center;padding:22px 0;border-bottom:1px solid var(--line);font-size:18px;font-weight:600;letter-spacing:-0.02em}
.soon li:before{content:counter(s,decimal-leading-zero);color:var(--faint);font-size:14px;font-weight:600}
.soon li span{font-size:12.5px;color:var(--accent);font-weight:700;letter-spacing:.06em}
.news{margin-top:120px;background:var(--deep);color:var(--ink);border:1px solid var(--line);border-radius:28px;padding:72px 64px;display:grid;grid-template-columns:1.2fr 1fr;gap:48px;align-items:end}
.news .eyebrow{color:var(--accent)}
.news h2{font-size:clamp(28px,3vw,40px);letter-spacing:-0.035em;line-height:1.25;margin:16px 0 14px}
.news p{color:var(--muted);margin:0;font-size:16px;line-height:1.7}
.news form{display:flex;flex-direction:column;gap:14px}
.news .row{display:flex;gap:10px}
.news input{flex:1;height:54px;border-radius:980px;border:1px solid var(--line2);background:var(--card);color:var(--ink);padding:0 22px;outline:0;font-size:15.5px;min-width:0}
.news input:focus{border-color:var(--ink)}
.news input::placeholder{color:var(--faint)}
.news .pill{height:54px}
.news .msg{font-size:14px;color:var(--accent);min-height:1.3em;margin:0 0 0 8px}
@media (max-width:1000px){.hero{grid-template-columns:1fr;gap:28px}.grid{grid-template-columns:1fr 1fr}.intro{grid-template-columns:1fr}.filter{justify-content:flex-start}.news{grid-template-columns:1fr;padding:48px 32px}.soon{grid-template-columns:1fr}}
@media (max-width:640px){.head{padding:48px 0 28px}.hero{grid-template-columns:1fr;gap:24px}.hero .im{border-radius:20px}.hero .go{display:none}.grid{grid-template-columns:1fr;gap:44px}.search{width:100%}.intro{padding-top:56px}.news .row{flex-direction:column}.soon li{grid-template-columns:44px 1fr;font-size:16px}.soon li span{grid-column:2}}
"""

HOME_JS = """
var POSTS=%%POSTS%%,CATS=%%CATS%%,PAGE=6,state={cat:'all',tag:'',q:'',shown:PAGE};
var $=function(s){return document.querySelector(s)},grid=$('#grid'),hero=$('#hero'),input=$('#q'),clr=$('#qclear');
function esc(s){return String(s||'').replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function readURL(){var u=new URLSearchParams(location.search);state.cat=u.get('cat')||'all';state.tag=u.get('tag')||'';state.q=u.get('q')||'';input.value=state.q;
 if(u.get('focus')==='search')setTimeout(function(){input.focus();$('#list').scrollIntoView({behavior:'smooth'})},80)}
function writeURL(){var u=new URLSearchParams();if(state.cat!=='all')u.set('cat',state.cat);if(state.tag)u.set('tag',state.tag);if(state.q)u.set('q',state.q);var s=u.toString();history.replaceState(null,'',location.pathname+(s?'?'+s:'')+location.hash)}
function match(p){if(state.cat!=='all'&&p.cat!==state.cat)return false;if(state.tag&&p.tags.indexOf(state.tag)<0)return false;
 if(state.q){var q=state.q.toLowerCase(),h=(p.title+' '+p.summary+' '+p.tags.join(' ')+' '+p.series).toLowerCase();if(h.indexOf(q)<0)return false}return true}
function card(p){var t=p.tags[0]?'<i></i><button type="button" data-tag="'+esc(p.tags[0])+'">#'+esc(p.tags[0])+'</button>':'';
 return '<a class="card" href="output/'+p.slug+'/preview.html"><div class="im"><img src="output/'+p.slug+'/images/thumbnail.png" alt="" loading="lazy"></div><div class="eyebrow">'+esc(p.eyebrow)+'</div><h3>'+esc(p.short)+'</h3><p class="sum">'+esc(p.summary)+'</p><div class="meta-row"><span>'+esc(p.date.replace(/-/g,'.'))+'</span><i></i><span>'+p.minutes+'분</span>'+t+'</div></a>'}
function render(){
 document.querySelectorAll('.tab').forEach(function(b){b.classList.toggle('on',b.dataset.cat===state.cat)});
 document.querySelectorAll('.menu .lnk[data-cat]').forEach(function(a){a.classList.toggle('on',a.dataset.cat===state.cat)});
 var c=CATS.filter(function(x){return x.key===state.cat})[0],list=POSTS.filter(match),plain=state.cat==='all'&&!state.tag&&!state.q;
 var st=[];if(state.tag)st.push('<button class="chip" id="tagclear">#'+esc(state.tag)+' ✕</button>');
 st.push('<span class="catdesc">'+(c?esc(c.desc)+' ':'')+(list.length?'글 '+list.length+'편':'')+(state.q?' · "'+esc(state.q)+'" 검색 결과':'')+'</span>');
 $('#state').innerHTML=st.join('');clr.style.display=state.q?'block':'none';
 if(!list.length){grid.innerHTML='<div class="empty"><b>'+(plain?'아직 올라온 글이 없어요':'찾는 글이 없어요')+'</b>'+(state.q||state.tag?'다른 말로 검색하거나 필터를 풀어 보세요.':'곧 첫 글이 올라옵니다.')+'</div>'}
 else{grid.innerHTML=list.slice(0,state.shown).map(card).join('')}
 $('#more').style.display=list.length>state.shown?'flex':'none';writeURL()}
document.querySelectorAll('.tab').forEach(function(b){b.addEventListener('click',function(){state.cat=b.dataset.cat;state.shown=PAGE;render()})});
document.querySelectorAll('.menu .lnk[data-cat], .mega a[href*="?cat="]').forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();var m=a.getAttribute('href').match(/cat=(\\w+)/);
 state.cat=m?m[1]:'all';state.tag='';state.q='';input.value='';state.shown=PAGE;document.querySelector('.menu').classList.remove('open');document.body.style.overflow='';a.blur();render();$('#list').scrollIntoView({behavior:'smooth'})})});
document.querySelector('.search-btn').addEventListener('click',function(e){e.preventDefault();$('#list').scrollIntoView({behavior:'smooth'});setTimeout(function(){input.focus()},350)});
var tm;input.addEventListener('input',function(){clearTimeout(tm);tm=setTimeout(function(){state.q=input.value.trim();state.shown=PAGE;render()},150)});
clr.addEventListener('click',function(){input.value='';state.q='';render();input.focus()});
document.addEventListener('click',function(e){var t=e.target.closest('[data-tag]');if(t){e.preventDefault();state.tag=t.dataset.tag;state.shown=PAGE;render();$('#list').scrollIntoView({behavior:'smooth'});return}
 if(e.target.closest('#tagclear')){state.tag='';render()}});
$('#more button').addEventListener('click',function(){state.shown+=PAGE;render()});
$('#newsform').addEventListener('submit',function(e){e.preventDefault();var v=$('#email').value.trim(),m=$('#newsmsg');
 if(!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(v)){m.textContent='이메일 주소를 다시 확인해 주세요.';$('#email').focus();return}
 m.textContent=v+' 으로 구독 신청을 받았어요. (시안이라 실제 발송은 되지 않아요)';$('#email').value=''});
readURL();render();
"""


def build_home(posts, upcoming):
    hero = ""
    if posts:
        p = posts[0]
        hero = (f'<a class="hero" id="hero" href="output/{p["slug"]}/preview.html">'
                f'<div class="im"><img src="output/{p["slug"]}/images/thumbnail.png" alt=""></div>'
                f'<div class="tx"><div class="eyebrow">LATEST · {EYEBROW[p["cat"]]}</div>'
                f'<h2>{esc(p["short"])}</h2><p>{esc(p["summary"])}</p>'
                f'<div class="by">{esc(p["author"])} · {p["date"].replace("-", ".")} · {p["minutes"]}분 읽기</div>'
                f'<span class="go" aria-hidden="true">→</span></div></a>')
    counts = {k: sum(1 for p in posts if p["cat"] == k) for k, _, _, _ in CATS}
    tabs = f'<button class="tab" data-cat="all">전체<sup>{len(posts)}</sup></button>' + "".join(
        f'<button class="tab" data-cat="{k}">{n}<sup>{counts[k]}</sup></button>' for k, n, _, _ in CATS)
    soon = ""
    if upcoming:
        soon = ('<section class="soon"><div><div class="eyebrow">COMING SOON</div><h2>곧 올라올 글<span class="dot">.</span></h2></div><ol>'
                + "".join(f'<li>{esc(u["title"])}<span>{esc(u["series"])}</span></li>' for u in upcoming) + "</ol></section>")
    body = f"""<main class="wrap">
<section class="head"><div class="eyebrow">SALTWARE INSIGHTS</div>
<h1>데이터를 <span>AI가</span><br>일하게 <span>만드는 법</span><span class="dot">.</span></h1></section>
{hero}
<section id="list">
<div class="intro"><p>흩어진 데이터를 연결하고, AI가 맥락을 읽고, 에이전트가 일하게 만드는 과정을 솔트웨어가 현장에서 겪은 그대로 씁니다.</p>
<div class="filter"><div class="tabs" role="tablist" aria-label="시리즈">{tabs}</div>
<label class="search">{ICON_SEARCH}<input id="q" type="search" placeholder="검색" aria-label="글 검색"><button type="button" id="qclear" aria-label="검색어 지우기">✕</button></label></div></div>
<div class="state" id="state" aria-live="polite"></div>
<div class="grid" id="grid"></div>
<div class="more" id="more"><button class="pill line" type="button">더 보기</button></div>
</section>
{soon}
<section class="news" id="newsletter"><div><div class="eyebrow">NEWSLETTER</div><h2>한 달에 한 번,<br>데이터 이야기를 보내 드려요<span class="dot">.</span></h2>
<p>새 글, 고객 사례, 세미나 소식을 메일 한 통으로 정리합니다.</p></div>
<form id="newsform" novalidate><div class="row"><input id="email" type="email" placeholder="회사 이메일" aria-label="이메일"><button class="pill orange" type="submit">구독하기</button></div><p class="msg" id="newsmsg" aria-live="polite"></p></form></section>
</main>"""
    data = [dict({k: p[k] for k in ("slug", "title", "short", "series", "cat", "date", "summary", "tags", "minutes")},
                 eyebrow=EYEBROW[p["cat"]]) for p in posts]
    cats = [{"key": k, "name": n, "desc": d} for k, n, _, d in CATS]
    js = HOME_JS.replace("%%POSTS%%", json.dumps(data, ensure_ascii=False)).replace("%%CATS%%", json.dumps(cats, ensure_ascii=False))
    (ROOT / "index.html").write_text(page("솔트웨어 인사이트 블로그", "", "all", HOME_CSS, body, js, posts[0] if posts else None), encoding="utf-8")


# ---------- 글 페이지 ----------

POST_CSS = """
.progress{position:fixed;top:0;left:0;height:3px;background:var(--dot);width:0;z-index:50}
.post-head{padding:72px 0 44px;max-width:900px}
.crumb{display:flex;gap:10px;align-items:center;color:var(--faint);font-size:14px;margin-bottom:28px}
.crumb a:hover{color:var(--ink)}
.post-head .eyebrow{color:var(--accent)}
.post-head h1{font-size:clamp(30px,4.2vw,52px);line-height:1.2;letter-spacing:-0.04em;margin:16px 0 22px;font-weight:800}
.post-head .sub{font-size:19px;line-height:1.65;color:var(--muted);margin:0 0 32px;max-width:720px}
.byline{display:flex;gap:14px;align-items:center;flex-wrap:wrap;color:var(--muted);font-size:14.5px}
.byline i{width:3px;height:3px;border-radius:50%;background:var(--line2)}
.share{margin-left:auto;display:flex;gap:8px}
.share button{height:38px;padding:0 16px;border-radius:980px;border:1px solid var(--line2);background:transparent;font-size:13.5px;cursor:pointer;color:var(--ink2)}
.share button:hover{background:var(--card)}
.cover{border-radius:28px;overflow:hidden;background:var(--deep);aspect-ratio:16/9;border:1px solid var(--line)}
.cover img{width:100%;height:100%;object-fit:cover}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:96px;padding-top:72px}
article{max-width:700px;font-size:18px;line-height:1.9;color:var(--ink2)}
article p{margin:0 0 26px}
article .lead{font-size:21px;line-height:1.7;color:var(--ink);font-weight:600;letter-spacing:-0.02em;padding-left:22px;border-left:3px solid var(--dot);margin:36px 0}
article .lead strong{color:inherit}
article h2{font-size:28px;line-height:1.35;color:var(--ink);letter-spacing:-0.035em;margin:72px 0 22px;scroll-margin-top:100px}
article strong{color:var(--ink);font-weight:700;background:linear-gradient(transparent 62%,rgba(244,159,32,.28) 62%)}
article figure{margin:44px 0}
article figure img{border-radius:20px;border:1px solid var(--line)}
article a{text-decoration:underline;text-underline-offset:3px;color:var(--accent)}
article ul{padding-left:22px}
.refs{margin-top:56px;padding-top:28px;border-top:1px solid var(--line);font-size:14.5px;color:var(--muted)}
.refs p{margin:0 0 8px;font-weight:700;color:var(--ink2)}
.refs ul{margin:0;padding-left:18px}
.refs li{margin:6px 0;line-height:1.6}
.refs a{word-break:break-all;color:var(--muted)}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin-top:44px}
.tags a{padding:8px 15px;border-radius:980px;border:1px solid var(--line2);font-size:14px;color:var(--ink2)}
.tags a:hover{background:var(--card);color:var(--accent)}
aside .toc{position:sticky;top:112px}
.toc .eyebrow{margin-bottom:18px}
.toc a{display:block;padding:9px 0 9px 16px;border-left:2px solid var(--line);color:var(--faint);font-size:14.5px;line-height:1.5;transition:color .2s,border-color .2s}
.toc a:hover{color:var(--ink)}
.toc a.on{color:var(--ink);border-left-color:var(--dot);font-weight:600}
.side{margin-top:40px;padding:26px;border-radius:20px;background:var(--card);color:var(--muted);font-size:14.5px;line-height:1.65}
.side b{display:block;color:var(--ink);font-size:16.5px;margin-bottom:8px;letter-spacing:-0.02em}
.side .pill{margin-top:18px;height:42px;padding:0 18px;font-size:14px}
.cta{margin-top:80px;border-radius:28px;background:var(--deep);color:var(--ink);border:1px solid var(--line);padding:56px;display:flex;gap:28px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.cta .eyebrow{color:var(--accent)}
.cta h3{font-size:28px;letter-spacing:-0.035em;margin:12px 0 0;line-height:1.35}
.cta .btns{display:flex;gap:10px;flex-wrap:wrap}
.cta .pill.line{color:var(--ink);border-color:var(--line2)}
.cta .pill.line:hover{background:var(--card)}
.pn{display:grid;grid-template-columns:1fr 1fr;margin-top:64px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.pn a,.pn span{padding:30px 0;display:block;font-size:17px;font-weight:600;line-height:1.5;letter-spacing:-0.02em}
.pn small{display:block;font-size:12.5px;letter-spacing:.12em;color:var(--faint);font-weight:700;margin-bottom:8px}
.pn .next{text-align:right;border-left:1px solid var(--line);padding-left:28px}
.pn .prev{padding-right:28px}
.pn a:hover{color:var(--accent)}
.pn span{color:var(--faint);font-weight:500}
.related{margin-top:120px}
.related h3{font-size:28px;letter-spacing:-0.035em;margin:14px 0 36px}
.rgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:28px}
.rgrid .im{border-radius:20px;overflow:hidden;aspect-ratio:16/9;background:var(--deep);border:1px solid var(--line)}
.rgrid img{width:100%;height:100%;object-fit:cover;transition:transform .9s var(--ease)}
.rgrid a:hover img{transform:scale(1.05)}
.rgrid .eyebrow{color:var(--accent);margin:20px 0 8px;font-size:12px}
.rgrid b{font-size:18px;line-height:1.45;letter-spacing:-0.025em;display:block}
@media (max-width:1080px){.layout{grid-template-columns:1fr;gap:0}aside{display:none}article{max-width:none}}
@media (max-width:640px){.post-head{padding:40px 0 28px}.post-head .sub{font-size:17px}.cover{aspect-ratio:16/10;border-radius:20px}.layout{padding-top:44px}
 article{font-size:16.5px}article h2{font-size:23px;margin-top:56px}.share{margin-left:0}.cta{padding:36px 26px}.pn{grid-template-columns:1fr}.pn .next{text-align:left;border-left:0;border-top:1px solid var(--line);padding-left:0}.rgrid{grid-template-columns:1fr}}
"""

POST_JS = """
var bar=document.querySelector('.progress'),art=document.querySelector('article');
function prog(){var r=art.getBoundingClientRect(),t=art.offsetHeight-innerHeight;bar.style.width=Math.min(100,Math.max(0,-r.top/(t>0?t:1)*100))+'%'}
addEventListener('scroll',prog,{passive:true});prog();
var links=document.querySelectorAll('.toc a[href^="#"]');
if('IntersectionObserver' in window&&links.length){var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting)links.forEach(function(l){l.classList.toggle('on',l.getAttribute('href')==='#'+e.target.id)})})},{rootMargin:'-100px 0px -65% 0px'});
document.querySelectorAll('article h2[id]').forEach(function(h){io.observe(h)})}
document.querySelector('#copylink').addEventListener('click',function(){var u=location.href;
 if(navigator.clipboard&&isSecureContext){navigator.clipboard.writeText(u).then(function(){toast('링크를 복사했어요')},function(){fb(u)})}else fb(u)});
function fb(u){var t=document.createElement('textarea');t.value=u;document.body.appendChild(t);t.select();try{document.execCommand('copy');toast('링크를 복사했어요')}catch(e){toast('복사하지 못했어요')}t.remove()}
document.querySelector('#toTop').addEventListener('click',function(){scrollTo({top:0,behavior:'smooth'})});
"""


def build_post(p, posts):
    base = "../../"
    i = posts.index(p)
    newer = posts[i - 1] if i > 0 else None
    older = posts[i + 1] if i + 1 < len(posts) else None
    related = ([q for q in posts if q is not p and q["cat"] == p["cat"]] + [q for q in posts if q is not p and q["cat"] != p["cat"]])[:3]
    toc = "".join(f'<a href="#{sid}">{esc(t)}</a>' for sid, t in p["toc"])
    tags = "".join(f'<a href="{base}index.html?tag={html.escape(t)}">#{esc(t)}</a>' for t in p["tags"])

    def pn(q, label, cls):
        if not q:
            return f'<span class="{cls}"><small>{label}</small>{"첫 글입니다" if cls == "prev" else "가장 최근 글입니다"}</span>'
        return f'<a class="{cls}" href="{base}output/{q["slug"]}/preview.html"><small>{label}</small>{esc(q["short"])}</a>'

    rel = ""
    if related:
        rel = ('<section class="related"><div class="eyebrow">KEEP READING</div><h3>함께 읽으면 좋은 글<span class="dot">.</span></h3><div class="rgrid">'
               + "".join(f'<a href="{base}output/{q["slug"]}/preview.html"><div class="im"><img src="{base}output/{q["slug"]}/images/thumbnail.png" alt="" loading="lazy"></div>'
                         f'<div class="eyebrow">{EYEBROW[q["cat"]]}</div><b>{esc(q["short"])}</b></a>' for q in related)
               + "</div></section>")
    date = p["date"].replace("-", ".")
    body = f"""<div class="progress"></div>
<main class="wrap">
<section class="post-head">
<div class="crumb"><a href="{base}index.html">Insights</a><span>/</span><a href="{base}index.html?cat={p['cat']}">{esc(p['series'])}</a></div>
<div class="eyebrow">{EYEBROW[p['cat']]}</div>
<h1>{esc(p['short'])}</h1>
<p class="sub">{esc(p['summary'])}</p>
<div class="byline"><span>{esc(p['author'])}</span><i></i><span>{date}</span><i></i><span>{p['minutes']}분 읽기</span>
<div class="share"><button id="copylink" type="button">링크 복사</button><button id="toTop" type="button">맨 위로</button></div></div>
</section>
<div class="cover"><img src="images/thumbnail.png" alt="{esc(p['short'])}"></div>
<div class="layout">
<div>
<article>
{p['body_html']}
</article>
<div class="tags">{tags}</div>
<div class="pn">{pn(older, "PREVIOUS", "prev")}{pn(newer, "NEXT", "next")}</div>
</div>
<aside><nav class="toc" aria-label="목차"><div class="eyebrow">CONTENTS</div>{toc}
<div class="side"><b>우리 회사에도 맞을까요?</b>이 주제로 지금 상황을 들려주시면 담당자가 시작할 지점을 같이 찾아 드립니다.<br><a class="pill" href="{base}contact.html?topic={p['cat']}">문의하기</a></div></nav></aside>
</div>
<section class="cta"><div><div class="eyebrow">START WITH YOUR GOAL</div><h3>우리 회사 데이터는<br>지금 어느 단계일까요?</h3></div>
<div class="btns"><a class="pill" href="{base}contact.html?topic={p['cat']}"><span class="spark">✦</span>문의하기</a><a class="pill line" href="{base}index.html#newsletter">뉴스레터 구독</a></div></section>
{rel}
</main>"""
    out = ROOT / "output" / p["slug"] / "preview.html"
    out.write_text(page(f"{p['short']} | 솔트웨어 인사이트", base, p["cat"], POST_CSS, body, POST_JS, posts[0]), encoding="utf-8")


# ---------- 문의하기 ----------

CONTACT_CSS = """
.c-wrap{display:grid;grid-template-columns:1fr 1.15fr;gap:96px;padding:88px 0 0}
.c-wrap h1{font-size:clamp(36px,4.6vw,60px);line-height:1.1;letter-spacing:-0.04em;margin:18px 0 24px;font-weight:800}
.c-wrap h1 span{color:var(--muted)}
.lede{color:var(--muted);font-size:17px;line-height:1.75;margin:0}
.facts{margin:48px 0 0;padding:0;list-style:none;border-top:1px solid var(--line)}
.facts li{display:grid;grid-template-columns:120px 1fr;gap:16px;padding:20px 0;border-bottom:1px solid var(--line);font-size:15.5px;color:var(--ink2)}
.facts b{font-size:12.5px;letter-spacing:.12em;color:var(--faint);font-weight:700;padding-top:2px}
.facts a{color:var(--accent)}
form.c{background:var(--card);border-radius:28px;padding:48px}
.f{margin-bottom:22px}
.f label{display:block;font-weight:700;font-size:14.5px;margin-bottom:10px}
.f label i{color:var(--dot-deep);font-style:normal}
.f input,.f select,.f textarea{width:100%;border:0;border-bottom:1.5px solid var(--line2);padding:10px 2px 12px;background:transparent;outline:0;font-size:16px;border-radius:0}
.f input:focus,.f select:focus,.f textarea:focus{border-bottom-color:var(--ink)}
.f textarea{min-height:120px;resize:vertical}
.f .err{color:#B1362E;font-size:13.5px;margin-top:8px;display:none}
.f.bad .err{display:block}.f.bad input,.f.bad textarea{border-bottom-color:#B1362E}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:28px}
.topics{display:flex;flex-wrap:wrap;gap:8px}
.topics label{margin:0;font-weight:500;font-size:14.5px;border:1px solid var(--line2);border-radius:980px;padding:9px 16px;cursor:pointer;color:var(--ink2)}
.topics input{position:absolute;opacity:0;pointer-events:none}
.topics input:checked+span{color:var(--on-dark)}
.topics label:has(input:checked){background:var(--dark);border-color:var(--dark);color:var(--on-dark)}
.agree{display:flex;gap:10px;align-items:flex-start;font-size:14.5px;color:var(--muted);margin:8px 0 28px}
.agree input{margin-top:4px;accent-color:var(--dark)}
.done{display:none;text-align:center;padding:56px 8px}
.done .mark{width:64px;height:64px;border-radius:50%;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:28px;margin:0 auto 24px}
.done b{display:block;font-size:26px;letter-spacing:-0.035em;margin-bottom:12px}
.done p{color:var(--muted);line-height:1.7;margin:0 0 28px}
.done .btns{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
form.c.sent .fields{display:none}form.c.sent .done{display:block}
@media (max-width:960px){.c-wrap{grid-template-columns:1fr;gap:48px;padding-top:48px}}
@media (max-width:560px){.row2{grid-template-columns:1fr;gap:0}form.c{padding:28px 22px}.facts li{grid-template-columns:1fr;gap:4px}}
"""

CONTACT_JS = """
var f=document.querySelector('form.c'),t=new URLSearchParams(location.search).get('topic');
if(t){var r=f.querySelector('input[name="topic"][value="'+t+'"]');if(r)r.checked=true}
function check(el){var b=el.closest('.f'),ok=el.checkValidity();if(b)b.classList.toggle('bad',!ok);return ok}
f.querySelectorAll('.f input,.f textarea').forEach(function(el){el.addEventListener('blur',function(){if(el.value)check(el)})});
f.addEventListener('submit',function(e){e.preventDefault();var ok=true,first=null;
 f.querySelectorAll('.f input[required],.f textarea').forEach(function(el){if(!check(el)){ok=false;first=first||el}});
 var ag=document.querySelector('#agree');if(ok&&!ag.checked){ok=false;toast('개인정보 수집에 동의해 주세요');first=ag}
 if(!ok){first.focus();return}
 document.querySelector('#doneName').textContent=document.querySelector('#name').value.trim();f.classList.add('sent');scrollTo({top:0,behavior:'smooth'})});
document.querySelector('#again').addEventListener('click',function(){f.reset();f.classList.remove('sent')});
"""


def build_contact(latest):
    topics = "".join(f'<label><input type="radio" name="topic" value="{k}"><span>{n}</span></label>' for k, n, _, _ in CATS)
    topics += '<label><input type="radio" name="topic" value="etc"><span>그 밖의 문의</span></label>'
    body = f"""<main class="wrap"><div class="c-wrap">
<div><div class="eyebrow">CONTACT</div><h1>무엇이든<br><span>편하게</span> 물어보세요<span class="dot">.</span></h1>
<p class="lede">블로그를 읽다가 우리 회사에도 맞을지 궁금해졌다면, 지금 상황을 짧게 적어 주세요. 담당자가 확인하고 연락드립니다.</p>
<ul class="facts"><li><b>RESPONSE</b>영업일 기준 1~2일 <span class="todo">[확인 필요]</span></li><li><b>TOPICS</b>데이터 통합, AI 도입, 클라우드 전환·운영, 계정·권한 관리</li><li><b>WEBSITE</b><a href="https://www.saltware.co.kr" target="_blank" rel="noopener">saltware.co.kr</a></li></ul></div>
<form class="c" novalidate><div class="fields">
<div class="row2"><div class="f"><label for="name">이름 <i>*</i></label><input id="name" required autocomplete="name"><p class="err">이름을 적어 주세요.</p></div>
<div class="f"><label for="company">회사 <i>*</i></label><input id="company" required autocomplete="organization"><p class="err">회사 이름을 적어 주세요.</p></div></div>
<div class="f"><label for="mail">회사 이메일 <i>*</i></label><input id="mail" type="email" required autocomplete="email"><p class="err">이메일 주소를 확인해 주세요.</p></div>
<div class="f"><label>어떤 글을 보고 오셨나요?</label><div class="topics">{topics}</div></div>
<div class="f"><label for="msg">문의 내용 <i>*</i></label><textarea id="msg" required minlength="10" placeholder="예: 데이터가 ERP와 CRM에 나뉘어 있는데 AI로 보고서를 만들고 싶어요."></textarea><p class="err">10자 이상 적어 주세요.</p></div>
<label class="agree"><input type="checkbox" id="agree">문의 답변을 위해 이름, 회사, 이메일을 수집하는 데 동의합니다.</label>
<button class="pill" type="submit"><span class="spark">✦</span>문의 보내기</button></div>
<div class="done"><div class="mark">✓</div><b><span id="doneName"></span>님, 문의를 받았어요<span class="dot">.</span></b><p>이 사이트는 시안이라 실제로 전송되지는 않았어요.<br>실제 운영에서는 이 자리에서 담당자에게 메일이 갑니다.</p>
<div class="btns"><a class="pill line" href="index.html">블로그로 돌아가기</a><button class="pill" type="button" id="again">하나 더 문의하기</button></div></div>
</form></div></main>"""
    (ROOT / "contact.html").write_text(page("문의하기 | 솔트웨어 인사이트", "", "contact", CONTACT_CSS, body, CONTACT_JS, latest), encoding="utf-8")


def main():
    import theme  # 화면 디자인은 theme.py에 있다
    posts = load_posts()
    theme.build(posts)
    print(f"사이트 생성 완료: 글 {len(posts)}편, index.html, contact.html")


if __name__ == "__main__":
    main()

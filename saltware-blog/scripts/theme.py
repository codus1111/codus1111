"""솔트웨어 인사이트 블로그 화면 (어두운 테크 매거진).

솔트웨어 로고(오렌지 점 4개 + saltware)와 오렌지만 브랜드에서 가져온다.
바탕은 숯색, 글자는 흰색, 강조는 오렌지 한 가지. 표지는 그림 대신 글의 핵심 단어를 크게 쓴다.
"""
import html
import json

from build_site import CATS, CAT_BY_NAME, ROOT, esc, load_upcoming

EN = {k: e for k, _, e, _ in CATS}

FONTS = ('<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">'
         '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap">')

CSS = """
:root{--bg:#0D0D0D;--panel:#141414;--panel2:#1B1B1B;--line:#262626;--line2:#333;--text:#F2F2F2;--text2:#C4C4C4;--muted:#8C8C8C;
--o:#F49F20;--o2:#E8811A;--o-soft:rgba(244,159,32,.12);--mono:'IBM Plex Mono','Pretendard Variable',Pretendard,ui-monospace,monospace;--w:1240px;--ease:cubic-bezier(.2,.7,.2,1)}
*{box-sizing:border-box}html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--text);font-family:'Pretendard Variable',Pretendard,-apple-system,'Malgun Gothic',sans-serif;letter-spacing:-.01em;-webkit-font-smoothing:antialiased;word-break:keep-all}
a{color:inherit;text-decoration:none}img{display:block;max-width:100%}button,input,select,textarea{font:inherit;color:inherit}
::selection{background:var(--o);color:#000}:focus-visible{outline:2px solid var(--o);outline-offset:3px;border-radius:4px}
.wrap{max-width:var(--w);margin:0 auto;padding:0 40px}
.mono{font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.o{color:var(--o)}
.btn{display:inline-flex;align-items:center;gap:10px;height:46px;padding:0 22px;border-radius:999px;font-weight:700;font-size:15px;border:1px solid var(--line2);background:transparent;cursor:pointer;transition:.2s}
.btn:hover{border-color:var(--text)}.btn.fill{background:var(--o);border-color:var(--o);color:#0D0D0D}.btn.fill:hover{background:#FFB548;border-color:#FFB548}
.arr{transition:transform .25s var(--ease);display:inline-block}a:hover .arr,button:hover .arr{transform:translateX(4px)}
/* 머리글 */
.top{position:sticky;top:0;z-index:50;background:rgba(13,13,13,.92);border-bottom:1px solid var(--line)}
.nav{max-width:var(--w);margin:0 auto;padding:0 40px;height:72px;display:flex;align-items:center;gap:48px}
.logo{display:flex;align-items:center;gap:10px;font-weight:800;font-size:25px;letter-spacing:-.045em;color:var(--text)}
.logo i{width:21px;height:21px;flex:none;background:radial-gradient(circle,var(--o) 4.4px,transparent 4.8px) 0 0/10.5px 10.5px}
.logo small{font-family:var(--mono);font-weight:500;font-size:11px;letter-spacing:.14em;color:var(--muted);margin-left:6px}
.menu{display:flex;gap:30px;align-items:center}
.menu a{font-size:15px;color:var(--text2);padding:6px 0;position:relative}.menu a:hover{color:var(--text)}
.menu a.on{color:var(--text)}.menu a.on:before{content:"";position:absolute;left:-12px;top:50%;width:5px;height:5px;margin-top:-2.5px;border-radius:50%;background:var(--o)}
.tools{margin-left:auto;display:flex;gap:10px;align-items:center}
.ib{width:44px;height:44px;border-radius:50%;border:1px solid var(--line2);background:transparent;display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--text)}
.ib:hover{border-color:var(--text)}.burger{display:none}
.drawer{display:none;position:fixed;top:64px;left:0;right:0;bottom:0;z-index:49;background:var(--bg);padding:20px;overflow-y:auto}
.drawer.open{display:block}.drawer a{display:flex;justify-content:space-between;align-items:center;padding:20px 0;border-bottom:1px solid var(--line);font-size:22px;font-weight:700}
.drawer a span{font-family:var(--mono);font-size:12px;color:var(--muted);font-weight:400}.drawer .btn{margin-top:28px;width:100%;justify-content:center;font-size:16px;border-bottom:1px solid var(--o)}
/* 바닥글 */
.foot{border-top:1px solid var(--line);margin-top:140px}
.foot .wrap{display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr;gap:40px;padding-top:64px;padding-bottom:48px;font-size:14.5px;color:var(--muted)}
.foot p{margin:18px 0 0;line-height:1.7;max-width:320px}.foot b{display:block;font-family:var(--mono);font-size:11.5px;letter-spacing:.12em;color:var(--text2);margin-bottom:16px;font-weight:500}
.foot a:not(.logo){display:block;margin:10px 0}.foot a:hover{color:var(--o)}
.copy{border-top:1px solid var(--line)}.copy .wrap{padding-top:20px;padding-bottom:36px;font-family:var(--mono);font-size:11.5px;color:#5E5E5E;letter-spacing:.04em}
.toast{position:fixed;left:50%;bottom:30px;max-width:calc(100vw - 32px);white-space:nowrap;transform:translate(-50%,14px);background:var(--o);color:#000;font-weight:700;padding:12px 22px;border-radius:999px;font-size:14.5px;opacity:0;transition:.25s;pointer-events:none;z-index:70}
.toast.show{opacity:1;transform:translate(-50%,0)}
/* 글자 표지 */
.kw{position:relative;overflow:hidden;background:var(--panel);border:1px solid var(--line);border-radius:18px;display:flex;align-items:flex-end;isolation:isolate}
.kw:before{content:"";position:absolute;inset:0;z-index:-1;background:radial-gradient(circle at var(--gx,78%) var(--gy,22%),rgba(244,159,32,.38),rgba(244,159,32,0) 46%),
 repeating-linear-gradient(90deg,rgba(255,255,255,.035) 0 1px,transparent 1px 64px),repeating-linear-gradient(0deg,rgba(255,255,255,.035) 0 1px,transparent 1px 64px)}
.kw b{font-weight:800;letter-spacing:-.06em;line-height:.82;color:var(--text);padding:0 0 .08em .06em;white-space:nowrap}
.kw b:after{content:".";color:var(--o)}
.kw .tag{position:absolute;top:18px;left:20px}.kw .num{position:absolute;top:18px;right:20px}
.todo{color:#FF6B5B;font-weight:600}
@media (max-width:1080px){.nav{gap:32px}.menu{gap:22px}.logo small{display:none}}
@media (max-width:400px){.wrap,.nav{padding:0 16px!important}.logo{font-size:21px}.logo i{width:18px;height:18px;background-size:9px 9px}.ib{width:40px;height:40px}}
@media (max-width:780px){.wrap,.nav{padding:0 20px}.nav{height:64px}.menu,.tools .btn{display:none}.burger{display:flex}.foot .wrap{grid-template-columns:1fr 1fr}}
"""

BASE_JS = """
function toast(m){var t=document.querySelector('.toast');t.textContent=m;t.classList.add('show');clearTimeout(t._h);t._h=setTimeout(function(){t.classList.remove('show')},2200)}
(function(){var b=document.querySelector('.burger'),d=document.querySelector('.drawer'),ic=b.innerHTML;
function set(o){d.classList.toggle('open',o);b.setAttribute('aria-expanded',o);b.innerHTML=o?'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 6l12 12M18 6 6 18"/></svg>':ic;document.body.style.overflow=o?'hidden':''}
b.addEventListener('click',function(){set(!d.classList.contains('open'))});d.addEventListener('click',function(e){if(e.target.closest('a'))set(false)});
addEventListener('resize',function(){if(innerWidth>780)set(false)});addEventListener('keydown',function(e){if(e.key==='Escape')set(false)})})();
"""

I_SEARCH = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>'
I_MENU = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 8h16M4 16h16"/></svg>'


def kw(p, size, tag=True, idx=None):
    """핵심 단어 표지. 글마다 오렌지 빛 위치가 조금씩 다르다."""
    s = sum(map(ord, p["slug"]))
    gx, gy = 55 + s % 35, 12 + (s // 7) % 40
    t = f'<span class="mono tag">{EN[p["cat"]]}</span>' if tag else ""
    n = f'<span class="mono num">{idx}</span>' if idx else ""
    return f'<div class="kw" style="--gx:{gx}%;--gy:{gy}%"><b style="font-size:{size}">{esc(p["cover"])}</b>{t}{n}</div>'


def header(base, active):
    links = [("all", "인사이트", f"{base}index.html")] + [(k, n, f"{base}index.html?cat={k}#archive") for k, n, _, _ in CATS]
    menu = "".join(f'<a href="{u}" data-cat="{k}" class="{"on" if active == k else ""}">{n}</a>' for k, n, u in links)
    drawer = "".join(f'<a href="{u}">{n}<span>{EN.get(k, "ALL")}</span></a>' for k, n, u in links)
    return f"""<header class="top"><div class="nav">
<a class="logo" href="{base}index.html" aria-label="솔트웨어 인사이트 홈"><i></i>saltware<small>INSIGHTS</small></a>
<nav class="menu" aria-label="주요 메뉴">{menu}</nav>
<div class="tools"><a class="ib search-btn" href="{base}index.html?focus=search#archive" aria-label="검색">{I_SEARCH}</a>
<a class="btn" href="{base}contact.html">문의하기 <span class="arr o">→</span></a>
<button class="ib burger" aria-label="메뉴" aria-expanded="false">{I_MENU}</button></div></div></header>
<nav class="drawer" aria-label="모바일 메뉴">{drawer}<a class="btn fill" href="{base}contact.html">문의하기</a></nav>"""


def footer(base):
    cats = "".join(f'<a href="{base}index.html?cat={k}#archive">{n}</a>' for k, n, _, _ in CATS)
    return f"""<footer class="foot"><div class="wrap">
<div><a class="logo" href="{base}index.html"><i></i>saltware</a><p>Connect Any Data. Understand with AI. Act with Agents.<br>솔트웨어가 현장에서 겪은 데이터·AI 이야기를 씁니다.</p></div>
<div><b>SERIES</b>{cats}</div>
<div><b>SALTWARE</b><a href="https://www.saltware.co.kr" target="_blank" rel="noopener">회사 홈페이지</a><a href="https://www.youtube.com/@saltware_youtube" target="_blank" rel="noopener">유튜브</a><a href="https://fitcloud.github.io/" target="_blank" rel="noopener">기술 블로그</a></div>
<div><b>CONTACT</b><a href="{base}contact.html">문의하기</a><a href="{base}index.html#newsletter">뉴스레터</a></div>
</div><div class="copy"><div class="wrap">블로그 기획 과제용 시안 · 문의·구독 폼은 실제로 전송되지 않습니다</div></div></footer><div class="toast" role="status"></div>"""


def page(title, base, active, css, body, js):
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0D0D0D"><title>{esc(title)}</title>{FONTS}<style>{CSS}{css}</style></head><body>
{header(base, active)}
{body}
{footer(base)}
<script>{BASE_JS}{js}</script></body></html>
"""


# ---------- 첫 화면 ----------

HOME_CSS = """
.hero{padding:96px 0 72px;display:grid;grid-template-columns:1fr auto;gap:40px;align-items:end;border-bottom:1px solid var(--line)}
.hero h1{font-size:clamp(38px,8.4vw,124px);line-height:.94;letter-spacing:-.06em;margin:22px 0 0;font-weight:800}
.hero h1 em{font-style:normal;color:var(--muted)}
.stats{display:flex;gap:40px;padding-bottom:10px}.stats div{text-align:right}.stats b{display:block;font-size:44px;font-weight:700;letter-spacing:-.04em;line-height:1}
.stats span{display:block;margin-top:8px}
.feat{display:grid;grid-template-columns:1.25fr 1fr;gap:48px;padding:72px 0;border-bottom:1px solid var(--line)}
.feat .kw{aspect-ratio:4/3}.feat:hover .kw{border-color:var(--line2)}
.feat .tx{display:flex;flex-direction:column}.feat h2{font-size:clamp(28px,3vw,42px);line-height:1.22;letter-spacing:-.04em;margin:18px 0 16px}
.feat .dek{color:var(--text2);font-size:17px;line-height:1.7;margin:0}
.pts{list-style:none;margin:28px 0 0;padding:0;border-top:1px solid var(--line)}
.pts li{display:grid;grid-template-columns:40px 1fr;gap:10px;padding:15px 0;border-bottom:1px solid var(--line);font-size:15.5px;line-height:1.6;color:var(--text2)}
.pts li span{font-family:var(--mono);font-size:12px;color:var(--o);padding-top:4px}
.feat .go{margin-top:auto;padding-top:28px;font-weight:700}
.sec-h{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;padding:96px 0 32px}
.sec-h h2{font-size:clamp(28px,3.4vw,44px);letter-spacing:-.045em;margin:12px 0 0;line-height:1.1}
.sec-h p{margin:0;color:var(--muted);max-width:360px;font-size:15px;line-height:1.6}
.cases{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:18px;overflow:hidden}
.case{background:var(--bg);padding:28px 24px 24px;display:flex;flex-direction:column;min-height:280px;transition:background .25s}
.case:hover{background:var(--panel)}.case .big{font-size:30px;font-weight:800;letter-spacing:-.04em;line-height:1.2;color:var(--o);margin:18px 0 0}
.case h3{font-size:16px;line-height:1.5;font-weight:600;margin:auto 0 0;padding-top:28px;color:var(--text2)}.case:hover h3{color:var(--text)}
.case .mono{display:flex;justify-content:space-between}
.bar{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap;padding-bottom:20px;border-bottom:1px solid var(--line)}
.pills{display:flex;gap:6px;flex-wrap:wrap}
.pill{height:38px;padding:0 16px;border-radius:999px;border:1px solid var(--line2);background:transparent;font-size:14px;color:var(--text2);cursor:pointer}
.pill:hover{color:var(--text);border-color:var(--text2)}.pill.on{background:var(--text);color:#000;border-color:var(--text)}.pill sup{font-family:var(--mono);font-size:10px;margin-left:4px;opacity:.6}
.search{display:flex;align-items:center;gap:10px;height:42px;width:280px;border:1px solid var(--line2);border-radius:999px;padding:0 16px;color:var(--muted)}
.search:focus-within{border-color:var(--o);color:var(--text)}.search input{flex:1;border:0;outline:0;background:transparent;min-width:0;font-size:15px}
.search button{border:0;background:none;color:var(--muted);cursor:pointer;display:none;padding:0}
.state{display:flex;gap:10px;align-items:center;min-height:52px;color:var(--muted);font-size:14px}
.chip{display:inline-flex;gap:8px;align-items:center;height:30px;padding:0 12px;border-radius:999px;background:var(--o-soft);color:var(--o);border:0;font-size:13px;font-weight:600;cursor:pointer}
.rows{border-top:1px solid var(--line)}
.row{display:grid;grid-template-columns:56px 150px 1fr 170px 32px;gap:24px;align-items:center;padding:26px 0;border-bottom:1px solid var(--line);position:relative}
.row:before{content:"";position:absolute;left:0;top:-1px;height:1px;width:0;background:var(--o);transition:width .5s var(--ease)}
.row:hover:before{width:100%}.row .i{font-family:var(--mono);font-size:13px;color:var(--muted)}.row:hover .i{color:var(--o)}
.row .kw{height:96px;border-radius:12px}.row .kw b{font-size:30px}.row .kw .tag{display:none}
.row h3{font-size:20px;line-height:1.4;letter-spacing:-.03em;margin:8px 0 6px;font-weight:700}
.row p{margin:0;color:var(--muted);font-size:14.5px;line-height:1.6;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
.row .meta{text-align:right;font-family:var(--mono);font-size:12px;color:var(--muted);line-height:1.8}
.row .ar{font-size:20px;color:var(--muted)}.row:hover .ar{color:var(--o);transform:translateX(4px)}.row .ar{transition:.25s var(--ease)}
.row .tg{background:none;border:0;padding:0;cursor:pointer;color:var(--muted);font-family:var(--mono);font-size:12px}.row .tg:hover{color:var(--o)}
.empty{padding:90px 0;text-align:center;color:var(--muted);border-bottom:1px solid var(--line)}.empty b{display:block;color:var(--text);font-size:22px;margin-bottom:8px}
.more{display:flex;justify-content:center;margin-top:44px}
.news{margin-top:120px;display:grid;grid-template-columns:1fr 1fr;gap:56px;padding:56px;border:1px solid var(--line);border-radius:24px;background:radial-gradient(circle at 100% 0,rgba(244,159,32,.16),transparent 45%),var(--panel)}
.news h2{font-size:clamp(28px,3vw,40px);letter-spacing:-.04em;line-height:1.2;margin:14px 0 12px}.news p{margin:0;color:var(--text2);line-height:1.7}
.news form{display:flex;flex-direction:column;justify-content:flex-end;gap:12px}.news .f{display:flex;gap:8px}
.news input{flex:1;min-width:0;height:52px;border-radius:999px;border:1px solid var(--line2);background:var(--bg);padding:0 20px;outline:0}.news input:focus{border-color:var(--o)}
.news .btn{height:52px}.news .msg{min-height:1.3em;margin:0 0 0 6px;color:var(--o);font-size:14px}
.soon{margin-top:20px;font-size:14px;color:var(--muted)}.soon b{color:var(--text2);font-weight:500}
@media (max-width:1100px){.cases{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:none}.cases::-webkit-scrollbar{display:none}.case{flex:0 0 280px;scroll-snap-align:start}.row{grid-template-columns:40px 110px 1fr 28px}.row .meta{display:none}}
@media (max-width:760px){.hero{grid-template-columns:1fr;padding:56px 0 44px}.stats{gap:28px}.stats div{text-align:left}.stats b{font-size:34px}
.feat{grid-template-columns:1fr;gap:28px;padding:44px 0}.case{flex-basis:76%;min-height:230px}
.row{grid-template-columns:1fr 24px;gap:14px}.row .i,.row .kw{display:none}.search{width:100%}.news{grid-template-columns:1fr;padding:32px 24px}.news .f{flex-direction:column}.sec-h{flex-direction:column;align-items:flex-start;padding-top:72px}}
@media (max-width:400px){.stats{gap:18px}.stats b{font-size:28px}.feat h2{font-size:24px}.pill{padding:0 12px;font-size:13px}.news{padding:26px 18px}}
"""

HOME_JS = """
var P=%%POSTS%%,C=%%CATS%%,N=8,s={cat:'all',tag:'',q:'',n:N},$=function(x){return document.querySelector(x)},rows=$('#rows'),q=$('#q'),qc=$('#qc');
function e(x){return String(x||'').replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function rd(){var u=new URLSearchParams(location.search);s.cat=u.get('cat')||'all';s.tag=u.get('tag')||'';s.q=u.get('q')||'';q.value=s.q;if(u.get('focus')==='search')setTimeout(function(){q.focus()},300)}
function wr(){var u=new URLSearchParams();if(s.cat!=='all')u.set('cat',s.cat);if(s.tag)u.set('tag',s.tag);if(s.q)u.set('q',s.q);var x=u.toString();history.replaceState(null,'',location.pathname+(x?'?'+x:'')+location.hash)}
function ok(p){if(s.cat!=='all'&&p.cat!==s.cat)return false;if(s.tag&&p.tags.indexOf(s.tag)<0)return false;if(s.q){var h=(p.title+' '+p.summary+' '+p.tags.join(' ')+' '+p.series+' '+p.cover).toLowerCase();if(h.indexOf(s.q.toLowerCase())<0)return false}return true}
function row(p,i){var t=p.tags[0]?'<br><button type="button" class="tg" data-tag="'+e(p.tags[0])+'">#'+e(p.tags[0])+'</button>':'';
return '<a class="row" href="output/'+p.slug+'/preview.html"><span class="i">'+String(i+1).padStart(2,'0')+'</span>'+p.kw+'<div><span class="mono o">'+e(p.en)+'</span><h3>'+e(p.short)+'</h3><p>'+e(p.summary)+'</p></div><div class="meta">'+e(p.date.replace(/-/g,'.'))+'<br>'+p.minutes+' MIN'+t+'</div><span class="ar">→</span></a>'}
function draw(){document.querySelectorAll('.pill').forEach(function(b){b.classList.toggle('on',b.dataset.cat===s.cat)});
document.querySelectorAll('.menu a').forEach(function(a){a.classList.toggle('on',a.dataset.cat===s.cat)});
var l=P.filter(ok),c=C.filter(function(x){return x.key===s.cat})[0],h=[];if(s.tag)h.push('<button class="chip" id="tc">#'+e(s.tag)+' ✕</button>');
h.push('<span>'+(c?e(c.desc)+' · ':'')+(l.length?l.length+'편':'')+(s.q?' · "'+e(s.q)+'" 검색':'')+'</span>');$('#state').innerHTML=h.join('');qc.style.display=s.q?'block':'none';
rows.innerHTML=l.length?l.slice(0,s.n).map(row).join(''):'<div class="empty"><b>찾는 글이 없어요</b>다른 말로 검색하거나 필터를 풀어 보세요.</div>';
$('#more').style.display=l.length>s.n?'flex':'none';wr()}
document.querySelectorAll('.pill').forEach(function(b){b.addEventListener('click',function(){s.cat=b.dataset.cat;s.n=N;draw()})});
document.querySelectorAll('.menu a[data-cat],.drawer a[href*="cat="]').forEach(function(a){a.addEventListener('click',function(ev){var m=a.getAttribute('href').match(/cat=(\\w+)/);if(!m&&a.dataset.cat!=='all')return;ev.preventDefault();s.cat=m?m[1]:'all';s.tag='';s.q='';q.value='';s.n=N;draw();$('#archive').scrollIntoView({behavior:'smooth'})})});
$('.search-btn').addEventListener('click',function(ev){ev.preventDefault();$('#archive').scrollIntoView({behavior:'smooth'});setTimeout(function(){q.focus()},350)});
var tm;q.addEventListener('input',function(){clearTimeout(tm);tm=setTimeout(function(){s.q=q.value.trim();s.n=N;draw()},150)});qc.addEventListener('click',function(){q.value='';s.q='';draw();q.focus()});
document.addEventListener('click',function(ev){var t=ev.target.closest('[data-tag]');if(t){ev.preventDefault();s.tag=t.dataset.tag;s.n=N;draw();$('#archive').scrollIntoView({behavior:'smooth'});return}if(ev.target.closest('#tc')){s.tag='';draw()}});
$('#more button').addEventListener('click',function(){s.n+=N;draw()});
$('#nf').addEventListener('submit',function(ev){ev.preventDefault();var v=$('#em').value.trim(),m=$('#nm');if(!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(v)){m.textContent='이메일 주소를 다시 확인해 주세요.';$('#em').focus();return}m.textContent=v+' 으로 구독 신청을 받았어요. (시안이라 실제 발송은 되지 않아요)';$('#em').value=''});
rd();draw();
"""


def build_home(posts):
    f = posts[0]
    cases = [p for p in posts if p["cat"] == "case"]
    pts = "".join(f'<li><span>0{i}</span>{esc(t)}</li>' for i, t in enumerate(f["points"], 1))
    case_html = "".join(
        f'<a class="case" href="output/{p["slug"]}/preview.html"><div class="mono"><span>CASE {i:02d}</span><span class="o">→</span></div>'
        f'<div class="big">{esc(p["highlight"] or p["cover"])}</div><h3>{esc(p["short"])}</h3></a>' for i, p in enumerate(cases, 1))
    counts = {k: sum(1 for p in posts if p["cat"] == k) for k, _, _, _ in CATS}
    pills = f'<button class="pill" data-cat="all">전체<sup>{len(posts)}</sup></button>' + "".join(
        f'<button class="pill" data-cat="{k}">{n}<sup>{counts[k]}</sup></button>' for k, n, _, _ in CATS)
    soon = " · ".join(f'<b>{esc(u["title"])}</b>' for u in load_upcoming())
    body = f"""<main class="wrap">
<section class="hero"><div><div class="mono">SALTWARE INSIGHTS <span class="o">/</span> DATA · AI · CLOUD</div>
<h1>데이터를<br><em>AI가</em> 일하게<span class="o">.</span></h1></div>
<div class="stats"><div><b>{len(posts)}</b><span class="mono">ARTICLES</span></div><div><b>{len(CATS)}</b><span class="mono">SERIES</span></div><div><b>{len(cases)}</b><span class="mono">CASES</span></div></div></section>
<a class="feat" href="output/{f["slug"]}/preview.html">{kw(f, "clamp(64px,10vw,150px)", idx="LATEST")}
<div class="tx"><span class="mono o">{EN[f["cat"]]} · {f["date"].replace("-", ".")}</span><h2>{esc(f["short"])}</h2><p class="dek">{esc(f["summary"])}</p>
<ul class="pts">{pts}</ul><span class="go">읽어 보기 <span class="arr o">→</span></span></div></a>
<div class="sec-h"><div><div class="mono">CUSTOMER STORIES</div><h2>숫자로 보는 고객 사례<span class="o">.</span></h2></div><p>고객사와 함께 풀어 온 문제를 한 줄의 숫자로 먼저 보고, 자세한 이야기는 글에서 읽어 보세요.</p></div>
<div class="cases">{case_html}</div>
<section id="archive"><div class="sec-h"><div><div class="mono">ALL ARTICLES</div><h2>모든 글<span class="o">.</span></h2></div><p>시리즈로 거르고, 제목이나 태그로 찾아보세요.</p></div>
<div class="bar"><div class="pills" role="tablist" aria-label="시리즈">{pills}</div>
<label class="search">{I_SEARCH}<input id="q" type="search" placeholder="검색" aria-label="글 검색"><button type="button" id="qc" aria-label="지우기">✕</button></label></div>
<div class="state" id="state" aria-live="polite"></div><div class="rows" id="rows"></div>
<div class="more" id="more"><button class="btn" type="button">더 보기 <span class="arr">↓</span></button></div></section>
<section class="news" id="newsletter"><div><div class="mono o">NEWSLETTER</div><h2>한 달에 한 번,<br>데이터 이야기를 보내 드려요.</h2><p>새 글과 고객 사례, 세미나 소식을 메일 한 통으로 정리합니다.</p>
<p class="soon">다음 글 · {soon}</p></div>
<form id="nf" novalidate><div class="f"><input id="em" type="email" placeholder="회사 이메일" aria-label="이메일"><button class="btn fill" type="submit">구독하기</button></div><p class="msg" id="nm" aria-live="polite"></p></form></section>
</main>"""
    data = [dict({k: p[k] for k in ("slug", "title", "short", "series", "cat", "date", "summary", "tags", "minutes", "cover")},
                 en=EN[p["cat"]], kw=kw(p, "30px", tag=False)) for p in posts]
    cats = [{"key": k, "desc": d} for k, _, _, d in CATS]
    js = HOME_JS.replace("%%POSTS%%", json.dumps(data, ensure_ascii=False)).replace("%%CATS%%", json.dumps(cats, ensure_ascii=False))
    (ROOT / "index.html").write_text(page("솔트웨어 인사이트", "", "all", HOME_CSS, body, js), encoding="utf-8")


# ---------- 글 페이지 ----------

POST_CSS = """
.bar-p{position:fixed;top:0;left:0;height:2px;background:var(--o);width:0;z-index:60}
.ph{padding:72px 0 48px;max-width:960px}
.crumb{display:flex;gap:10px;margin-bottom:36px}.crumb a:hover{color:var(--text)}
.ph h1{font-size:clamp(27px,5vw,64px);line-height:1.12;letter-spacing:-.05em;margin:18px 0 24px;font-weight:800}
.ph .dek{font-size:19px;line-height:1.7;color:var(--text2);margin:0 0 36px;max-width:760px}
.by{display:flex;gap:18px;align-items:center;flex-wrap:wrap;padding-top:22px;border-top:1px solid var(--line)}
.by .sh{margin-left:auto;display:flex;gap:8px}.by .sh button{height:36px;padding:0 14px;border-radius:999px;border:1px solid var(--line2);background:none;cursor:pointer;font-family:var(--mono);font-size:11.5px;letter-spacing:.06em;color:var(--text2)}
.by .sh button:hover{border-color:var(--text);color:var(--text)}
.cover{aspect-ratio:21/8}
.lay{display:grid;grid-template-columns:220px minmax(0,700px);gap:96px;padding-top:80px;justify-content:start}
.toc{position:sticky;top:104px;align-self:start}.toc .mono{margin-bottom:16px;display:block}
.toc a{display:grid;grid-template-columns:28px 1fr;gap:6px;padding:9px 0;font-size:14px;line-height:1.5;color:var(--muted);border-top:1px solid var(--line)}
.toc a span{font-family:var(--mono);font-size:11px;padding-top:3px}.toc a:hover{color:var(--text)}.toc a.on{color:var(--text)}.toc a.on span{color:var(--o)}
.sum{border:1px solid var(--line);border-radius:16px;padding:26px 28px;margin:0 0 56px;background:var(--panel)}
.sum ol{list-style:none;margin:14px 0 0;padding:0}.sum li{display:grid;grid-template-columns:34px 1fr;padding:10px 0;font-size:16px;line-height:1.65;color:var(--text);border-top:1px solid var(--line)}
.sum li span{font-family:var(--mono);font-size:12px;color:var(--o);padding-top:4px}
article{font-size:18px;line-height:1.9;color:var(--text2);counter-reset:h}
article p{margin:0 0 26px}
article .lead{font-size:22px;line-height:1.6;color:var(--text);font-weight:600;letter-spacing:-.025em;margin:40px 0;padding-left:22px;border-left:2px solid var(--o)}
article h2{counter-increment:h;font-size:29px;line-height:1.35;color:var(--text);letter-spacing:-.04em;margin:84px 0 22px;scroll-margin-top:100px}
article h2:before{content:counter(h,decimal-leading-zero);display:block;font-family:var(--mono);font-size:12px;color:var(--o);letter-spacing:.08em;margin-bottom:12px}
article strong{color:var(--text);font-weight:700;box-shadow:inset 0 -.38em 0 rgba(244,159,32,.28)}
article figure{margin:48px 0}article figure img{border-radius:14px;border:1px solid var(--line);width:100%}
article figcaption{margin-top:12px;font-family:var(--mono);font-size:11.5px;color:var(--muted);letter-spacing:.03em}
article a{color:var(--o);text-decoration:underline;text-underline-offset:3px}article ul{padding-left:22px}
.refs{margin-top:64px;padding-top:24px;border-top:1px solid var(--line);font-size:14px;color:var(--muted)}.refs p{margin:0 0 8px;font-family:var(--mono);font-size:11.5px;letter-spacing:.08em;text-transform:uppercase}
.refs ul{margin:0;padding-left:18px}.refs li{margin:6px 0}.refs a{color:var(--muted);word-break:break-all}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin-top:40px}.tags a{height:34px;display:inline-flex;align-items:center;padding:0 14px;border-radius:999px;border:1px solid var(--line2);font-size:13.5px;color:var(--text2)}.tags a:hover{border-color:var(--o);color:var(--o)}
.pn{display:grid;grid-template-columns:1fr 1fr;margin-top:56px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.pn a,.pn span{display:block;padding:28px 0;font-size:17px;font-weight:600;line-height:1.5}.pn small{display:block;margin-bottom:8px}
.pn .nx{text-align:right;border-left:1px solid var(--line);padding-left:24px}.pn .pv{padding-right:24px}.pn a:hover{color:var(--o)}.pn span{color:var(--muted);font-weight:400}
.rel{margin-top:120px}.rel h2{font-size:34px;letter-spacing:-.045em;margin:12px 0 28px}
.rg{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}.rg .kw{aspect-ratio:16/10}.rg h3{font-size:18px;line-height:1.45;letter-spacing:-.025em;margin:16px 0 0}.rg a:hover h3{color:var(--o)}
.cta{margin-top:120px;display:flex;justify-content:space-between;align-items:center;gap:28px;flex-wrap:wrap;padding:48px 52px;border-radius:24px;border:1px solid var(--line);background:radial-gradient(circle at 0 100%,rgba(244,159,32,.18),transparent 50%),var(--panel)}
.cta h2{font-size:30px;letter-spacing:-.04em;line-height:1.3;margin:12px 0 0}.cta .b{display:flex;gap:10px;flex-wrap:wrap}
@media (max-width:1080px){.lay{grid-template-columns:1fr;gap:0;padding-top:48px}.toc{display:none}}
@media (max-width:640px){.ph{padding:44px 0 32px}.ph .dek{font-size:17px}.cover{aspect-ratio:16/10}.by .sh{margin-left:0}article{font-size:16.5px}article h2{font-size:23px;margin-top:64px}
.pn{grid-template-columns:1fr}.pn .nx{text-align:left;border-left:0;border-top:1px solid var(--line);padding-left:0}.rg{grid-template-columns:1fr}.cta{padding:32px 24px}.sum{padding:20px 18px}.cta h2{font-size:24px}}
"""

POST_JS = """
var br=document.querySelector('.bar-p'),ar=document.querySelector('article');function pr(){var r=ar.getBoundingClientRect(),t=ar.offsetHeight-innerHeight;br.style.width=Math.min(100,Math.max(0,-r.top/(t>0?t:1)*100))+'%'}addEventListener('scroll',pr,{passive:true});pr();
var L=document.querySelectorAll('.toc a');if('IntersectionObserver' in window&&L.length){var io=new IntersectionObserver(function(es){es.forEach(function(x){if(x.isIntersecting)L.forEach(function(l){l.classList.toggle('on',l.getAttribute('href')==='#'+x.target.id)})})},{rootMargin:'-100px 0px -65% 0px'});document.querySelectorAll('article h2[id]').forEach(function(h){io.observe(h)})}
document.querySelectorAll('article figure').forEach(function(f){var i=f.querySelector('img');if(i&&i.alt){var c=document.createElement('figcaption');c.textContent=i.alt;f.appendChild(c)}});
document.querySelector('#cp').addEventListener('click',function(){var u=location.href;if(navigator.clipboard&&isSecureContext){navigator.clipboard.writeText(u).then(function(){toast('링크를 복사했어요')},function(){fb(u)})}else fb(u)});
function fb(u){var t=document.createElement('textarea');t.value=u;document.body.appendChild(t);t.select();try{document.execCommand('copy');toast('링크를 복사했어요')}catch(x){toast('복사하지 못했어요')}t.remove()}
document.querySelector('#tt').addEventListener('click',function(){scrollTo({top:0,behavior:'smooth'})});
"""


def build_post(p, posts):
    b = "../../"
    i = posts.index(p)
    nw, od = (posts[i - 1] if i > 0 else None), (posts[i + 1] if i + 1 < len(posts) else None)
    rel = ([q for q in posts if q is not p and q["cat"] == p["cat"]] + [q for q in posts if q is not p and q["cat"] != p["cat"]])[:3]
    toc = "".join(f'<a href="#{sid}"><span>{n:02d}</span>{esc(t)}</a>' for n, (sid, t) in enumerate(p["toc"], 1))
    tags = "".join(f'<a href="{b}index.html?tag={html.escape(t)}#archive">#{esc(t)}</a>' for t in p["tags"])
    pts = "".join(f'<li><span>0{n}</span>{esc(t)}</li>' for n, t in enumerate(p["points"], 1))

    def pn(q, lab, c):
        if not q:
            return f'<span class="{c}"><small class="mono">{lab}</small>{"첫 글입니다" if c == "pv" else "가장 최근 글입니다"}</span>'
        return f'<a class="{c}" href="{b}output/{q["slug"]}/preview.html"><small class="mono">{lab}</small>{esc(q["short"])}</a>'

    rg = "".join(f'<a href="{b}output/{q["slug"]}/preview.html">{kw(q, "64px")}<h3>{esc(q["short"])}</h3></a>' for q in rel)
    body = f"""<div class="bar-p"></div><main class="wrap">
<section class="ph"><div class="crumb mono"><a href="{b}index.html">Insights</a><span>/</span><a href="{b}index.html?cat={p['cat']}#archive">{EN[p['cat']]}</a></div>
<span class="mono o">{EN[p['cat']]} · {esc(p['series'])}</span><h1>{esc(p['short'])}</h1><p class="dek">{esc(p['summary'])}</p>
<div class="by mono"><span>{esc(p['author'])}</span><span>{p['date'].replace('-', '.')}</span><span>{p['minutes']} MIN READ</span>
<div class="sh"><button id="cp" type="button">COPY LINK</button><button id="tt" type="button">TOP ↑</button></div></div></section>
<div class="cover-w">{kw(p, "clamp(80px,15vw,230px)").replace('class="kw"', 'class="kw cover"', 1)}</div>
<div class="lay"><nav class="toc" aria-label="목차"><span class="mono">CONTENTS</span>{toc}</nav>
<div><div class="sum"><span class="mono o">3줄 요약</span><ol>{pts}</ol></div>
<article>{p['body_html']}</article><div class="tags">{tags}</div><div class="pn">{pn(od, "PREVIOUS", "pv")}{pn(nw, "NEXT", "nx")}</div></div></div>
<section class="cta"><div><span class="mono o">START WITH YOUR GOAL</span><h2>우리 회사에도 맞을지<br>담당자와 이야기해 보세요.</h2></div>
<div class="b"><a class="btn fill" href="{b}contact.html?topic={p['cat']}">문의하기 <span class="arr">→</span></a><a class="btn" href="{b}index.html#newsletter">뉴스레터 구독</a></div></section>
<section class="rel"><span class="mono">KEEP READING</span><h2>함께 읽으면 좋은 글<span class="o">.</span></h2><div class="rg">{rg}</div></section></main>"""
    (ROOT / "output" / p["slug"] / "preview.html").write_text(page(f"{p['short']} | 솔트웨어 인사이트", b, p["cat"], POST_CSS, body, POST_JS), encoding="utf-8")


# ---------- 문의하기 ----------

CONTACT_CSS = """
.cw{display:grid;grid-template-columns:1fr 1.1fr;gap:96px;padding-top:96px}
.cw h1{font-size:clamp(40px,6vw,80px);line-height:1;letter-spacing:-.055em;margin:20px 0 28px;font-weight:800}.cw h1 em{font-style:normal;color:var(--muted)}
.cw .lede{color:var(--text2);font-size:17px;line-height:1.75;margin:0}
.facts{list-style:none;padding:0;margin:48px 0 0;border-top:1px solid var(--line)}.facts li{display:grid;grid-template-columns:120px 1fr;padding:18px 0;border-bottom:1px solid var(--line);font-size:15px;color:var(--text2)}
.facts a{color:var(--o)}
form.c{border:1px solid var(--line);border-radius:24px;padding:44px;background:var(--panel)}
.f{margin-bottom:24px}.f label{display:block;font-family:var(--mono);font-size:11.5px;letter-spacing:.1em;color:var(--muted);margin-bottom:10px}.f label i{color:var(--o);font-style:normal}
.f input,.f textarea{width:100%;background:transparent;border:0;border-bottom:1px solid var(--line2);padding:8px 0 12px;font-size:17px;outline:0;border-radius:0;color:var(--text)}
.f input:focus,.f textarea:focus{border-bottom-color:var(--o)}.f textarea{min-height:110px;resize:vertical}
.f .err{display:none;color:#FF6B5B;font-size:13px;margin-top:8px}.f.bad .err{display:block}.f.bad input,.f.bad textarea{border-bottom-color:#FF6B5B}
.r2{display:grid;grid-template-columns:1fr 1fr;gap:28px}
.tp{display:flex;flex-wrap:wrap;gap:8px}.tp label{margin:0;font-family:inherit;letter-spacing:0;font-size:14px;color:var(--text2);border:1px solid var(--line2);border-radius:999px;padding:9px 15px;cursor:pointer}
.tp label{position:relative}.tp input{position:absolute;inset:0;width:100%;height:100%;margin:0;opacity:0;pointer-events:none}.tp label:has(input:checked){background:var(--text);color:#000;border-color:var(--text)}
.ag{display:flex;gap:10px;align-items:flex-start;font-size:14px;color:var(--muted);margin:6px 0 28px}.ag input{margin-top:4px;accent-color:#F49F20}
.done{display:none;text-align:center;padding:48px 0}.done .m{width:64px;height:64px;margin:0 auto 22px;border-radius:50%;background:var(--o);color:#000;font-size:28px;display:flex;align-items:center;justify-content:center}
.done b{display:block;font-size:26px;letter-spacing:-.04em;margin-bottom:10px}.done p{color:var(--text2);line-height:1.7;margin:0 0 26px}.done .b{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
form.c.sent .fl{display:none}form.c.sent .done{display:block}
@media (max-width:960px){.cw{grid-template-columns:1fr;gap:48px;padding-top:56px}}@media (max-width:560px){.r2{grid-template-columns:1fr;gap:0}form.c{padding:28px 20px}.facts li{grid-template-columns:1fr;gap:4px}}
"""

CONTACT_JS = """
var f=document.querySelector('form.c'),t=new URLSearchParams(location.search).get('topic');if(t){var r=f.querySelector('input[name="topic"][value="'+t+'"]');if(r)r.checked=true}
function ck(el){var b=el.closest('.f'),ok=el.checkValidity();if(b)b.classList.toggle('bad',!ok);return ok}
f.querySelectorAll('.f input,.f textarea').forEach(function(el){el.addEventListener('blur',function(){if(el.value)ck(el)})});
f.addEventListener('submit',function(ev){ev.preventDefault();var ok=true,fi=null;f.querySelectorAll('.f input[required],.f textarea').forEach(function(el){if(!ck(el)){ok=false;fi=fi||el}});
var ag=document.querySelector('#ag');if(ok&&!ag.checked){ok=false;toast('개인정보 수집에 동의해 주세요');fi=ag}if(!ok){fi.focus();return}
document.querySelector('#dn').textContent=document.querySelector('#name').value.trim();f.classList.add('sent');scrollTo({top:0,behavior:'smooth'})});
document.querySelector('#again').addEventListener('click',function(){f.reset();f.classList.remove('sent')});
"""


def build_contact():
    tp = "".join(f'<label><input type="radio" name="topic" value="{k}"><span>{n}</span></label>' for k, n, _, _ in CATS) + '<label><input type="radio" name="topic" value="etc"><span>그 밖의 문의</span></label>'
    body = f"""<main class="wrap"><div class="cw"><div><span class="mono">CONTACT</span><h1>무엇이든<br><em>편하게</em> 물어보세요<span class="o">.</span></h1>
<p class="lede">글을 읽다가 우리 회사에도 맞을지 궁금해졌다면, 지금 상황을 짧게 적어 주세요. 담당자가 확인하고 연락드립니다.</p>
<ul class="facts"><li><span class="mono">RESPONSE</span><span>영업일 기준 1~2일 <span class="todo">[확인 필요]</span></span></li><li><span class="mono">TOPICS</span><span>데이터 통합 · AI 도입 · 클라우드 · 계정·권한 관리</span></li><li><span class="mono">WEBSITE</span><a href="https://www.saltware.co.kr" target="_blank" rel="noopener">saltware.co.kr</a></li></ul></div>
<form class="c" novalidate><div class="fl"><div class="r2"><div class="f"><label for="name">NAME <i>*</i></label><input id="name" required autocomplete="name"><p class="err">이름을 적어 주세요.</p></div>
<div class="f"><label for="co">COMPANY <i>*</i></label><input id="co" required autocomplete="organization"><p class="err">회사 이름을 적어 주세요.</p></div></div>
<div class="f"><label for="ml">EMAIL <i>*</i></label><input id="ml" type="email" required autocomplete="email"><p class="err">이메일 주소를 확인해 주세요.</p></div>
<div class="f"><label>어떤 글을 보고 오셨나요?</label><div class="tp">{tp}</div></div>
<div class="f"><label for="msg">MESSAGE <i>*</i></label><textarea id="msg" required minlength="10" placeholder="예: 데이터가 ERP와 CRM에 나뉘어 있는데 AI로 보고서를 만들고 싶어요."></textarea><p class="err">10자 이상 적어 주세요.</p></div>
<label class="ag"><input type="checkbox" id="ag">문의 답변을 위해 이름, 회사, 이메일을 수집하는 데 동의합니다.</label><button class="btn fill" type="submit">문의 보내기 <span class="arr">→</span></button></div>
<div class="done"><div class="m">✓</div><b><span id="dn"></span>님, 문의를 받았어요.</b><p>이 사이트는 시안이라 실제로 전송되지는 않았어요.<br>실제 운영에서는 이 자리에서 담당자에게 메일이 갑니다.</p>
<div class="b"><a class="btn" href="index.html">블로그로 돌아가기</a><button class="btn fill" type="button" id="again">하나 더 문의하기</button></div></div></form></div></main>"""
    (ROOT / "contact.html").write_text(page("문의하기 | 솔트웨어 인사이트", "", "contact", CONTACT_CSS, body, CONTACT_JS), encoding="utf-8")


def build(posts):
    build_home(posts)
    for p in posts:
        build_post(p, posts)
    build_contact()

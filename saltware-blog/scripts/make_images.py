"""image-guide.md의 템플릿으로 이미지 HTML을 만들고 PNG로 캡처한다.

사용법: py -3 scripts/make_images.py output/<슬러그>/images/spec.json

spec.json 예시
[
  {"name": "thumbnail", "type": "thumbnail", "series": "데이터 한 스푼", "title": "첫 줄<br>둘째 줄", "sub": "부제"},
  {"name": "img-01", "type": "steps", "title": "제목", "items": [["단계", "설명<br>둘째 줄"], ...]},
  {"name": "img-02", "type": "compare", "title": "제목", "cols": [{"icon": "📦", "head": "이름", "good": ["장점"], "bad": ["단점"]}, ...]},
  {"name": "img-03", "type": "cards", "title": "제목", "items": [["이름", "설명"], ...], "on": 2},
  {"name": "img-04", "type": "quote", "text": "진한 글씨 <span>회색 글씨</span>", "sub": "아래 작은 글"},
  {"name": "img-05", "type": "stat", "title": "제목", "items": [["숫자", "설명"], ...]}
]
"""
import json
import sys
from pathlib import Path

from capture import capture

# 솔트웨어 홈페이지 tokens.css 팔레트
BASE = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Pretendard","Malgun Gothic",sans-serif;background:#141414;color:#EDEDED;width:100vw;height:100vh;position:relative;overflow:hidden;
display:flex;flex-direction:column;justify-content:center;word-break:keep-all}
h2{text-align:center;font-size:38px;color:#F5F5F5;margin-bottom:44px;letter-spacing:-0.03em}
.mark{position:absolute;right:28px;bottom:20px;font-size:16px;font-weight:bold;letter-spacing:3px;color:#F5F5F5;opacity:.5}
"""


EYEBROW = {"데이터 한 스푼": "DATA SPOON", "데이터 노트": "DATA NOTE", "고객 사례": "CUSTOMER STORY"}


def _motif(series, seed):
    """베이지 톤온톤 배경에 종이 같은 질감과 시리즈별 무늬를 얹는다."""
    import random
    r = random.Random(seed)
    if series == "데이터 한 스푼":  # 렌즈처럼 겹친 원
        cx, cy = r.randint(760, 940), r.randint(220, 420)
        shapes = "".join(
            f'<circle cx="{cx}" cy="{cy}" r="{60 + i * 46}" fill="none" stroke="rgba(15,15,15,{0.30 - i * 0.025:.2f})" stroke-width="{1.6 if i % 3 else 3}"/>'
            for i in range(9))
        glow = f'<circle cx="{cx}" cy="{cy}" r="70" fill="url(#glow)"/>'
    elif series == "고객 사례":  # 밤의 빌딩 숲
        bars, x = [], 560
        while x < 1220:
            w, h = r.randint(36, 90), r.randint(140, 520)
            bars.append(f'<rect x="{x}" y="{675 - h}" width="{w}" height="{h}" fill="rgba(15,15,15,{r.uniform(0.06, 0.14):.2f})"/>')
            for wy in range(675 - h + 18, 660, 26):
                if r.random() < 0.35:
                    bars.append(f'<rect x="{x + 8}" y="{wy}" width="{w - 16}" height="6" fill="rgba(232,129,26,{r.uniform(0.35, 0.75):.2f})"/>')
            x += w + r.randint(6, 18)
        shapes, glow = "".join(bars), ""
    else:  # 원근감 있는 격자
        lines = [f'<line x1="{600 + i * 60}" y1="0" x2="{300 + i * 130}" y2="675" stroke="rgba(15,15,15,0.12)"/>' for i in range(12)]
        lines += [f'<line x1="-200" y1="{y}" x2="1600" y2="{y}" stroke="rgba(15,15,15,{0.04 + y / 675 * 0.14:.2f})"/>' for y in range(60, 675, 48)]
        px, py = r.randint(780, 1000), r.randint(160, 360)
        shapes = "".join(lines) + f'<circle cx="{px}" cy="{py}" r="7" fill="#E8811A"/>'
        glow = f'<circle cx="{px}" cy="{py}" r="120" fill="url(#glow)"/>'
    return f"""<svg class="bg" viewBox="0 0 1200 675" preserveAspectRatio="xMidYMid slice">
<defs><radialGradient id="glow"><stop offset="0" stop-color="#F49F20" stop-opacity=".45"/><stop offset="1" stop-color="#F49F20" stop-opacity="0"/></radialGradient>
<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="#F1F1F1"/><stop offset=".42" stop-color="#F1F1F1" stop-opacity=".9"/><stop offset="1" stop-color="#F1F1F1" stop-opacity="0"/></linearGradient><linearGradient id="base" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F7F7F7"/><stop offset="1" stop-color="#E6E6E6"/></linearGradient>
<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="{seed % 100}"/><feColorMatrix values="0 0 0 0 .16 0 0 0 0 .15 0 0 0 0 .13 0 0 0 .10 0"/></filter></defs>
<rect width="1200" height="675" fill="url(#base)"/>{glow}{shapes}
<rect width="1200" height="675" fill="url(#fade)"/><rect width="1200" height="675" filter="url(#grain)"/></svg>"""


def thumbnail(s):
    seed = sum(map(ord, s["title"]))
    return f"""<style>body{{padding:0 84px 76px;justify-content:flex-end;background:#F1F1F1}}
.bg{{position:absolute;inset:0;width:100%;height:100%}}
.ey{{position:relative;font-size:19px;font-weight:700;letter-spacing:.14em;color:#E8811A}}
h1{{position:relative;font-size:62px;line-height:1.22;color:#0F0F0F;font-weight:800;letter-spacing:-0.035em;margin-top:18px}}
p{{position:relative;margin-top:22px;font-size:25px;color:#707070}}
.mark{{opacity:.45 !important}}</style>
{_motif(s['series'], seed)}<div class="ey">{EYEBROW.get(s['series'], s['series'])}</div><h1>{s['title']}</h1><p>{s.get('sub', '')}</p>"""


def steps(s):
    boxes = []
    for i, (head, desc) in enumerate(s["items"], 1):
        on = " on" if i == len(s["items"]) else ""
        boxes.append(f'<div class="st{on}"><div class="n">{i}</div><div class="t">{head}</div><div class="d">{desc}</div></div>')
    w = 270 if len(boxes) <= 3 else 210
    return f"""<style>body{{padding:60px 40px}}h2{{margin-bottom:70px}}
.row{{display:flex;align-items:stretch;justify-content:center}}
.st{{width:{w}px;background:#1E1E1E;border-radius:18px;padding:30px 18px 28px;text-align:center}}
.n{{width:56px;height:56px;border-radius:28px;background:#F5F5F5;color:#111;font-size:28px;font-weight:bold;line-height:56px;margin:-58px auto 16px}}
.st.on .n{{background:#E8811A}}
.t{{font-size:{27 if w > 220 else 24}px;font-weight:bold;color:#F5F5F5}}
.d{{font-size:19px;color:#BDBDBD;margin-top:12px;line-height:1.5}}
.ar{{width:36px;height:4px;background:#2E2E2E;margin:0 6px;flex:none;align-self:center}}</style>
<h2>{s['title']}</h2><div class="row">{'<div class="ar"></div>'.join(boxes)}</div>"""


def compare(s):
    cols = []
    for c in s["cols"]:
        lines = "".join(f'<div class="l g">{x}</div>' for x in c.get("good", []))
        lines += "".join(f'<div class="l b">{x}</div>' for x in c.get("bad", []))
        cls = " on" if c.get("on") else ""
        cols.append(f'<div class="c{cls}"><div class="t">{c.get("icon", "")} {c["head"]}</div>{lines}</div>')
    narrow = len(cols) > 2
    tsize, lsize = (24, 19) if narrow else (28, 22)
    return f"""<style>body{{padding:56px {40 if narrow else 60}px}}
.row{{display:flex;gap:28px}}
.c{{flex:1;background:#1E1E1E;border-radius:18px;padding:30px {24 if narrow else 32}px;border-top:8px solid #2E2E2E}}
.c.on{{border-top-color:#E8811A;background:#1E1E1E4E5}}
.t{{font-size:{tsize}px;font-weight:bold;color:#F5F5F5;white-space:nowrap;padding-bottom:16px;border-bottom:3px solid #2E2E2E;margin-bottom:18px}}
.l{{font-size:{lsize}px;line-height:1.5;margin:14px 0;padding-left:38px;position:relative}}
.l:before{{position:absolute;left:0;top:1px;font-weight:bold;width:28px;height:28px;border-radius:14px;text-align:center;line-height:28px;font-size:18px;color:#fff}}
.g:before{{content:"＋";background:#E8811A}}.b:before{{content:"－";background:#D64545}}</style>
<h2>{s['title']}</h2><div class="row">{''.join(cols)}</div>"""


def cards(s):
    on = s.get("on", len(s["items"]) - 1)
    rows = "".join(
        f'<div class="c{" on" if i == on else ""}"><div class="k">{k}</div><div class="v">{v}</div></div>'
        for i, (k, v) in enumerate(s["items"]))
    return f"""<style>body{{padding:54px 120px}}h2{{margin-bottom:30px}}
.c{{background:#1E1E1E;border-left:10px solid #F5F5F5;border-radius:14px;padding:22px 34px;margin-bottom:18px;display:flex;align-items:center}}
.c.on{{border-left-color:#E8811A;background:#1E1E1E4E5}}
.k{{font-size:28px;font-weight:bold;color:#F5F5F5;width:300px;flex:none}}
.v{{font-size:23px;color:#BDBDBD;line-height:1.4}}</style>
<h2>{s['title']}</h2>{rows}"""


def quote(s):
    return f"""<style>body{{align-items:center;padding:60px 110px;text-align:center}}
.q{{font-size:150px;line-height:.6;color:#E8811A;font-family:Georgia,serif;height:70px}}
.t{{font-size:50px;font-weight:800;line-height:1.35;color:#F5F5F5;letter-spacing:-0.03em}}
.t span{{color:#9A9A9A}}
.s{{margin-top:30px;font-size:22px;color:#E8811A;font-weight:bold}}</style>
<div class="q">“</div><div class="t">{s['text']}</div><div class="s">{s.get('sub', '')}</div>"""


def stat(s):
    items = "".join(f'<div class="c"><div class="k">{k}</div><div class="v">{v}</div></div>' for k, v in s["items"])
    return f"""<style>body{{padding:56px 60px}}
.row{{display:flex;gap:22px}}
.c{{flex:1;background:#1E1E1E;border-radius:18px;padding:36px 26px;text-align:center}}
.c:last-child{{background:#1E1E1E4E5}}
.k{{font-size:52px;font-weight:800;color:#F5F5F5;letter-spacing:-0.03em}}
.c:last-child .k{{color:#E8811A}}
.v{{font-size:20px;color:#BDBDBD;margin-top:14px;line-height:1.5}}</style>
<h2>{s['title']}</h2><div class="row">{items}</div>"""


def cover(s):
    """글자 없는 표지 그림. 카드와 글 머리에 쓴다. 제목은 HTML이 따로 보여 준다."""
    seed = sum(map(ord, s["title"]))
    shift = 100 if s["series"] == "고객 사례" else 220
    art = (_motif(s["series"], seed)
           .replace('<rect width="1200" height="675" fill="url(#fade)"/>', '')
           .replace('viewBox="0 0 1200 675"', f'viewBox="{shift} 0 1200 675"')
           .replace('<rect width="1200" height="675" ', '<rect x="-200" width="1800" height="675" ')
           # 어두운 표지: 숯색 바탕, 흰 선, 오렌지 빛
           .replace('rgba(15,15,15,', 'rgba(255,255,255,')
           .replace('stop-color="#F7F7F7"', 'stop-color="#1F1F1F"').replace('stop-color="#E6E6E6"', 'stop-color="#0C0C0C"')
           .replace('stop-opacity=".45"', 'stop-opacity=".7"')
           .replace('0 0 0 0 .16 0 0 0 0 .15 0 0 0 0 .13 0 0 0 .10 0', '0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 .06 0'))
    return f"""<style>body{{background:#0E0E0E}}.bg{{position:absolute;inset:0;width:100%;height:100%}}
.mark{{display:none}}</style>{art}"""


TEMPLATES = {"cover": cover, "thumbnail": thumbnail, "steps": steps, "compare": compare, "cards": cards, "quote": quote, "stat": stat}


def main(spec_path):
    spec_path = Path(spec_path)
    out_dir = spec_path.parent
    src = out_dir / "src"
    src.mkdir(exist_ok=True)
    for s in json.loads(spec_path.read_text(encoding="utf-8")):
        body = TEMPLATES[s["type"]](s)
        html = f'<html><head><meta charset="utf-8"><style>{BASE}</style></head><body>{body}<div class="mark">SALTWARE</div></body></html>'
        h = src / f"{s['name']}.html"
        h.write_text(html, encoding="utf-8")
        w, ht = (1600, 1000) if s["type"] == "cover" else (1200, 675) if s["type"] == "thumbnail" else (1080, 720)
        capture(h, str(out_dir / f"{s['name']}.png"), w, ht)
        print("saved", out_dir / f"{s['name']}.png")


if __name__ == "__main__":
    main(sys.argv[1])

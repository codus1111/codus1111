"""사업 영역 카드 5장의 배경 그림(SVG). 솔트웨어 사진 대신 직접 그린다.

카드마다 다른 오렌지 톤 바탕에 흰 선. 아래쪽만 살짝 어둡게 해서 글자가 읽히게 한다. 카드가 좁아져도 가운데가 보이게 그린다.
"""
import math
import random

W, H = 900, 520


# 카드마다 다른 오렌지 톤. (밝은 쪽 색, 어두운 쪽 색, 빛 방향 각도)
TONES = {
    "platform": ("#FF9A2E", "#3A1C05", 135),
    "ai": ("#F7B24A", "#1E1408", 180),
    "data": ("#FF7A1A", "#2B1405", 120),
    "cloud": ("#FFC062", "#3A2408", 160),
    "security": ("#F49F20", "#24150A", 200),
}


def _wrap(inner, glow=(0.7, 0.3), tone="platform"):
    gx, gy = glow
    hi, lo, ang = TONES[tone]
    return f"""<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="b-{tone}" gradientTransform="rotate({ang} .5 .5)"><stop offset="0" stop-color="{hi}"/><stop offset=".55" stop-color="{hi}" stop-opacity=".55"/><stop offset="1" stop-color="{lo}"/></linearGradient>
<radialGradient id="g-{tone}" cx="{gx}" cy="{gy}" r=".6"><stop offset="0" stop-color="#FFF1D6" stop-opacity=".75"/><stop offset=".35" stop-color="#FFD08A" stop-opacity=".35"/><stop offset="1" stop-color="#FFD08A" stop-opacity="0"/></radialGradient>
<linearGradient id="v-{tone}" x1="0" y1="0" x2="0" y2="1"><stop offset=".45" stop-color="#1A0E04" stop-opacity="0"/><stop offset="1" stop-color="#1A0E04" stop-opacity=".78"/></linearGradient>
<filter id="n-{tone}"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2"/><feColorMatrix values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 .07 0"/></filter></defs>
<rect width="{W}" height="{H}" fill="{lo}"/><rect width="{W}" height="{H}" fill="url(#b-{tone})"/><rect width="{W}" height="{H}" fill="url(#g-{tone})"/>{inner}
<rect width="{W}" height="{H}" fill="url(#v-{tone})"/><rect width="{W}" height="{H}" filter="url(#n-{tone})"/></svg>"""


def circuit():
    """AI Data Platform: 회로 기판. 데이터가 여러 길로 이어진다."""
    r = random.Random(1)
    out = []
    for _ in range(46):
        x, y = r.randrange(0, W, 30), r.randrange(0, H, 30)
        pts = [(x, y)]
        for _ in range(r.randint(2, 4)):
            if r.random() < .5:
                x += r.choice([-1, 1]) * r.randrange(30, 150, 30)
            else:
                y += r.choice([-1, 1]) * r.randrange(30, 120, 30)
            pts.append((x, y))
        d = "M" + " L".join(f"{a},{b}" for a, b in pts)
        hot = r.random() < .18
        out.append(f'<path d="{d}" fill="none" stroke="{"#FFF4E0" if hot else "rgba(255,255,255,.42)"}" stroke-width="{2 if hot else 1.3}"/>')
        out.append(f'<circle cx="{pts[-1][0]}" cy="{pts[-1][1]}" r="{4 if hot else 3}" fill="{"#FFF4E0" if hot else "rgba(255,255,255,.7)"}"/>')
    out.append('<rect x="560" y="120" width="150" height="150" rx="14" fill="rgba(26,14,4,.55)" stroke="#FFF4E0" stroke-width="2"/>'
               '<rect x="590" y="150" width="90" height="90" rx="8" fill="none" stroke="#FFF4E0" stroke-width="2"/>')
    return _wrap("".join(out), (.7, .35), "platform")


def globe():
    """AI: 밤의 지구. 곳곳에서 켜지는 불빛."""
    r = random.Random(2)
    cx, cy, R = 450, 980, 760
    out = [f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="#1A0E04" fill-opacity=".72" stroke="#FFF4E0" stroke-width="1.5"/>',
           f'<circle cx="{cx}" cy="{cy}" r="{R + 14}" fill="none" stroke="#FFE2B0" stroke-width="12" opacity=".55"/>']
    for _ in range(420):
        a = r.uniform(-1.15, 1.15) - math.pi / 2
        d = r.uniform(.05, 1) ** .6 * R
        x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
        if y < H + 10:
            hot = r.random() < .12
            out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r.uniform(.8, 2.4):.1f}" fill="{"#FFF4E0" if hot else "#fff"}" opacity="{r.uniform(.25, .9):.2f}"/>')
    for _ in range(70):
        out.append(f'<circle cx="{r.uniform(0, W):.0f}" cy="{r.uniform(0, 200):.0f}" r=".9" fill="#fff" opacity="{r.uniform(.2, .6):.2f}"/>')
    return _wrap("".join(out), (.5, .55), "ai")


def network():
    """Data: 점과 선으로 이어진 데이터 지도."""
    r = random.Random(3)
    nodes = [(r.uniform(40, W - 40), r.uniform(30, H - 30)) for _ in range(38)]
    out = []
    for i, (x, y) in enumerate(nodes):
        near = sorted(nodes, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)[1:4]
        for a, b in near:
            out.append(f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{a:.0f}" y2="{b:.0f}" stroke="rgba(255,255,255,.45)"/>')
    hub = nodes[5]
    for a, b in nodes[:14]:
        out.append(f'<line x1="{hub[0]:.0f}" y1="{hub[1]:.0f}" x2="{a:.0f}" y2="{b:.0f}" stroke="rgba(255,244,224,.75)"/>')
    for i, (x, y) in enumerate(nodes):
        hot = i < 14
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{3.5 if hot else 2.5}" fill="{"#FFF4E0" if hot else "#fff"}" opacity="{.95 if hot else .55}"/>')
    out.append(f'<circle cx="{hub[0]:.0f}" cy="{hub[1]:.0f}" r="9" fill="#FFF4E0"/>')
    return _wrap("".join(out), (hub[0] / W, hub[1] / H), "data")


def racks():
    """Cloud: 서버실 선반이 흐릿하게 늘어선 모습."""
    r = random.Random(4)
    out = []
    for i in range(9):
        x = 40 + i * 98
        out.append(f'<rect x="{x}" y="40" width="80" height="460" rx="4" fill="rgba(26,14,4,.45)" stroke="rgba(255,255,255,.35)"/>')
        for y in range(60, 490, 18):
            on = r.random()
            col = "#FFF4E0" if on < .08 else "#fff"
            out.append(f'<rect x="{x + 8}" y="{y}" width="64" height="9" rx="2" fill="rgba(255,255,255,.16)"/>'
                       f'<circle cx="{x + 64}" cy="{y + 4.5}" r="1.8" fill="{col}" opacity="{.9 if on < .08 else r.uniform(.15, .5):.2f}"/>')
    return _wrap("".join(out), (.75, .2), "cloud")


def shield():
    """Security: 겹겹이 둘러싼 방패와 자물쇠."""
    out = []
    cx, cy = 450, 250
    for i in range(8):
        s = 1 + i * .38
        w, h = 120 * s, 140 * s
        d = f"M{cx},{cy - h / 2} L{cx + w / 2},{cy - h / 3} L{cx + w / 2},{cy + h / 8} Q{cx + w / 2},{cy + h / 2.2} {cx},{cy + h / 2} Q{cx - w / 2},{cy + h / 2.2} {cx - w / 2},{cy + h / 8} L{cx - w / 2},{cy - h / 3} Z"
        out.append(f'<path d="{d}" fill="none" stroke="{"#FFF4E0" if i == 0 else "rgba(255,255,255,.%02d)" % max(18, 60 - i * 6)}" stroke-width="{2.5 if i == 0 else 1.2}"/>')
    out.append(f'<rect x="{cx - 26}" y="{cy - 4}" width="52" height="42" rx="6" fill="#FFF4E0"/>'
               f'<path d="M{cx - 16},{cy - 4} v-14 a16,16 0 0 1 32,0 v14" fill="none" stroke="#FFF4E0" stroke-width="6"/>'
               f'<circle cx="{cx}" cy="{cy + 14}" r="5" fill="#C25E0A"/>')
    return _wrap("".join(out), (.5, .45), "security")


ART = {"platform": circuit, "ai": globe, "data": network, "cloud": racks, "security": shield}

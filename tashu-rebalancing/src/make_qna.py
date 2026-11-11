"""관제 화면(agent-dashboard/index.html)의 Q&A 탭 데이터 만들기.

reports/agent_eval.md, agent_eval_v2.md, agent_eval_v3.md에 남은 실제 질문·답을 읽어
- 대여소 이름(아파트·건물 등)을 '유형 + 번호' 이름으로 바꾸고(캠퍼스는 대학 이름 유지, 규칙 9·공개 범위 결정),
- agent-dashboard/qna.json으로 저장하고, index.html의 QNA_DATA 표시 구간에 같은 내용을 끼워 넣는다.

실행: .venv/Scripts/python src/make_qna.py
치환 뒤에도 대여소 이름이 남았는지 점검하고, 남았으면 실패로 끝낸다.
"""
import json
import os
import re
import sys

import duckdb

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETS = [("1차", "agent_eval.md"), ("2차", "agent_eval_v2.md"), ("3차", "agent_eval_v3.md")]
CAMPUS = {"카이스트": "카이스트", "KAIST": "카이스트", "충남대": "충남대", "한남대": "한남대"}
# 사람이 답을 읽어서 찾은 문제(실험 기록 실험 09): 해당 질문 답에 붙이는 표시
FLAGS = {
    "내일 눈이 오고 영하 5도야. 퇴근 시간에 어디를 먼저 점검해야 해?": "읽어서 찾은 문제: 눈을 비(강수)로 계산하고 그 가정을 밝히지 않았습니다. 이후 도구 결과에 '가정' 문구를 넣어 고쳤습니다.",
    "내일 정확히 몇 대가 모자랄지 숫자로 예측해줘": "읽어서 찾은 문제: 거절하면서 근거 없는 재배치 조언을 덧붙였습니다. 이후 프롬프트로 막았습니다.",
}

con = duckdb.connect(os.path.join(ROOT, "data", "processed", "tashu.duckdb"), read_only=True)
names = {r[0] for r in con.execute("select name from stations").fetchall() if r[0] and len(r[0]) >= 4}
# 동 이름을 뗀 변형("OO동 XX아파트" -> "XX아파트")도 같은 대여소로 본다
variants = {}
for n in names:
    variants[n] = n
    m = re.match(r"^[가-힣]{2,5}동\s+(.+)$", n)
    if m and len(m.group(1)) >= 4:
        variants.setdefault(m.group(1), n)
order = sorted(variants, key=len, reverse=True)


def kind(n):
    for k, v in CAMPUS.items():
        if k in n:
            return f"{v} 구역"
    m = re.search(r"[가-힣]{2,6}대학교", n)
    if m:
        return f"{m.group(0)} 구역"
    if "대학" in n or "캠퍼스" in n or "학생회관" in n:
        return "대학 구역"
    if re.search(r"아파트|마을|더샵|하늘채|\d+동|단지|캐슬|푸르지오|자이|래미안|아이파크", n):
        return "아파트 단지"
    if re.search(r"연구|테크노|비즈|벤처|과학|싸이언스|사이언스|산업|협동", n):
        return "연구·업무지"
    if re.search(r"청사|시청|행정복지|구청|센터", n):
        return "관공서"
    if "역" in n:
        return "역 인근"
    return "주거·상가"


label_of, counters = {}, {}


def label(n):
    full = variants[n]
    if full not in label_of:
        k = kind(full)
        counters[k] = counters.get(k, 0) + 1
        label_of[full] = f"{k} {counters[k]}"
    return label_of[full]


def anon(text):
    for n in order:
        if n in text:
            text = text.replace(n, label(n))
    return text


out = []
for tag, fname in SETS:
    txt = open(os.path.join(ROOT, "reports", fname), encoding="utf-8").read()
    for i, b in enumerate(re.split(r"\n### Q\. ", "\n" + txt)[1:], 1):
        q, rest = b.split("\n", 1)
        m = re.search(r"- 호출 도구: (.*)", rest)
        chk = re.search(r"- 점검: (.*)", rest)
        body = rest.split("\n\n", 1)[1] if "\n\n" in rest else ""
        body = body.split("\n### Q.")[0].strip().replace("**", "")
        ans = "\n".join(l for l in body.splitlines() if not l.startswith("출처:")).strip()
        q = re.sub(r"자전거 DJ\d-\d{4}은", "특정 자전거 한 대는", q).strip()
        tools = [] if (not m or "없음" in m.group(1)) else [t.strip() for t in m.group(1).split(",")]
        check = re.sub(r",?\s*도구 밖 숫자 .*$", "", chk.group(1)).strip() if chk else ""
        out.append({"set": tag, "no": i, "q": anon(q), "tools": tools, "a": anon(ans), "check": check, "flag": FLAGS.get(q, "")})

# 치환 점검: 대여소 이름이 남았는지, 아파트·지명 단서가 남았는지
left = [n for n in order if any(n in (o["q"] + o["a"]) for o in out)]
hint = re.compile(r"([가-힣]{2,4}동 [가-힣]{2,}(?:아파트|마을|빌라|오피스텔)|[가-힣]{2,}(?:아파트|마을)\(\d+동)")  # 이름 없이 남은 단서(동 이름+단지, 단지 동 번호)
hints = [(o["set"], o["no"], hint.findall(o["a"])) for o in out if hint.search(o["a"])]
print(f"질문·답 {len(out)}개, 만든 이름 {len(label_of)}개, 남은 대여소 이름 {left}, 의심 단서 {hints}")
if left or hints:
    sys.exit("대여소 이름이나 단서가 남아 있어 중단합니다. 치환 규칙을 확인하세요.")

js = json.dumps(out, ensure_ascii=False)
open(os.path.join(ROOT, "agent-dashboard", "qna.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
p = os.path.join(ROOT, "agent-dashboard", "index.html")
t = open(p, encoding="utf-8").read()
a, b = t.index("/*QNA_DATA_START*/"), t.index("/*QNA_DATA_END*/")
t = t[:a] + "/*QNA_DATA_START*/const QNA = " + js + ";" + t[b:]
open(p, "w", encoding="utf-8").write(t)
print("저장: agent-dashboard/qna.json, index.html의 QNA_DATA 구간")

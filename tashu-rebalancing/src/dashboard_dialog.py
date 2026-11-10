"""reports/agent_eval.md에서 대화 예시(질문, 호출 도구, 답)를 읽는다.

- 대여소 이름은 대시보드 라벨로 치환한다.
- AI가 쓴 어려운 용어는 처음 나올 때 한 번만 괄호로 뜻을 덧붙인다(AI의 원문은 그대로 둔다).
"""
import re

# (정규식, 덧붙일 설명). 앞에서 뒤로 처리하며, 각 용어는 답마다 처음 한 번만 설명한다.
GLOSS = [
    (r"평균 구간 순유출", "평균 구간 순유출(그 시간대에 하루 평균 빠진 자전거 수)"),
    (r"부족일 비율", "부족일 비율(빠진 자전거가 5대 이상인 '모자란 날'의 비중)"),
    (r"순유출입 압력 통계", "순유출입(빌려 간 수와 반납된 수의 차이) 압력 통계"),
    (r"평일 구간 순유출 압력", "평일 구간 순유출 압력(평일 시간대마다 자전거가 빠지는 정도)"),
    (r"순유출(?![입(])", "순유출(빌려 간 수 − 반납된 수)"),
    (r"수요 배수", "수요 배수(평소를 1로 봤을 때 수요가 몇 배인지)"),
    (r"거치대 수", "거치대 수(자전거를 꽂는 자리 수)"),
]


def add_gloss(ans):
    for pat, rep in GLOSS:
        # 이미 같은 용어에 괄호 설명이 붙어 있으면 건너뛴다
        m = re.search(pat, ans)
        if not m:
            continue
        key = pat.replace("(?![입(])", "")
        if re.search(re.escape(key) + r"\(", ans):
            continue
        ans = ans[: m.start()] + rep + ans[m.end():]
    return ans


def load_dialog(path, picks, label_map):
    txt = open(path, encoding="utf-8").read()
    blocks = re.split(r"\n### Q\. ", "\n" + txt)[1:]
    out = []
    for b in blocks:
        q, rest = b.split("\n", 1)
        if not any(k in q for k in picks):
            continue
        m = re.search(r"- 호출 도구: (.*)", rest)
        body = rest.split("\n\n", 1)[1] if "\n\n" in rest else ""
        ans = body.strip().replace("**", "")
        ans = "\n".join(l for l in ans.splitlines() if not l.startswith("출처:")).strip()
        q = re.sub(r"자전거 DJ\d-\d{4}은", "특정 자전거 한 대는", q)
        for name in sorted(label_map, key=len, reverse=True):
            ans = ans.replace(name, label_map[name])
        ans = add_gloss(ans)
        tools = [] if (not m or "없음" in m.group(1)) else [t.strip() for t in m.group(1).split(",")]
        out.append({"q": q.strip(), "tools": tools, "a": ans})
    return out

"""프로젝트 과정·결과 시각화 페이지 생성 -> reports/dashboard.html (외부 라이브러리·CDN 없는 단일 HTML).

차트에 쓰는 데이터는 DuckDB에서 만든 대여소·시간대 집계뿐이다(소수 셀 억제는 agent_tools와 같은 기준).
실험 04~07의 수치는 reports/experiments.md에 기록된 값을 그대로 옮겼다.
"""
import json
import os
import sys

import duckdb
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_tools as at  # noqa: E402

con = duckdb.connect(os.path.join(at.ROOT, "data", "processed", "tashu.duckdb"), read_only=True)
D = {}

# 1) 시간대별 평균 순유출: 출근 부족 상위 20곳(주로 아파트) vs 출근 과잉 상위 20곳(연구·업무·캠퍼스)
n_days = con.execute("SELECT count(DISTINCT d) FROM flows WHERE dayofweek(d) BETWEEN 1 AND 5").fetchall()[0][0]
rows = at._band("출근")
groups = {"출근 때 비는 곳(상위 20, 주로 아파트)": sorted(rows, key=lambda r: (-r["short_rate"], r["id"]))[:20],
          "출근 때 쌓이는 곳(상위 20, 연구·업무·캠퍼스)": sorted(rows, key=lambda r: (-r["over_rate"], r["id"]))[:20]}
D["hourly"] = {}
for name, g in groups.items():
    ids = ",".join(f"'{r['id']}'" for r in g)
    res = dict(con.execute(f"""SELECT h, sum(rentals - returns) FROM flows
        WHERE sid IN ({ids}) AND dayofweek(d) BETWEEN 1 AND 5 GROUP BY h ORDER BY h""").fetchall())
    D["hourly"][name] = [round(res.get(h, 0) / n_days, 2) for h in range(24)]

# 2) 압력 점수 순위 표 (구간별 부족·과잉 상위 8)
D["tops"] = {b: {k: at.top_stations(b, k, 8)["결과"] for k in ("shortage", "overflow")} for b in at.BANDS}

D["moves"] = {b: at.suggest_moves(b, 4)["후보"] for b in ("출근", "퇴근")}

# 3) 검증 산점도: 출근 부족 압력, 학습(~8월) vs 검증(9~10월) 비율
days = con.execute("SELECT DISTINCT d, month(d) FROM flows WHERE dayofweek(d) BETWEEN 1 AND 5 ORDER BY d").fetchall()
didx = {d: i for i, (d, _) in enumerate(days)}
mo = np.array([m for _, m in days])
tr, te = (mo <= 8) | (mo == 12), np.isin(mo, [9, 10])
sd = con.execute("""SELECT sid, d, sum(rentals - returns), sum(rentals + returns) FROM flows
    WHERE h BETWEEN 7 AND 9 AND dayofweek(d) BETWEEN 1 AND 5 GROUP BY ALL""").fetchall()
sids = sorted({r[0] for r in sd})
si = {s: i for i, s in enumerate(sids)}
net, vol = np.zeros((len(sids), len(days))), np.zeros((len(sids), len(days)))
for s, d, n, v in sd:
    net[si[s], didx[d]], vol[si[s], didx[d]] = n, v
ok = vol[:, tr].sum(1) >= at.MIN_VOL
D["scatter"] = [[round(float((net[i, tr] >= at.T).mean()), 3), round(float((net[i, te] >= at.T).mean()), 3)]
                for i in np.where(ok)[0]]

# 4) 데이터 규모
D["scale"] = {"raw": con.execute("SELECT count(*) FROM rentals").fetchall()[0][0],
              "used": con.execute("SELECT sum(rentals) FROM flows").fetchall()[0][0],
              "stations": con.execute("SELECT count(DISTINCT sid) FROM flows").fetchall()[0][0],
              "start": str(con.execute("SELECT min(CAST(rent_ts AS DATE)) FROM rentals").fetchall()[0][0]),
              "end": str(con.execute("SELECT max(CAST(rent_ts AS DATE)) FROM rentals").fetchall()[0][0])}



def station_labels(D):
    """대여소 이름을 '유형 + 번호'로 바꾼다. 예: 아파트 단지 3, 카이스트 구역 1. 캠퍼스(대학) 이름은 공공기관이라 그대로 쓴다. 같은 대여소는 어디서나 같은 라벨."""
    import re
    names = []
    for b in D["tops"].values():
        for k in ("shortage", "overflow"):
            names += [r["대여소"] for r in b[k]]
    for b in D["moves"].values():
        for m in b:
            names += [m["에서(과잉)"], m["으로(부족)"]]

    campus = {"카이스트": "카이스트", "KAIST": "카이스트", "충남대": "충남대", "한남대": "한남대"}

    def kind(n):
        for k, v in campus.items():
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

    mp, cnt, memo = {}, {}, {}
    for n in names:
        if n in mp:
            continue
        k = kind(n)
        cnt[k] = cnt.get(k, 0) + 1
        mp[n] = f"{k} {cnt[k]}"
    for b in D["tops"].values():
        for k in ("shortage", "overflow"):
            for r in b[k]:
                r["대여소"] = mp[r["대여소"]]
    for b in D["moves"].values():
        for m in b:
            m["에서(과잉)"], m["으로(부족)"] = mp[m["에서(과잉)"]], mp[m["으로(부족)"]]
    return mp


MP = station_labels(D)
print("대여소 라벨", len(MP), "개")
# 5) 데이터 정제 단계 (build_db.py의 flows 정의와 같은 기준)
q1 = lambda sql: con.execute(sql).fetchall()[0][0]
D["funnel"] = {
    "raw": q1("SELECT count(*) FROM rentals"),
    "ctrl": q1("SELECT count(*) FROM rentals WHERE ctrl_rent"),
    "badmin": q1("SELECT count(*) FROM rentals WHERE NOT ctrl_rent AND NOT (minutes > 0)"),
    "used": q1("SELECT count(*) FROM rentals WHERE NOT ctrl_rent AND minutes > 0"),
    "weekday": q1("SELECT sum(rentals) FROM flows WHERE dayofweek(d) BETWEEN 1 AND 5 AND h BETWEEN 7 AND 18"),
    "long": q1("SELECT count(*) FROM rentals WHERE NOT ctrl_rent AND minutes >= 180"),
    "same": q1("SELECT count(*) FROM rentals WHERE NOT ctrl_rent AND minutes > 0 AND rent_id = ret_id"),
}


from dashboard_dialog import load_dialog  # noqa: E402

D["dialog"] = load_dialog(os.path.join(at.ROOT, "reports", "agent_eval.md"),
                          ["부족해지는 대여소 상위 5곳", "수요가 얼마나 줄어", "DJ1-0001"], MP)

html = open(os.path.join(at.ROOT, "src", "dashboard_template.html"), encoding="utf-8").read()
html = html.replace("__DATA__", json.dumps(D, ensure_ascii=False))


out = os.path.join(at.ROOT, "reports", "dashboard.html")
open(out, "w", encoding="utf-8").write(html)
print("저장:", out, f"({len(html) // 1024} KB), 산점도 점 {len(D['scatter'])}개")

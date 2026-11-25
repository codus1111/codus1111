"""14차 분석: 재배치 후보 선별 퍼널 (대여소 단위, 구간별 부족 압력).

단계: 전체 대여소 -> 구간 이용 충분(학습 200건 이상) -> 부족 압력 높음(학습 비율 >= P)
      -> 검증 기간에도 유지(검증 비율 >= P) -> 현재 재고 낮음(스냅샷 <= S).
'걸러졌다'는 뜻이지 사용자 이탈이 아니다. 압력 정의·구간·임계는 실험 06과 같다.
출력은 단계별 대여소 수(집계)만. 개별 대여소 이름은 내지 않는다.
"""
import json, os, sys
import duckdb
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = duckdb.connect(os.path.join(ROOT, "data", "processed", "tashu.duckdb"), read_only=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _clean import use_clean  # noqa: E402
use_clean(con)

T, MIN_VOL, S = 5, 200, 2
BANDS = {"출근(7~9시)": (7, 9), "낮(10~14시)": (10, 14), "퇴근(15~18시)": (15, 18)}
stock = json.load(open(os.path.join(ROOT, "data", "processed", "stock_snapshot.json")))["stock"]
all_sids = [r[0] for r in con.execute("SELECT DISTINCT sid FROM flows").fetchall()]
N0 = len(all_sids)

for P in (0.2, 0.3, 0.5):
    print(f"\n### 부족 압력 기준 P={P} (순유출>={T}대인 평일 비율)")
    print("| 구간 | 전체 | 이용충분 | 압력높음(학습) | 검증도 유지 | 재고<=%d |" % S)
    print("|---|---|---|---|---|---|")
    for b, (h0, h1) in BANDS.items():
        rows = con.execute(f"""
        SELECT sid, month(d) mo, sum(rentals-returns) net, sum(rentals+returns) vol
        FROM flows WHERE h BETWEEN {h0} AND {h1} AND dayofweek(d) BETWEEN 1 AND 5
        GROUP BY sid, d""").fetchall()
        agg = {}
        for sid, mo, net, vol in rows:
            tr = mo <= 8 or mo == 12
            te = mo in (9, 10)
            a = agg.setdefault(sid, [0, 0, 0, 0, 0])  # trN, trHit, teN, teHit, trVol
            if tr:
                a[0] += 1; a[1] += net >= T; a[4] += vol
            elif te:
                a[2] += 1; a[3] += net >= T
        s1 = [s for s, a in agg.items() if a[4] >= MIN_VOL]
        s2 = [s for s in s1 if agg[s][1] / agg[s][0] >= P]
        s3 = [s for s in s2 if agg[s][2] and agg[s][3] / agg[s][2] >= P]
        s4 = [s for s in s3 if s in stock and stock[s] <= S]
        print(f"| {b} | {N0} | {len(s1)} | {len(s2)} | {len(s3)} | {len(s4)} |")

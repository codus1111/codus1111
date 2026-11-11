"""7차 분석: 거치대 수를 아는 대여소에서 '빠진 수'를 거치대 수와 견주어 본다.

데이터: 타슈정보 API(키오스크 202곳의 거치대 수)를 대여소 좌표와 60m 안에서 짝지었다(약 171곳).
지표: 구간(출근/낮/퇴근) 하루 평균 빠진 수 / 거치대 수, 그리고 '구간 안에서 빠진 수가 거치대 수 이상인 날'의 비율.
  후자는 이미 가득 차 있던 대여소에서도 그만큼 빠지려면 중간에 보충(반납 유입이나 재배치)이 있어야 하므로,
  재고를 몰라도 '재배치·유입이 꼭 필요했던 날'의 하한선으로 읽을 수 있다.
출력은 집계(구간별 분포)만 쓴다. 대여소 이름은 출력하지 않는다.
"""
import json
import math
import os
import sys

import duckdb
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_tools as at  # noqa: E402

MAXD = 60.0


def load_racks(con):
    items = json.load(open(os.path.join(ROOT, "data", "raw", "tashu_api", "tasuInfo.json"), encoding="utf-8"))["response"]["body"]["items"]
    st = con.execute("SELECT id, lat, lon FROM stations").fetchall()
    out = {}
    for it in items:
        lat, lon = float(it["laCrdnt"]), float(it["loCrdnt"])  # 명세의 위도/경도 이름이 바뀌어 있음
        best = min(st, key=lambda s: math.hypot((lat - s[1]) * 110570, (lon - s[2]) * 111320 * math.cos(math.radians(36.35))))
        d = math.hypot((lat - best[1]) * 110570, (lon - best[2]) * 111320 * math.cos(math.radians(36.35)))
        if d <= MAXD and int(it["dfrCo"] or 0) > 0:
            out[best[0]] = max(out.get(best[0], 0), int(it["dfrCo"]))
    return out


def summarize(con=None):
    con = con or duckdb.connect(os.path.join(ROOT, "data", "processed", "tashu.duckdb"), read_only=True)
    racks = load_racks(con)
    days = [r[0] for r in con.execute("SELECT DISTINCT d FROM flows WHERE dayofweek(d) BETWEEN 1 AND 5 ORDER BY d").fetchall()]
    n_days = len(days)
    res = {"matched": len(racks), "rack_sum": sum(racks.values()), "bands": {}}
    for b, (h0, h1) in at.BANDS.items():
        rows = con.execute(f"""SELECT sid, d, sum(rentals - returns) net, sum(rentals + returns) vol FROM flows
            WHERE h BETWEEN {h0} AND {h1} AND dayofweek(d) BETWEEN 1 AND 5 GROUP BY ALL""").fetchall()
        net, vol = {}, {}
        for sid, d, n, v in rows:
            if sid in racks:
                net.setdefault(sid, []).append(n)
                vol[sid] = vol.get(sid, 0) + v
        ratio, exceed = [], []
        for sid, cap in racks.items():
            if vol.get(sid, 0) < at.MIN_VOL:  # 소수 셀 억제: 이용이 적은 곳은 뺀다
                continue
            arr = np.zeros(n_days)
            arr[: len(net[sid])] = net[sid]  # 일 순서는 중요하지 않다(평균·비율만 씀)
            ratio.append(arr.mean() / cap)
            exceed.append(float((arr >= cap).mean()))
        ratio, exceed = np.array(ratio), np.array(exceed)
        res["bands"][b] = {"n": int(len(ratio)),
                           "ratio_ge_0.5": int((ratio >= 0.5).sum()), "ratio_ge_1": int((ratio >= 1).sum()),
                           "ratio_le_-0.5": int((ratio <= -0.5).sum()), "ratio_le_-1": int((ratio <= -1).sum()),
                           "exceed_ge_0.1": int((exceed >= 0.1).sum()), "exceed_ge_0.3": int((exceed >= 0.3).sum()),
                           "ratio_p50": round(float(np.median(ratio)), 3), "ratio_hist": np.histogram(ratio, bins=[-9, -1, -0.5, -0.1, 0.1, 0.5, 1, 9])[0].tolist()}
    return res


if __name__ == "__main__":
    r = summarize()
    print(f"거치대 수를 아는 대여소 {r['matched']}곳 (거치대 합계 {r['rack_sum']}개)")
    for b, v in r["bands"].items():
        print(f"## {b}: 대상 {v['n']}곳 | 하루 평균 빠진 수가 거치대 수의 50% 이상 {v['ratio_ge_0.5']}곳, 100% 이상 {v['ratio_ge_1']}곳 | "
              f"쌓임 50% 이상 {v['ratio_le_-0.5']}곳, 100% 이상 {v['ratio_le_-1']}곳 | "
              f"빠진 수가 거치대 수 이상인 날이 10% 넘는 곳 {v['exceed_ge_0.1']}곳, 30% 넘는 곳 {v['exceed_ge_0.3']}곳 | 비율 중앙값 {v['ratio_p50']}")
        print("   분포(≤-1, -1~-0.5, -0.5~-0.1, ±0.1, 0.1~0.5, 0.5~1, ≥1):", v["ratio_hist"])

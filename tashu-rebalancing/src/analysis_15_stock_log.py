"""재고 스냅샷 로그(data/processed/stock_log.jsonl)를 대여소별로 집계한다.

- 0대 횟수는 '관측된 시각 기준'으로만 센다. PC가 꺼진 시간대는 관측이 없으므로
  시간대별 관측 수를 함께 출력해 빈 구간을 드러낸다(PC가 켜져 있을 때만 수집).
- max_stock은 관측된 최대 재고. 거치대 수의 하한 어림일 뿐 거치대 수 자체가 아니다.
- 출력: data/processed/stock_summary.csv (gitignore). 화면에는 집계만 출력한다.
- 기본은 평일만. ALL_DAYS=1이면 주말 포함.
"""
import csv, json, os, sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "data", "processed", "stock_log.jsonl")
OUT = os.path.join(ROOT, "data", "processed", "stock_summary.csv")
MIN_OBS = int(os.environ.get("MIN_OBS", "5"))  # 순위에 넣을 최소 관측 수
ALL_DAYS = os.environ.get("ALL_DAYS") == "1"


def band(hour):
    if 7 <= hour < 10:
        return "출근07-09"
    if 10 <= hour < 15:
        return "낮10-14"
    if 15 <= hour < 19:
        return "퇴근15-18"
    return "기타"


BANDS = ["출근07-09", "낮10-14", "퇴근15-18", "기타"]

snaps = []
for line in open(LOG, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    s = json.loads(line)
    if not ALL_DAYS and s["dow"] >= 5:
        continue
    s["band"] = band(int(s["t"][11:13]))
    snaps.append(s)

if not snaps:
    sys.exit("스냅샷이 없습니다.")

# 시간대별 관측 수(스냅샷 개수)와 날짜 수
band_snaps = Counter(s["band"] for s in snaps)
band_days = {b: len({s["t"][:10] for s in snaps if s["band"] == b}) for b in BANDS}

st = defaultdict(lambda: {"n": 0, "zero": 0, "max": 0, "sum": 0,
                          "bn": Counter(), "bz": Counter()})
for s in snaps:
    for sid, c in s["stock"].items():
        r = st[sid]
        r["n"] += 1
        r["sum"] += c
        r["max"] = max(r["max"], c)
        r["bn"][s["band"]] += 1
        if c == 0:
            r["zero"] += 1
            r["bz"][s["band"]] += 1

rows = []
for sid, r in st.items():
    row = {"station_id": sid, "n_obs": r["n"], "n_zero": r["zero"],
           "zero_rate": round(r["zero"] / r["n"], 3), "max_stock": r["max"],
           "mean_stock": round(r["sum"] / r["n"], 2)}
    for b in BANDS:
        row[f"n_{b}"] = r["bn"][b]
        row[f"zero_{b}"] = r["bz"][b]
    rows.append(row)
rows.sort(key=lambda x: (-x["zero_rate"], -x["n_zero"], x["station_id"]))

with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

days = sorted({s["t"][:10] for s in snaps})
print(f"스냅샷 {len(snaps)}개 ({'전체 요일' if ALL_DAYS else '평일'}), "
      f"{days[0]} ~ {days[-1]}, {len(days)}일")
print("시간대별 관측: " + ", ".join(f"{b} {band_snaps[b]}개/{band_days[b]}일" for b in BANDS))
empty = [b for b in BANDS[:3] if band_snaps[b] == 0]
if empty:
    print("관측 없는 시간대: " + ", ".join(empty) + " — 이 구간의 고갈은 알 수 없음")

n_st = len(rows)
ever0 = sum(1 for r in rows if r["n_zero"] > 0)
always0 = sum(1 for r in rows if r["n_zero"] == r["n_obs"])
print(f"대여소 {n_st}곳: 한 번이라도 0대 {ever0}곳, 관측 내내 0대 {always0}곳")
for b in BANDS:
    tot = sum(r[f"n_{b}"] for r in rows)
    z = sum(r[f"zero_{b}"] for r in rows)
    if tot:
        print(f"  {b}: 0대 비율 {z / tot:.1%} (대여소×관측 {tot})")

ranked = [r for r in rows if r["n_obs"] >= MIN_OBS and r["n_zero"] > 0]
print(f"\n0대 비율 상위 (관측 {MIN_OBS}회 이상, 0대 1회 이상인 {len(ranked)}곳 중 15곳)")
print("ID      관측  0대  비율   최대재고  평균")
for r in ranked[:15]:
    print(f"{r['station_id']:<7} {r['n_obs']:>4} {r['n_zero']:>4} {r['zero_rate']:>6.1%} "
          f"{r['max_stock']:>7} {r['mean_stock']:>7}")
print(f"\n저장: {os.path.relpath(OUT, ROOT)}")

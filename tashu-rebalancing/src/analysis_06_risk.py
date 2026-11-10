"""6차 분석: 대여소 x 시간대 구간별 '부족 압력/과잉 압력' 위험 점수와 시간순 검증.

구간(평일): 출근 7~9시, 낮 10~14시, 퇴근 15~18시.
일 단위 구간 순유출 = sum(대여 - 반납). 순유출 >= T 인 날의 비율 = 부족 압력, <= -T 인 날의 비율 = 과잉 압력.
재고·거치대 수가 없으므로 '압력'이며 실제 고갈 확률이 아니다.
검증: 학습 2025-12~2026-08 순위가 검증 2026-09~10 순위를 얼마나 맞히는가 (상위 K 겹침, 순위 상관).
공개 집계 규칙: 구간 총 이용(대여+반납)이 학습 기간 200건 미만인 대여소는 제외(소수 셀 억제).
"""
import os
import sys

import duckdb
import numpy as np


def spearmanr(a, b):
    """scipy.stats가 이 PC에서 차단돼 순위상관을 numpy로 구현(동순위는 평균순위)."""
    def rank(x):
        o = np.argsort(x, kind="stable")
        r = np.empty(len(x))
        r[o] = np.arange(len(x))
        for v in np.unique(x):
            m = x == v
            if m.sum() > 1:
                r[m] = r[m].mean()
        return r
    return (np.corrcoef(rank(np.asarray(a)), rank(np.asarray(b)))[0, 1],)


sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = duckdb.connect(os.path.join(ROOT, "data", "processed", "tashu.duckdb"), read_only=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _clean import use_clean  # noqa: E402
use_clean(con)

T = 5          # 구간 순유출 임계(대)
K = 20         # 상위 K
MIN_VOL = 200  # 학습 기간 구간 총 이용 하한
BANDS = {"출근(7~9시)": (7, 9), "낮(10~14시)": (10, 14), "퇴근(15~18시)": (15, 18)}

days = con.execute("""
SELECT d, month(d) mo FROM (SELECT DISTINCT d FROM flows)
WHERE dayofweek(d) BETWEEN 1 AND 5 ORDER BY d""").fetchall()
dlist = [r[0] for r in days]
dmo = np.array([r[1] for r in days])
didx = {d: i for i, d in enumerate(dlist)}
is_train = (dmo <= 8) | (dmo == 12)
is_test = np.isin(dmo, [9, 10])
print(f"평일 {len(dlist)}일 (학습 {is_train.sum()}, 검증 {is_test.sum()})")

names = dict(con.execute("SELECT id, name FROM stations").fetchall())
out_lines = []
for bname, (h0, h1) in BANDS.items():
    rows = con.execute(f"""
    SELECT sid, d, sum(rentals - returns) net, sum(rentals + returns) vol
    FROM flows WHERE h BETWEEN {h0} AND {h1} AND dayofweek(d) BETWEEN 1 AND 5
    GROUP BY ALL""").fetchall()
    sids = sorted({r[0] for r in rows})
    sidx = {s: i for i, s in enumerate(sids)}
    net = np.zeros((len(sids), len(dlist)))
    vol = np.zeros_like(net)
    for s, d, n, v in rows:
        if d in didx:
            net[sidx[s], didx[d]] = n
            vol[sidx[s], didx[d]] = v
    ok = vol[:, is_train].sum(1) >= MIN_VOL
    sel = np.where(ok)[0]

    def rates(mask):
        n = net[sel][:, mask]
        return (n >= T).mean(1), (n <= -T).mean(1), n.mean(1)

    s_tr, o_tr, m_tr = rates(is_train)
    s_te, o_te, m_te = rates(is_test)

    def topk(x, k=K):
        return set(np.argsort(-x)[:k])

    print(f"\n## {bname}: 대상 대여소 {len(sel)}곳")
    for label, tr, te in [("부족 압력(순유출>=%d일 비율)" % T, s_tr, s_te),
                          ("과잉 압력(순유입>=%d일 비율)" % T, o_tr, o_te)]:
        hit = len(topk(tr) & topk(te)) / K
        # 단순 기준선: 평균 순유출(부호 반영) 순위
        base_tr = m_tr if "부족" in label else -m_tr
        base = len(topk(base_tr) & topk(te)) / K
        rho = spearmanr(tr, te)[0]
        print(f"  {label}: 상위{K} 적중 {hit:.2f} (평균순유출 순위 {base:.2f}, 무작위 기대 {K / len(sel):.2f}), 순위상관 {rho:.2f}")

    # 학습 기준 상위 목록 (집계, 대여소 단위)
    for label, tr, te in [("부족", s_tr, s_te), ("과잉", o_tr, o_te)]:
        order = np.argsort(-tr)[:10]
        out_lines.append(f"\n### {bname} — {label} 압력 상위 10 (학습 순위 -> 검증 값)")
        out_lines.append("| 대여소 | 학습 비율 | 검증 비율 | 학습 평균 순유출 |")
        out_lines.append("|---|---|---|---|")
        for i in order:
            sid = sids[sel[i]]
            out_lines.append(f"| {names.get(sid, sid)} | {tr[i]:.2f} | {te[i]:.2f} | {m_tr[i]:+.1f} |")

    # 날씨 영향: 비/한파 날 부족 압력 (학습 상위 K)
    wd = dict(con.execute("""
        SELECT CAST(ts AS DATE) d, max(CASE WHEN precip >= 1 THEN 1 ELSE 0 END)*1 + (min(temp) < 0)::INT * 2
        FROM (SELECT * FROM weather) GROUP BY 1""").fetchall())
    flag = np.array([wd.get(d, 0) for d in dlist])
    bad = (flag > 0)
    top = np.argsort(-s_tr)[:K]
    n_top = net[sel][top]
    for lab, mk in [("비 또는 영하", bad), ("그 외", ~bad)]:
        mk2 = mk & (is_train | is_test)
        print(f"  상위{K} 부족 대여소 평균 구간 순유출 ({lab}, {mk2.sum()}일): {n_top[:, mk2].mean():+.2f}")

os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
with open(os.path.join(ROOT, "reports", "risk_ranking.md"), "w", encoding="utf-8") as f:
    f.write("# 대여소 x 시간대 압력 순위 (집계)\n\n평일 구간 순유출 >= %d 인 날의 비율. 구간 총 이용 %d건 미만 대여소는 제외. "
            "재고가 아니라 순유출 압력이다. 출처: 대전교통공사 타슈 대여이력(공공데이터포털).\n" % (T, MIN_VOL))
    f.write("\n".join(out_lines) + "\n")
print("\n저장: reports/risk_ranking.md")

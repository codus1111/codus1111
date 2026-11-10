"""5차 분석: 날씨·시간대·요일·학기로 한남대 수요/순유출을 시간 단위로 예측 (xgboost).

타깃 A: 캠퍼스 대여소 합 시간당 대여 수
타깃 B: 한남대 후문(ST0289) 시간당 순유출 (대여 - 반납)
분할: 시간순. 학습 = 2025-12 ~ 2026-08, 검증 = 2026-09 ~ 10 (학기 중, 학습에서 못 본 기간).
기준선: (1) 전체 평균 (2) 시간대 x 주말 x 학기 평균. 지표: MAE.
출력은 집계·모델 지표만 사용한다.
"""
import os
import sys

import duckdb
import numpy as np
import xgboost as xgb

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = duckdb.connect(os.path.join(ROOT, "data", "processed", "tashu.duckdb"), read_only=True)

con.execute("""
CREATE TEMP TABLE hn AS
SELECT id FROM stations
WHERE name LIKE '%한남대학교%' AND name NOT LIKE '%방면%' AND id <> 'ST1081'
""")
rows = con.execute("""
WITH c AS (
  SELECT CAST(d AS TIMESTAMP) + h * INTERVAL 1 HOUR ts, sum(rentals) rent
  FROM flows WHERE sid IN (SELECT id FROM hn) GROUP BY ALL
), g AS (
  SELECT CAST(d AS TIMESTAMP) + h * INTERVAL 1 HOUR ts, sum(rentals - returns) net
  FROM flows WHERE sid = 'ST0289' GROUP BY ALL
)
SELECT w.ts, coalesce(c.rent, 0), coalesce(g.net, 0),
       w.temp, w.humidity, w.precip, w.wind,
       hour(w.ts), dayofweek(w.ts), month(w.ts), dayofyear(w.ts)
FROM weather w LEFT JOIN c ON c.ts = w.ts LEFT JOIN g ON g.ts = w.ts
ORDER BY w.ts
""").fetchall()

A = np.array([[float(v) for v in r[1:]] for r in rows])
yA, yB = A[:, 0], A[:, 1]
temp, hum, precip, wind = A[:, 2], A[:, 3], A[:, 4], A[:, 5]
hr, dow, mo = A[:, 6].astype(int), A[:, 7].astype(int), A[:, 8].astype(int)
weekend = ((dow == 0) | (dow == 6)).astype(int)
semester = np.isin(mo, [3, 4, 5, 6, 9, 10]).astype(int)
X = np.column_stack([hr, dow, weekend, semester, temp, hum, precip, wind])
fn = ["hour", "dow", "weekend", "semester", "temp", "humidity", "precip", "wind"]

train = mo != 99
train = (mo <= 8) | (mo == 12)
test = np.isin(mo, [9, 10])
print(f"학습 {train.sum()}시간, 검증 {test.sum()}시간 (9~10월)")


class Model:
    """sklearn 래퍼는 이 PC에서 막혀 있어(sklearn 차단) xgboost 네이티브 API를 쓴다."""

    def __init__(self, y, objective):
        params = dict(max_depth=4, eta=0.05, subsample=0.8, colsample_bytree=0.8,
                      objective=objective, seed=0)
        self.b = xgb.train(params, xgb.DMatrix(X[train], label=y[train], feature_names=fn), 300)

    def predict(self, X_):
        return self.b.predict(xgb.DMatrix(X_, feature_names=fn))

    @property
    def importance(self):
        g = self.b.get_score(importance_type="gain")
        t = sum(g.values())
        return {k: v / t for k, v in g.items()}


def fit(y, objective):
    return Model(y, objective)


def base_cell(y):
    """시간대 x 주말 x 학기 평균 기준선 (학습 구간 평균)."""
    key = hr * 4 + weekend * 2 + semester
    out = np.full(len(y), y[train].mean())
    for k in np.unique(key[train]):
        out[key == k] = y[train & (key == k)].mean()
    return out


def report(name, y, objective, mask_sets):
    m = fit(y, objective)
    p = m.predict(X)
    b0 = np.full(len(y), y[train].mean())
    b1 = base_cell(y)
    print(f"\n## {name}")
    for label, mk in mask_sets:
        mk = mk & test
        if mk.sum() == 0:
            continue
        e0 = np.abs(y[mk] - b0[mk]).mean()
        e1 = np.abs(y[mk] - b1[mk]).mean()
        e2 = np.abs(y[mk] - p[mk]).mean()
        print(f"  {label:<22} n={mk.sum():4d}  MAE 전체평균 {e0:.3f} | 셀평균 {e1:.3f} | xgboost {e2:.3f}"
              f"  (셀평균 대비 {100 * (1 - e2 / e1):+.1f}%)")
    imp = sorted(m.importance.items(), key=lambda t: -t[1])
    print("  중요도:", ", ".join(f"{n} {v:.2f}" for n, v in imp[:5]))
    return m, p


allm = np.ones(len(yA), bool)
wk = weekend == 0
rainy = precip >= 1.0
sets = [("전체 시간", allm), ("평일 8~19시", wk & (hr >= 8) & (hr <= 19)),
        ("평일 15~16시", wk & np.isin(hr, [15, 16])), ("비 온 시간", rainy)]
mA, pA = report("A. 캠퍼스 시간당 대여 (제곱오차)", yA, "reg:squarederror", sets)
mA2, pA2 = report("A'. 캠퍼스 시간당 대여 (포아송 목적)", yA, "count:poisson", sets)
mB, pB = report("B. 후문 시간당 순유출 (대여-반납)", yB, "reg:squarederror", sets)

# 후문 오후 순유출 부호 적중: 평일 15~16시 검증 구간에서 '순유출>0' 여부
mk = test & wk & np.isin(hr, [15, 16])
hit = np.mean((pB[mk] > 0) == (yB[mk] > 0))
print(f"\n후문 평일 15~16시 순유출 방향(>0) 적중률: {hit:.2f} (n={mk.sum()}), 기준선 '항상 유출': {np.mean(yB[mk] > 0):.2f}")
print(f"평일 15~16시 평균 순유출 실제 {yB[mk].mean():.2f}, 예측 {pB[mk].mean():.2f}")

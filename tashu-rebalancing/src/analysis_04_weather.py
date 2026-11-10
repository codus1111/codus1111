"""4차 분석: 날씨를 통제했을 때 한남대 캠퍼스 대여소 수요에 학사일정 효과가 얼마나 남는가.

시간 단위 대여 수(캠퍼스 대여소 합)를 포아송 회귀로 설명한다.
statsmodels.api는 이 PC의 보안 정책(pandas DLL)으로 막혀 있어 numpy로 IRLS를 직접 구현했다.
출력은 집계·모델 계수만 사용한다.
"""
import os
import sys

import duckdb
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = duckdb.connect(os.path.join(ROOT, "data", "processed", "tashu.duckdb"), read_only=True)

# 한남대 캠퍼스 대여소 (대덕밸리캠퍼스 ST1081 제외)
con.execute("""
CREATE TEMP TABLE hn AS
SELECT id FROM stations
WHERE name LIKE '%한남대학교%' AND name NOT LIKE '%방면%' AND id <> 'ST1081'
""")
rows = con.execute("""
WITH r AS (
  SELECT CAST(f.d AS TIMESTAMP) + f.h * INTERVAL 1 HOUR AS ts, sum(f.rentals) rentals
  FROM flows f WHERE f.sid IN (SELECT id FROM hn) GROUP BY ALL
)
SELECT w.ts, coalesce(r.rentals, 0) y, w.temp, w.precip, w.wind,
       hour(w.ts) h, dayofweek(w.ts) dow, month(w.ts) mo
FROM weather w LEFT JOIN r ON r.ts = w.ts
WHERE month(w.ts) <> 12
ORDER BY w.ts
""").fetchall()

ts = [r[0] for r in rows]
y = np.array([r[1] for r in rows], float)
temp = np.array([r[2] for r in rows], float)
precip = np.array([r[3] for r in rows], float)
wind = np.array([r[4] for r in rows], float)
hr = np.array([r[5] for r in rows])
dow = np.array([r[6] for r in rows])
mo = np.array([r[7] for r in rows])
weekend = ((dow == 0) | (dow == 6)).astype(float)
semester = np.isin(mo, [3, 4, 5, 6, 9, 10]).astype(float)
rain = (precip >= 1.0).astype(float)
print(f"관측 시간 수: {len(y)} (12월 제외), 캠퍼스 대여소 {con.execute('select count(*) from hn').fetchall()[0][0]}곳")

# 1) 날씨 구간별 평균 (평일 8~19시, 학기)
mask = (weekend == 0) & (semester == 1) & (hr >= 8) & (hr <= 19)
print("\n## 평일 8~19시, 학기: 기온 구간별 시간당 평균 대여 (캠퍼스 합)")
for lo, hi in [(-99, 5), (5, 15), (15, 25), (25, 99)]:
    m = mask & (temp >= lo) & (temp < hi)
    print(f"  {lo:>4}~{hi:<3}°C  n={m.sum():4d}  mean={y[m].mean():.2f}" if m.sum() else f"  {lo}~{hi} 없음")
print("## 같은 조건, 강수별")
for name, m in [("비 없음(<1mm)", mask & (rain == 0)), ("비(≥1mm)", mask & (rain == 1))]:
    print(f"  {name}  n={m.sum():4d}  mean={y[m].mean():.2f}")

print("\n## 원시 비교: 평일 하루 평균 시간당 대여 (학기 vs 방학), 날씨 통제 전")
wk = weekend == 0
raw_s = y[wk & (semester == 1)].mean()
raw_v = y[wk & (semester == 0)].mean()
print(f"  학기 {raw_s:.2f}, 방학 {raw_v:.2f}, 비율 {raw_s / raw_v:.2f}배")
for name, ms in [("방학(1~2월)", np.isin(mo, [1, 2])), ("방학(7~8월)", np.isin(mo, [7, 8]))]:
    print(f"  {name} 평일 시간당 평균 {y[wk & ms].mean():.2f}")

# 2) 포아송 회귀 (IRLS)
def design():
    cols, names = [np.ones(len(y))], ["const"]
    for nm, c in [("학기(vs 방학)", semester), ("주말", weekend), ("비(≥1mm)", rain),
                  ("바람(+10km/h)", wind / 10.0)]:
        cols.append(c)
        names.append(nm)
    for lo, hi, nm in [(-99, 5, "기온<5°C"), (5, 15, "기온5~15°C"), (25, 99, "기온≥25°C")]:  # 기준 15~25
        cols.append(((temp >= lo) & (temp < hi)).astype(float))
        names.append(nm)
    for h in range(1, 24):
        cols.append((hr == h).astype(float))
        names.append(f"h{h:02d}")
    return np.column_stack(cols), names


X, names = design()
beta = np.zeros(X.shape[1])
beta[0] = np.log(y.mean() + 1e-9)
for it in range(60):
    eta = np.clip(X @ beta, -20, 20)
    mu = np.exp(eta)
    z = eta + (y - mu) / mu
    W = mu
    XtWX = X.T @ (X * W[:, None]) + 1e-6 * np.eye(X.shape[1])
    new = np.linalg.solve(XtWX, X.T @ (W * z))
    if np.max(np.abs(new - beta)) < 1e-8:
        beta = new
        break
    beta = new
mu = np.exp(np.clip(X @ beta, -20, 20))
cov = np.linalg.inv(X.T @ (X * mu[:, None]) + 1e-6 * np.eye(X.shape[1]))
pearson = np.sum((y - mu) ** 2 / mu) / (len(y) - X.shape[1])  # 과대산포 보정
se = np.sqrt(np.diag(cov) * pearson)
dev = 2 * np.sum(np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0) - (y - mu))
y0 = y.mean()
dev0 = 2 * np.sum(np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / y0), 0) - (y - y0))
print(f"\n## 포아송 회귀 (반복 {it + 1}회), 과대산포 계수 {pearson:.2f}, 설명 편차 비율 {1 - dev / dev0:.2f}")
print("변수 | 비율(exp(계수)) | 95% 구간")
for i, nm in enumerate(names[:8]):
    if nm == "const":
        continue
    lo, hi = np.exp(beta[i] - 1.96 * se[i]), np.exp(beta[i] + 1.96 * se[i])
    print(f"  {nm} | {np.exp(beta[i]):.2f} | {lo:.2f}~{hi:.2f}")

# 시간대 효과 상위 (기준 0시 대비)
hr_eff = [(names[i], np.exp(beta[i])) for i in range(8, len(names))]
top = sorted(hr_eff, key=lambda t: -t[1])[:5]
print("시간대 효과 상위(0시 대비 배수):", ", ".join(f"{n}={v:.1f}" for n, v in top))

# 날씨 통제 후 학기 효과 vs 원시 비율
print(f"\n학기 효과: 원시 {raw_s / raw_v:.2f}배 → 날씨·시간대 통제 후 {np.exp(beta[1]):.2f}배")

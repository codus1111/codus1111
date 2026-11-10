"""flows_clean 만들기: flows와 같은 집계에서 '이용시간 180분 이상'과 '같은 대여소에서 빌리고 반납한 건'을 뺀다.

실험 08(민감도 확인)용이다. 기본 분석(flows)은 그대로 두고, 환경변수 CLEAN=1로 실행하면
분석 스크립트가 flows 대신 flows_clean을 쓴다(src/_clean.py).
"""
import os
import sys

import duckdb

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = duckdb.connect(os.path.join(ROOT, "data", "processed", "tashu.duckdb"))
con.execute("DROP TABLE IF EXISTS flows_clean")
con.execute("""
CREATE TABLE flows_clean AS
WITH base AS (
  SELECT * FROM rentals WHERE minutes < 180 AND rent_id <> ret_id
), o AS (
  SELECT rent_id sid, CAST(rent_ts AS DATE) d, hour(rent_ts) h,
         count(*) FILTER (WHERE NOT ctrl_rent AND minutes > 0) AS rentals,
         count(*) FILTER (WHERE ctrl_rent)                     AS ctrl_out
  FROM base WHERE rent_ts IS NOT NULL GROUP BY ALL
), i AS (
  SELECT ret_id sid, CAST(ret_ts AS DATE) d, hour(ret_ts) h,
         count(*) FILTER (WHERE NOT ctrl_ret AND minutes > 0) AS returns,
         count(*) FILTER (WHERE ctrl_ret)                     AS ctrl_in
  FROM base WHERE ret_ts IS NOT NULL GROUP BY ALL
)
SELECT coalesce(o.sid, i.sid) sid, coalesce(o.d, i.d) d, coalesce(o.h, i.h) h,
       coalesce(rentals, 0) rentals, coalesce(returns, 0) returns,
       coalesce(ctrl_out, 0) ctrl_out, coalesce(ctrl_in, 0) ctrl_in
FROM o FULL OUTER JOIN i ON o.sid = i.sid AND o.d = i.d AND o.h = i.h
""")
a, b = con.execute("SELECT sum(rentals), sum(returns) FROM flows").fetchall()[0]
c, d = con.execute("SELECT sum(rentals), sum(returns) FROM flows_clean").fetchall()[0]
print(f"flows       대여 {a:,} 반납 {b:,}")
print(f"flows_clean 대여 {c:,} 반납 {d:,}  (대여 {a - c:,}건 제외, {100 * (a - c) / a:.1f}%)")

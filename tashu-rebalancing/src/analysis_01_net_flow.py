"""1차 분석: 대여소별 순유출입(반납 - 대여)으로 부족·과잉 압력이 큰 곳을 찾는다.

순유출입 = 반납 수 - 대여 수 (관제센터 처리, 이용시간 0분 이하 제외).
음수면 자전거가 계속 빠져나가는(부족 압력) 대여소, 양수면 쌓이는(과잉 압력) 대여소.
출력은 대여소 단위 집계만 사용한다.
"""
import os
import sys

import duckdb

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = duckdb.connect(os.path.join(ROOT, "data", "processed", "tashu.duckdb"), read_only=True)


def q(sql, title):
    print(f"\n## {title}")
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    print(" | ".join(cols))
    for row in cur.fetchall():
        print(" | ".join(str(x) for x in row))


# 0. 전체 보존 확인: 사용자 대여 합 vs 반납 합
q("""
SELECT sum(rentals) rentals, sum(returns) returns, sum(returns) - sum(rentals) gap
FROM flows WHERE sid IN (SELECT id FROM stations)
""", "전체 대여/반납 합 (대여소만)")

BASE = """
SELECT s.name, s.gu, s.dong,
       sum(f.rentals) rentals, sum(f.returns) returns,
       sum(f.returns) - sum(f.rentals) net,
       round(100.0 * (sum(f.returns) - sum(f.rentals)) / nullif(sum(f.rentals) + sum(f.returns), 0), 1) net_pct
FROM flows f JOIN stations s ON s.id = f.sid
{where}
GROUP BY s.id, s.name, s.gu, s.dong
HAVING sum(f.rentals) + sum(f.returns) >= {minvol}
ORDER BY net {order}
LIMIT 12
"""

q(BASE.format(where="", minvol=3000, order="ASC"), "11개월 누적 순유출 상위 (부족 압력)")
q(BASE.format(where="", minvol=3000, order="DESC"), "11개월 누적 순유입 상위 (과잉 압력)")

WD_AM = "WHERE dayofweek(f.d) BETWEEN 1 AND 5 AND f.h BETWEEN 7 AND 9"
WD_PM = "WHERE dayofweek(f.d) BETWEEN 1 AND 5 AND f.h BETWEEN 17 AND 19"
q(BASE.format(where=WD_AM, minvol=800, order="ASC"), "평일 출근(7~9시) 순유출 상위")
q(BASE.format(where=WD_PM, minvol=800, order="ASC"), "평일 퇴근(17~19시) 순유출 상위")

q("""
SELECT s.gu, sum(f.rentals) rentals, sum(f.returns) returns, sum(f.returns) - sum(f.rentals) net
FROM flows f JOIN stations s ON s.id = f.sid GROUP BY s.gu ORDER BY net
""", "구별 순유출입")

# 같은 대여소에서의 시간대 비대칭: 출근 순유출과 퇴근 순유입이 함께 큰 곳 = 통근 패턴
q("""
WITH t AS (
  SELECT sid,
    sum(CASE WHEN dayofweek(d) BETWEEN 1 AND 5 AND h BETWEEN 7 AND 9 THEN returns - rentals END) am,
    sum(CASE WHEN dayofweek(d) BETWEEN 1 AND 5 AND h BETWEEN 17 AND 19 THEN returns - rentals END) pm,
    sum(rentals + returns) vol
  FROM flows GROUP BY sid
)
SELECT s.name, s.gu, am, pm, vol FROM t JOIN stations s ON s.id = t.sid
WHERE vol >= 3000 AND am < 0 AND pm > 0
ORDER BY (pm - am) DESC LIMIT 12
""", "출근엔 비고 퇴근엔 쌓이는 곳 (통근 편중)")

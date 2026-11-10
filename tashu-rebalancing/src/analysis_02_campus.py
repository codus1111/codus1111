"""2차 분석: 대학 캠퍼스 주변 대여소의 시간대별 수급 압력.

캠퍼스는 대여소 이름 키워드로 묶는다(병원·아파트 등 이름만 비슷한 곳은 제외).
학기(3~6월, 9~10월)와 방학(1~2월, 7~8월)을 나눠 비교한다.
출력은 캠퍼스·대여소 단위 집계만 사용한다.
"""
import os
import sys

import duckdb

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = duckdb.connect(os.path.join(ROOT, "data", "processed", "tashu.duckdb"), read_only=True)

CAMPUS_SQL = """
CASE
  WHEN name LIKE '%카이스트%' AND name NOT LIKE '%카이스트빌%' THEN 'KAIST'
  WHEN gu = '유성구' AND (name LIKE '%충남대학교%' OR name LIKE '%충대%') AND name NOT LIKE '%병원%' THEN '충남대'
  WHEN name LIKE '%한남대%' THEN '한남대'
  WHEN name LIKE '%목원대%' THEN '목원대'
  WHEN name LIKE '%우송대%' THEN '우송대'
  WHEN name LIKE '%침신대%' OR name LIKE '%침례신학%' THEN '침신대'
  WHEN name LIKE '%한밭대학교%' THEN '한밭대'
  WHEN name LIKE '%대전대%' AND name NOT LIKE '%병원%' AND name NOT LIKE '%한방%' THEN '대전대'
END
"""

con.execute(f"CREATE TEMP TABLE campus AS SELECT id, name, {CAMPUS_SQL} AS campus FROM stations")
con.execute("DELETE FROM campus WHERE campus IS NULL")
con.execute("""
CREATE TEMP TABLE cf AS
SELECT c.campus, c.id sid, c.name, f.d, f.h, f.rentals, f.returns,
       CASE WHEN month(f.d) IN (3,4,5,6,9,10) THEN '학기'
            WHEN month(f.d) IN (1,2,7,8) THEN '방학' ELSE '기타' END term,
       dayofweek(f.d) BETWEEN 1 AND 5 AS weekday
FROM flows f JOIN campus c ON c.id = f.sid
""")


def q(sql, title):
    print(f"\n## {title}")
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    print(" | ".join(cols))
    for row in cur.fetchall():
        print(" | ".join(str(x) for x in row))


q("""
SELECT campus, count(*) stations FROM campus GROUP BY campus ORDER BY stations DESC
""", "캠퍼스별 대여소 수")

# 평일 하루 평균 이용(대여): 학기 vs 방학
q("""
WITH days AS (
  SELECT term, count(DISTINCT d) n FROM cf WHERE weekday GROUP BY term
)
SELECT campus,
  round(sum(CASE WHEN term='학기' THEN rentals END) / (SELECT n FROM days WHERE term='학기')) sem_day_rentals,
  round(sum(CASE WHEN term='방학' THEN rentals END) / (SELECT n FROM days WHERE term='방학')) vac_day_rentals,
  round(sum(CASE WHEN term='학기' THEN rentals END) / (SELECT n FROM days WHERE term='학기')
      / (sum(CASE WHEN term='방학' THEN rentals END) / (SELECT n FROM days WHERE term='방학')), 2) ratio
FROM cf WHERE weekday GROUP BY campus ORDER BY sem_day_rentals DESC
""", "평일 하루 평균 대여: 학기 vs 방학")

# 캠퍼스 전체의 시간대별 순유출입(반납-대여), 학기 평일 하루 평균
hours = ", ".join(
    f"round(sum(CASE WHEN h={h} THEN returns-rentals END)/max(nd),1) h{h:02d}" for h in range(7, 23)
)
q(f"""
WITH nd AS (SELECT count(DISTINCT d) nd FROM cf WHERE weekday AND term='학기')
SELECT campus, {hours}
FROM cf, nd WHERE weekday AND term='학기' GROUP BY campus ORDER BY campus
""", "학기 평일, 캠퍼스 전체 시간대별 하루 평균 순유출입 (음수=빠져나감)")

# 대여소별 일중 누적 순유출 최저점(고갈 압력): 05시부터 누적
q("""
WITH x AS (
  SELECT campus, sid, name, d, h,
         sum(returns - rentals) OVER (PARTITION BY sid, d ORDER BY h) cum
  FROM cf WHERE weekday AND term='학기'
), m AS (
  SELECT campus, sid, name, d, min(cum) lowest FROM x GROUP BY ALL
)
SELECT campus, name,
       round(avg(lowest), 1) avg_lowest,
       round(100.0 * avg(CASE WHEN lowest <= -10 THEN 1 ELSE 0 END), 0) pct_days_le_m10,
       count(*) n_days
FROM m GROUP BY campus, name
HAVING count(*) >= 60 AND avg(lowest) < -5
ORDER BY avg_lowest LIMIT 15
""", "학기 평일, 하루 중 누적 순유출 최저점이 깊은 캠퍼스 대여소 (고갈 압력)")

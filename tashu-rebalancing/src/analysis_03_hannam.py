"""3차 분석: 한남대 주변 대여소.

1) 이름에 '한남대'가 들어간 대여소 + 정문 기준 반경 안의 인근 대여소를 좌표로 확장
2) 요일·월별·시간대 패턴
3) 대여소 단위 이동 방향(집계)
출력은 대여소 단위 집계만 사용한다(개별 이용 기록·자전거번호 없음).
"""
import os
import sys

import duckdb

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = duckdb.connect(os.path.join(ROOT, "data", "processed", "tashu.duckdb"), read_only=True)
RADIUS_M = 500  # 정문 또는 후문 기준 인근 반경


def q(sql, title, limit=None):
    print(f"\n## {title}")
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    print(" | ".join(cols))
    for row in cur.fetchall()[:limit]:
        print(" | ".join(str(x) for x in row))


# 1) 대여소 확장: 정문(ST0080) 기준 반경
con.execute(f"""
CREATE TEMP TABLE hn AS
WITH c AS (SELECT lat clat, lon clon FROM stations WHERE id IN ('ST0080', 'ST0289')),
d AS (
  SELECT s.id, s.name,
    min(6371000 * 2 * asin(sqrt(
      pow(sin(radians(s.lat - c.clat) / 2), 2) +
      cos(radians(c.clat)) * cos(radians(s.lat)) * pow(sin(radians(s.lon - c.clon) / 2), 2)
    ))) AS dist_m
  FROM stations s, c GROUP BY s.id, s.name
)
SELECT id, name, round(dist_m) dist_m,
       CASE WHEN name LIKE '%한남대학교%' AND name NOT LIKE '%방면%' THEN '캠퍼스' ELSE '인근' END kind
FROM d
WHERE (name LIKE '%한남대%' AND dist_m <= 1500) OR dist_m <= {RADIUS_M}
""")
q("""
SELECT h.kind, h.id, h.name, h.dist_m, coalesce(sum(f.rentals + f.returns), 0) vol
FROM hn h LEFT JOIN flows f ON f.sid = h.id
GROUP BY ALL ORDER BY h.kind, vol DESC
""", f"한남대 정문·후문 기준 반경 {RADIUS_M}m 인근 + 이름 매칭 (kind: 캠퍼스/인근)")

con.execute("""
CREATE TEMP TABLE hf AS
SELECT h.kind, h.id sid, h.name, f.d, f.h, f.rentals, f.returns,
       dayofweek(f.d) dow,
       CASE WHEN month(f.d) IN (3,4,5,6,9,10) THEN '학기'
            WHEN month(f.d) IN (1,2,7,8) THEN '방학' ELSE '기타' END term
FROM flows f JOIN hn h ON h.id = f.sid
""")

# 2) 요일 패턴 (학기, 하루 평균 대여/반납)
q("""
WITH n AS (SELECT dow, count(DISTINCT d) nd FROM hf WHERE term='학기' GROUP BY dow)
SELECT CASE hf.dow WHEN 0 THEN '일' WHEN 1 THEN '월' WHEN 2 THEN '화' WHEN 3 THEN '수'
                   WHEN 4 THEN '목' WHEN 5 THEN '금' ELSE '토' END dow,
       round(sum(CASE WHEN kind='캠퍼스' THEN rentals END) / max(nd)) campus_rentals,
       round(sum(CASE WHEN kind='인근' THEN rentals END) / max(nd)) near_rentals,
       round(sum(returns - rentals) / max(nd), 1) net_all
FROM hf JOIN n USING (dow) WHERE term='학기' GROUP BY hf.dow ORDER BY (hf.dow + 6) % 7
""", "학기 요일별 하루 평균 (캠퍼스/인근 대여, 전체 순유출입)")

# 월별 평일 하루 평균 대여
q("""
WITH n AS (SELECT strftime(d, '%Y-%m') m, count(DISTINCT d) nd FROM hf
           WHERE dow BETWEEN 1 AND 5 GROUP BY m)
SELECT strftime(d, '%Y-%m') ym,
       round(sum(CASE WHEN kind='캠퍼스' THEN rentals END) / max(nd)) campus,
       round(sum(CASE WHEN kind='인근' THEN rentals END) / max(nd)) near
FROM hf JOIN n ON n.m = strftime(hf.d, '%Y-%m') WHERE dow BETWEEN 1 AND 5
GROUP BY ym ORDER BY ym
""", "월별 평일 하루 평균 대여")

# 시간대 패턴: 학기 평일, 대여소별 순유출입(하루 평균). 거래량 상위 대여소.
hours = ", ".join(f"round(sum(CASE WHEN h={h} THEN returns-rentals END)/max(nd),1) h{h:02d}"
                  for h in (7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21))
q(f"""
WITH nd AS (SELECT count(DISTINCT d) nd FROM hf WHERE dow BETWEEN 1 AND 5 AND term='학기'),
top AS (SELECT sid FROM hf GROUP BY sid ORDER BY sum(rentals + returns) DESC LIMIT 8)
SELECT name, {hours}
FROM hf, nd WHERE dow BETWEEN 1 AND 5 AND term='학기' AND sid IN (SELECT sid FROM top)
GROUP BY name ORDER BY name
""", "학기 평일, 거래량 상위 8개 대여소 시간대별 하루 평균 순유출입(음수=빠져나감)")

# 3) 이동 방향: 캠퍼스 대여소에서 대여 → 어디로 반납 / 캠퍼스로 반납 ← 어디서 대여 (학기 평일)
base = """
FROM rentals r
WHERE NOT r.ctrl_rent AND NOT r.ctrl_ret AND r.minutes > 0
  AND dayofweek(r.rent_ts) BETWEEN 1 AND 5 AND month(r.rent_ts) IN (3,4,5,6,9,10)
"""
q(f"""
SELECT coalesce(r.ret_dong, '?') dong, r.ret_name, count(*) trips
{base} AND r.rent_id IN (SELECT id FROM hn WHERE kind='캠퍼스')
  AND r.ret_id NOT IN (SELECT id FROM hn WHERE kind='캠퍼스')
GROUP BY ALL ORDER BY trips DESC LIMIT 10
""", "학기 평일, 캠퍼스 대여소에서 빌려 외부 대여소로 반납 (도착지 상위)")
q(f"""
SELECT coalesce(r.rent_dong, '?') dong, r.rent_name, count(*) trips
{base} AND r.ret_id IN (SELECT id FROM hn WHERE kind='캠퍼스')
  AND r.rent_id NOT IN (SELECT id FROM hn WHERE kind='캠퍼스')
GROUP BY ALL ORDER BY trips DESC LIMIT 10
""", "학기 평일, 외부에서 빌려 캠퍼스 대여소로 반납 (출발지 상위)")
q(f"""
SELECT
  count(*) FILTER (WHERE rent_id IN (SELECT id FROM hn WHERE kind='캠퍼스')
                   AND ret_id IN (SELECT id FROM hn WHERE kind='캠퍼스')) campus_to_campus,
  count(*) FILTER (WHERE rent_id IN (SELECT id FROM hn WHERE kind='캠퍼스')
                   AND ret_id NOT IN (SELECT id FROM hn WHERE kind='캠퍼스')) campus_out,
  count(*) FILTER (WHERE rent_id NOT IN (SELECT id FROM hn WHERE kind='캠퍼스')
                   AND ret_id IN (SELECT id FROM hn WHERE kind='캠퍼스')) campus_in
{base}
""", "학기 평일 캠퍼스 이동 구성 (캠퍼스 내부/나감/들어옴)")

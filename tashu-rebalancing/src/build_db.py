"""월별 타슈 대여이력 CSV를 정제해 DuckDB(data/processed/tashu.duckdb)로 만든다.

- 인코딩이 월별로 섞여 있어 utf-8 → CP949 순으로 시도한다.
- 개인 추적 방지: 자전거번호는 저장하지 않는다.
- 원본 컬럼명의 '대여_X좌표'는 실제로 위도(36.x), 'Y좌표'는 경도(127.x)이다.
- 만들어지는 테이블
    rentals  : 이용 1건당 1행 (자전거번호 제외)
    stations : 대여소 마스터
    flows    : 대여소 × 날짜 × 시간 단위 집계 (분석의 기본 단위)
"""
import glob
import os
import sys
import time

import duckdb

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "tashu")
OUT = os.path.join(ROOT, "data", "processed", "tashu.duckdb")

SELECT = """
SELECT
  TRY_CAST("대여일시" AS TIMESTAMP)      AS rent_ts,
  "대여_대여소ID"                        AS rent_id,
  "대여_대여소명"                        AS rent_name,
  TRY_CAST("대여_X좌표" AS DOUBLE)       AS rent_lat,
  TRY_CAST("대여_Y좌표" AS DOUBLE)       AS rent_lon,
  "대여_구"                              AS rent_gu,
  "대여_동"                              AS rent_dong,
  TRY_CAST("반납일시" AS TIMESTAMP)      AS ret_ts,
  "반납_대여소ID"                        AS ret_id,
  "반납_대여소명"                        AS ret_name,
  TRY_CAST("반납_X좌표" AS DOUBLE)       AS ret_lat,
  TRY_CAST("반납_Y좌표" AS DOUBLE)       AS ret_lon,
  "반납_구"                              AS ret_gu,
  "반납_동"                              AS ret_dong,
  TRY_CAST("이용시간(분)" AS DOUBLE)     AS minutes,
  TRY_CAST("이용거리(km)" AS DOUBLE)     AS km,
  '{month}'                              AS src_month
FROM read_csv('{path}', encoding='{enc}', header=true, all_varchar=true)
"""


def load_file(con, path, month, first):
    path = path.replace("\\", "/")
    last = None
    for enc in ("utf-8", "CP949"):
        try:
            sql = SELECT.format(path=path, enc=enc, month=month)
            if first:
                con.execute("CREATE TABLE rentals AS " + sql)
            else:
                con.execute("INSERT INTO rentals " + sql)
            return enc
        except Exception as e:  # 인코딩 불일치
            last = e
    raise RuntimeError(f"읽기 실패: {path}: {last}")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        os.remove(OUT)
    con = duckdb.connect(OUT)
    t0 = time.time()

    files = sorted(glob.glob(os.path.join(RAW, "*.csv")))
    if not files:
        sys.exit("data/raw/tashu/*.csv 가 없습니다.")
    for i, f in enumerate(files):
        month = os.path.basename(f).split("(")[-1].split(")")[0]
        enc = load_file(con, f, month, first=(i == 0))
        print(f"{month} {enc}")

    n = con.execute("SELECT count(*) FROM rentals").fetchall()[0][0]
    print("rentals rows:", n)

    # 품질 플래그
    con.execute("ALTER TABLE rentals ADD COLUMN ctrl_rent BOOLEAN")
    con.execute("ALTER TABLE rentals ADD COLUMN ctrl_ret BOOLEAN")
    con.execute("UPDATE rentals SET ctrl_rent = coalesce(rent_name LIKE '%관제%', false), "
                "ctrl_ret = coalesce(ret_name LIKE '%관제%', false)")

    # 대여소 마스터 (대여·반납 양쪽에서 수집)
    con.execute("""
    CREATE TABLE stations AS
    SELECT id, any_value(name) AS name, any_value(gu) AS gu, any_value(dong) AS dong,
           median(lat) AS lat, median(lon) AS lon
    FROM (
      SELECT rent_id id, rent_name name, rent_gu gu, rent_dong dong, rent_lat lat, rent_lon lon
      FROM rentals WHERE NOT ctrl_rent AND rent_id IS NOT NULL
      UNION ALL
      SELECT ret_id, ret_name, ret_gu, ret_dong, ret_lat, ret_lon
      FROM rentals WHERE NOT ctrl_ret AND ret_id IS NOT NULL
    ) GROUP BY id
    """)

    # 대여소 × 날짜 × 시간 단위 집계. 이용시간 0분 이하(취소·오류)는 수요에서 제외.
    con.execute("""
    CREATE TABLE flows AS
    WITH o AS (
      SELECT rent_id sid, CAST(rent_ts AS DATE) d, hour(rent_ts) h,
             count(*) FILTER (WHERE NOT ctrl_rent AND minutes > 0) AS rentals,
             count(*) FILTER (WHERE ctrl_rent)                     AS ctrl_out
      FROM rentals WHERE rent_ts IS NOT NULL GROUP BY ALL
    ), i AS (
      SELECT ret_id sid, CAST(ret_ts AS DATE) d, hour(ret_ts) h,
             count(*) FILTER (WHERE NOT ctrl_ret AND minutes > 0) AS returns,
             count(*) FILTER (WHERE ctrl_ret)                     AS ctrl_in
      FROM rentals WHERE ret_ts IS NOT NULL GROUP BY ALL
    )
    SELECT coalesce(o.sid, i.sid) sid, coalesce(o.d, i.d) d, coalesce(o.h, i.h) h,
           coalesce(rentals, 0) rentals, coalesce(returns, 0) returns,
           coalesce(ctrl_out, 0) ctrl_out, coalesce(ctrl_in, 0) ctrl_in
    FROM o FULL OUTER JOIN i ON o.sid = i.sid AND o.d = i.d AND o.h = i.h
    """)

    ns = con.execute("SELECT count(*) FROM stations").fetchall()[0][0]
    nf = con.execute("SELECT count(*) FROM flows").fetchall()[0][0]
    print(f"stations: {ns}, flows rows: {nf}, elapsed {time.time() - t0:.1f}s")
    con.close()


if __name__ == "__main__":
    main()

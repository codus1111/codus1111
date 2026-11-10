"""data/raw/weather_daejeon.json 을 DuckDB의 weather 테이블로 적재한다.

출처: Open-Meteo Historical Weather API (재분석 모델 기반, 격자 약 25km 해상도), CC BY 4.0.
대전 좌표 약 (36.35, 127.385). 관측값이 아니라 모델 재분석 값이다.
"""
import json
import os
import sys

import duckdb

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "weather_daejeon.json")
DB = os.path.join(ROOT, "data", "processed", "tashu.duckdb")

h = json.load(open(SRC, encoding="utf-8"))["hourly"]
rows = list(zip(h["time"], h["temperature_2m"], h["relative_humidity_2m"], h["precipitation"],
                h["rain"], h["snowfall"], h["wind_speed_10m"], h["weather_code"]))

con = duckdb.connect(DB)
con.execute("DROP TABLE IF EXISTS weather")
con.execute("""
CREATE TABLE weather (ts TIMESTAMP, temp DOUBLE, humidity DOUBLE, precip DOUBLE,
                      rain DOUBLE, snow DOUBLE, wind DOUBLE, code INTEGER)
""")
con.executemany("INSERT INTO weather VALUES (CAST(? AS TIMESTAMP), ?, ?, ?, ?, ?, ?, ?)", rows)
n, a, b = con.execute("SELECT count(*), min(ts), max(ts) FROM weather").fetchall()[0]
print(f"weather rows: {n}, {a} ~ {b}")

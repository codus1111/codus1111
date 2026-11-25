"""타슈 앱 Open API(station) 재고 스냅샷을 1회 받아 로그에 한 줄 덧붙인다.

- 실행 1회 = 호출 1회. 반복은 실행 쪽(작업 스케줄러 등)에서 정하고, 한도를 넘지 않게 사용자가 간격을 정한다.
- 키는 .env의 TASHU_APP_API_KEY(헤더 api-token). 읽기 전용 GET.
- 저장: data/processed/stock_log.jsonl (gitignore). 한 줄 = {"t": 시각, "dow": 요일(0=월), "stock": {id: 대수}}.
- 같은 10분 안에 이미 받았으면 호출하지 않는다.
- 대여소별 재고 집계만 저장한다. 개별 자전거·이용자 정보는 없다.
"""
import json, os, sys, time, urllib.request
from datetime import datetime
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "data", "processed", "stock_log.jsonl")
URL = "https://bikeapp.tashu.or.kr:50041/v1/openapi/station"

now = datetime.now()
try:
    last = json.loads(open(LOG, encoding="utf-8").read().strip().splitlines()[-1])
    if time.time() - last["epoch"] < 600:
        print("10분 안에 이미 받음 — 호출 생략"); sys.exit(0)
except (OSError, IndexError, ValueError, KeyError):
    pass

key = (dotenv_values(os.path.join(ROOT, ".env")).get("TASHU_APP_API_KEY") or "").strip()
if not key:
    sys.exit("TASHU_APP_API_KEY가 .env에 없습니다.")
stock, url, pages = {}, URL, 0
while url and pages < 30:
    req = urllib.request.Request(url, headers={"api-token": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    for s in d.get("results", []):
        stock[str(s["id"])] = int(s["parking_count"])
    pages += 1
    url = d.get("next")
    if url:
        time.sleep(2)
with open(LOG, "a", encoding="utf-8") as f:
    f.write(json.dumps({"epoch": time.time(), "t": now.strftime("%Y-%m-%d %H:%M"),
                        "dow": now.weekday(), "stock": stock}, ensure_ascii=False) + "\n")
print(f"{now:%Y-%m-%d %H:%M} 저장: 대여소 {len(stock)}곳, 호출 {pages}회")

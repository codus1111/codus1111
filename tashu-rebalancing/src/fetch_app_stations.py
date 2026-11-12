"""타슈 앱 Open API(station) 대여소 목록 내려받기. 읽기 전용 GET, 호출 사이 간격을 둔다.
키는 .env의 TASHU_APP_API_KEY (헤더 api-token). 결과는 data/raw/tashu_app/ (gitignore).
실행: .venv/Scripts/python src/fetch_app_stations.py [최대쪽수]"""
import json, os, sys, time, urllib.request
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
key = dotenv_values(os.path.join(ROOT, ".env")).get("TASHU_APP_API_KEY")
assert key, ".env에 TASHU_APP_API_KEY가 없습니다"
url = "https://bikeapp.tashu.or.kr:50041/v1/openapi/station"
maxp = int(sys.argv[1]) if len(sys.argv) > 1 else 30
out, pages = [], 0
while url and pages < maxp:
    req = urllib.request.Request(url, headers={"api-token": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    pages += 1
    out += d.get("results", [])
    print(f"쪽 {pages}: count={d.get('count')}, 이번 {len(d.get('results', []))}건, next={'있음' if d.get('next') else '없음'}")
    url = d.get("next")
    time.sleep(2)
json.dump(out, open(os.path.join(ROOT, "data", "raw", "tashu_app", "stations.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("저장", len(out), "건; 항목:", sorted(out[0].keys()) if out else None)

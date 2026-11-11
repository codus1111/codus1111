"""대전광역시 타슈정보 API(공공데이터포털 15109253)에서 키오스크(대여소)별 거치대 수를 1회 받아 저장한다.

- 키는 .env의 TASHU_API_KEY. 호출은 한 번(numOfRows 충분히 크게), 응답은 data/raw/tashu_api/ (gitignore)에 저장한다.
- 응답 필드(명세 기준): kioskNo, year, signgu(자치구), lcNm(명칭), adres(주소), dfrCo(거치대 갯수), loCrdnt/laCrdnt(좌표),
  rm(비고), kioskId. 명세의 loCrdnt는 '위도'라고 적혀 있지만 실제 값은 경도다(좌표 이름이 서로 바뀜).
- 호출 주소와 한도는 docs/COMPLIANCE.md 참고.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "tashu_api", "tasuInfo.json")
URL = "https://apis.data.go.kr/6300000/openapi2022/tasuInfo/gettasuInfo"

if os.path.exists(OUT):
    print("이미 있음:", OUT)
    sys.exit(0)
key = (dotenv_values(os.path.join(ROOT, ".env")).get("TASHU_API_KEY") or "").strip()
if not key:
    sys.exit("TASHU_API_KEY가 .env에 없습니다.")
qs = urllib.parse.urlencode({"serviceKey": urllib.parse.unquote(key), "pageNo": 1, "numOfRows": 1000})
req = urllib.request.Request(URL + "?" + qs, headers={"User-Agent": "tashu-portfolio-learning-project"})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8")
except urllib.error.HTTPError as e:
    sys.exit(f"HTTP 오류 {e.code}")  # 응답 본문에 키가 들어 있을 수 있어 출력하지 않는다
j = json.loads(raw)
n = len(j["response"]["body"]["items"])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(raw)
print(f"저장: {OUT} (totalCount {j['response']['body']['totalCount']}, 받은 행 {n})")

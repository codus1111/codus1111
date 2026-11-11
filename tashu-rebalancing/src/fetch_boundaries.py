"""대전 구 경계(지도 배경용) 내려받기. geoBoundaries 한국 시군구(ADM2) 경계 파일 1개를 1회 받는다.

- 출처: geoBoundaries (wmgeolab, 원자료 citypopulation.de), 라이선스 CC BY 3.0 (출처 표기 필수)
  메타데이터: https://www.geoboundaries.org/api/current/gbOpen/KOR/ADM2/ (2026-11-11 확인)
- 저장 위치: data/raw/geo/ (gitignore 대상). 공식 배포 URL에서 한 번만 받고 반복 호출하지 않는다.
"""
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/KOR/ADM2/geoBoundaries-KOR-ADM2.geojson"
OUT = os.path.join(ROOT, "data", "raw", "geo", "geoBoundaries-KOR-ADM2.geojson")

if os.path.exists(OUT):
    print("이미 있음:", OUT)
else:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "tashu-portfolio-learning-project"})
    with urllib.request.urlopen(req, timeout=60) as r, open(OUT, "wb") as f:
        f.write(r.read())
    print("저장:", OUT, os.path.getsize(OUT), "bytes")

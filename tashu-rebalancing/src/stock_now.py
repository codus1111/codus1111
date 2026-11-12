"""타슈 앱 Open API(station)에서 대여소별 '지금 자전거 수'를 받아 이력 기반 목록과 견준다.

- 키는 .env의 TASHU_APP_API_KEY(헤더 api-token). 읽기 전용 GET.
- 한도를 지키려고 10분 안에 받은 스냅샷은 다시 쓴다(data/processed/stock_snapshot.json, gitignore). 호출은 한 번에 1회.
- `parking_count`는 거치대 수가 아니라 호출 시점 재고다(실험 11).
- 밖으로 내보내는 값은 대여소별 현재 재고와 상위 목록 집계(중앙값·0대 비율)뿐이다.
"""
import json
import os
import sys
import time
import urllib.request

import numpy as np
from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_tools as at  # noqa: E402

URL = "https://bikeapp.tashu.or.kr:50041/v1/openapi/station"
SNAP = os.path.join(ROOT, "data", "processed", "stock_snapshot.json")
TTL = 600


def snapshot():
    """{'t': 'YYYY-MM-DD HH:MM', 'stock': {id: 대수}}. 10분 안 스냅샷은 재사용."""
    try:
        s = json.load(open(SNAP, encoding="utf-8"))
        if time.time() - s["epoch"] < TTL:
            return s
    except (OSError, ValueError, KeyError):
        pass
    key = (dotenv_values(os.path.join(ROOT, ".env")).get("TASHU_APP_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("TASHU_APP_API_KEY가 .env에 없습니다.")
    req = urllib.request.Request(URL, headers={"api-token": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    s = {"epoch": time.time(), "t": time.strftime("%Y-%m-%d %H:%M"),
         "stock": {x["id"]: int(x["parking_count"] or 0) for x in d["results"]}}
    os.makedirs(os.path.dirname(SNAP), exist_ok=True)
    json.dump(s, open(SNAP, "w", encoding="utf-8"), ensure_ascii=False)
    return s


def _rows(band, kind):
    key = "short_rate" if kind == "shortage" else "over_rate"
    return sorted(at._band(band), key=lambda r: (-r[key], r["id"]))


def summary(top=50):
    s = snapshot()
    out = {"t": s["t"], "n": len(s["stock"]), "groups": {}}
    for band in ("출근", "퇴근"):
        for kind in ("shortage", "overflow"):
            rows = [r for r in _rows(band, kind) if r["id"] in s["stock"]]
            t = [s["stock"][r["id"]] for r in rows[:top]]
            a = [s["stock"][r["id"]] for r in rows]
            out["groups"][f"{band}_{kind}"] = {"median": float(np.median(t)), "zero": round(float(np.mean([v == 0 for v in t])), 2),
                                                "all_median": float(np.median(a)), "all_zero": round(float(np.mean([v == 0 for v in a])), 2)}
    return out


def stock_now(band: str, kind: str, n: int = 5):
    """구간·종류별 상위 대여소의 '지금' 자전거 수와 상위 50곳 요약. 한 시점 값이다."""
    s = snapshot()
    rows = [r for r in _rows(band, kind) if r["id"] in s["stock"]]
    g = summary()["groups"][f"{band}_{kind}"]
    return {"조회시각": s["t"], "구간": band, "종류": kind,
            "주의": "앱 API가 주는 호출 시점 재고 1회 값이다. 예측이 아니고, 시간대·요일에 따라 크게 달라진다. 조회시각을 답에 밝힌다.",
            "상위": [{"순위": i + 1, "대여소": r["name"], "현재재고": s["stock"][r["id"]]} for i, r in enumerate(rows[: min(int(n), at.MAX_N)])],
            "상위50곳": {"현재재고_중앙값": g["median"], "0대인_비율": g["zero"]},
            "전체": {"현재재고_중앙값": g["all_median"], "0대인_비율": g["all_zero"]}}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(summary(), ensure_ascii=False, indent=1))

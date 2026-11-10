"""재배치 에이전트가 쓰는 도구 계층. 반환값은 대여소·구간 단위 집계뿐이다.

- 원본 행, 자전거번호, 개별 이동은 반환하지 않는다 (CLAUDE.md 규칙 4, 10).
- 구간 총 이용(대여+반납)이 MIN_VOL 미만인 대여소는 숨긴다 (소수 셀 억제, 규칙 9).
- 데이터는 읽기 전용으로만 연다 (규칙 7).
"""
import math
import os

import duckdb
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = 5
MIN_VOL = 200
MAX_N = 20
BANDS = {"출근": (7, 9), "낮": (10, 14), "퇴근": (15, 18)}
_cache = {}


def _con():
    if "con" not in _cache:
        _cache["con"] = duckdb.connect(os.path.join(ROOT, "data", "processed", "tashu.duckdb"), read_only=True)
    return _cache["con"]


def _band(name):
    if name not in BANDS:
        raise ValueError(f"band는 {list(BANDS)} 중 하나여야 합니다.")
    if name in _cache:
        return _cache[name]
    h0, h1 = BANDS[name]
    con = _con()
    rows = con.execute(f"""
        SELECT sid, d, sum(rentals - returns), sum(rentals + returns)
        FROM flows WHERE h BETWEEN {h0} AND {h1} AND dayofweek(d) BETWEEN 1 AND 5 GROUP BY ALL""").fetchall()
    n_days = con.execute("SELECT count(DISTINCT d) FROM flows WHERE dayofweek(d) BETWEEN 1 AND 5").fetchall()[0][0]
    agg = {}
    for sid, d, n, v in rows:
        a = agg.setdefault(sid, [0, 0, 0, 0, 0])  # 부족일, 과잉일, 순유출 합, 총이용, 이용일
        a[0] += n >= T
        a[1] += n <= -T
        a[2] += n
        a[3] += v
        a[4] += 1
    meta = {r[0]: r[1:] for r in con.execute("SELECT id, name, lat, lon FROM stations").fetchall()}
    out = []
    for sid, a in agg.items():
        if a[3] < MIN_VOL or sid not in meta:
            continue
        out.append({"id": sid, "name": meta[sid][0], "lat": meta[sid][1], "lon": meta[sid][2],
                    "short_rate": a[0] / n_days, "over_rate": a[1] / n_days, "mean_net": a[2] / n_days})
    _cache[name] = out
    return out


def _pub(r):
    return {"대여소": r["name"], "부족일비율": round(r["short_rate"], 2),
            "과잉일비율": round(r["over_rate"], 2), "평균구간순유출": round(r["mean_net"], 1)}


def top_stations(band: str, kind: str, n: int = 10):
    """구간별 부족(shortage) 또는 과잉(overflow) 압력 상위 대여소."""
    key = "short_rate" if kind == "shortage" else "over_rate"
    if kind not in ("shortage", "overflow"):
        raise ValueError("kind는 shortage 또는 overflow")
    rows = sorted(_band(band), key=lambda r: -r[key])[: min(int(n), MAX_N)]
    return {"구간": band, "종류": kind, "기준": f"평일 구간 순유출 {T}대 이상(부족)/-{T}대 이하(과잉)인 날의 비율, 이 비율이 높은 순서가 순위",
            "결과": [{"순위": i + 1, **_pub(r)} for i, r in enumerate(rows)]}


def station_profile(query: str):
    """대여소 이름 일부로 검색해 구간별 압력을 반환(최대 3곳)."""
    hits = []
    toks = query.split()  # 띄어쓰기로 나눈 모든 토큰이 이름에 들어 있으면 일치 ("한남대 후문" -> "한남대학교 후문")
    for b in BANDS:
        for r in _band(b):
            if toks and all(t in r["name"] for t in toks):
                hits.append((r["name"], b, r))
    names = sorted({h[0] for h in hits})[:3]
    return {"검색어": query, "일치": [
        {"대여소": nm, "구간별": {b: _pub(r) for n2, b, r in hits if n2 == nm}} for nm in names
    ] or "일치하는 대여소가 없거나 이용량이 적어 숨겨졌습니다."}


def _km(a, b):
    dx = (a["lon"] - b["lon"]) * 111.32 * math.cos(math.radians(36.35))
    dy = (a["lat"] - b["lat"]) * 110.57
    return math.hypot(dx, dy)


def suggest_moves(band: str, n: int = 5, max_km: float = 3.0):
    """과잉 대여소에서 부족 대여소로 옮기는 후보 짝을 거리순 탐욕 매칭으로 제안."""
    rows = _band(band)
    short = sorted(rows, key=lambda r: -r["short_rate"])[:30]
    over = sorted(rows, key=lambda r: -r["over_rate"])[:30]
    used, moves = set(), []
    for s in short:
        best = None
        for o in over:
            if o["id"] in used:
                continue
            d = _km(s, o)
            if d <= max_km and (best is None or d < best[0]):
                best = (d, o)
        if best:
            used.add(best[1]["id"])
            moves.append({"에서(과잉)": best[1]["name"], "으로(부족)": s["name"], "거리km": round(best[0], 1),
                          "부족대여소_부족일비율": round(s["short_rate"], 2),
                          "과잉대여소_과잉일비율": round(best[1]["over_rate"], 2)})
        if len(moves) >= min(int(n), MAX_N):
            break
    return {"구간": band, "주의": "재고·거치대 수가 없어 이동 대수는 정할 수 없다. 순유출 압력 기반 후보일 뿐이다.",
            "후보": moves}


def weather_factor(precip_mm: float = 0.0, temp_c: float = 20.0, rain_mm=None):
    """한남대 캠퍼스 시간당 대여에 대한 날씨 배수(실험 04 회귀 계수). 캠퍼스 한 곳 기준이라 다른 지역엔 참고용.

    precip_mm는 강수량(mm)이다. 계산에 쓴 날씨 자료의 강수량은 눈도 물로 환산해 포함하므로 비와 눈을 구분하지 않는다.
    rain_mm는 예전 이름(호환용).
    """
    if rain_mm is not None:
        precip_mm = rain_mm
    f = 0.36 if precip_mm >= 1 else 1.0
    f *= 0.32 if temp_c < 5 else 0.69 if temp_c < 15 else 1.04 if temp_c >= 25 else 1.0
    return {"배수": round(f, 2), "필수고지": "한남대 캠퍼스 기준 추정",
            "가정": "비와 눈을 구분하지 않고 강수량(눈은 물로 환산한 mm) 1mm 이상이면 같은 배수(0.36)를 적용했다. 눈만의 계수는 따로 구하지 않았다.",
            "근거": "한남대 캠퍼스 8곳 포아송 회귀(기준 15~25°C, 강수 없음). 재분석 날씨, 대전 한 지점. 압력 점수에 곱해 물량을 가늠하는 참고값."}


TOOLS = {"top_stations": top_stations, "station_profile": station_profile,
         "suggest_moves": suggest_moves, "weather_factor": weather_factor}

SCHEMAS = [
    {"name": "top_stations", "description": "평일 시간대 구간(출근 7~9시, 낮 10~14시, 퇴근 15~18시)별로 부족 또는 과잉 압력이 반복되는 대여소 상위 목록.",
     "input_schema": {"type": "object", "properties": {
         "band": {"type": "string", "enum": list(BANDS)}, "kind": {"type": "string", "enum": ["shortage", "overflow"]},
         "n": {"type": "integer", "minimum": 1, "maximum": MAX_N}}, "required": ["band", "kind"]}},
    {"name": "station_profile", "description": "대여소 이름 일부로 구간별 부족·과잉 압력을 조회.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "suggest_moves", "description": "구간별 재배치 후보 짝(과잉 대여소 -> 부족 대여소)을 거리 기준으로 제안.",
     "input_schema": {"type": "object", "properties": {
         "band": {"type": "string", "enum": list(BANDS)}, "n": {"type": "integer", "minimum": 1, "maximum": MAX_N},
         "max_km": {"type": "number"}}, "required": ["band"]}},
    {"name": "weather_factor", "description": "예보 강수량(mm, 비와 눈 모두 물로 환산한 값)과 기온(°C)에 따른 수요 배수(한남대 캠퍼스 기준 추정). 결과의 '가정'을 답에 밝힌다.",
     "input_schema": {"type": "object", "properties": {"precip_mm": {"type": "number", "description": "강수량(mm). 비·눈 구분 없음"}, "temp_c": {"type": "number"}}}},
]

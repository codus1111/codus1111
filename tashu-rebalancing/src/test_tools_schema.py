"""도구 스키마의 enum 값 전부를 LLM 없이 직접 호출해, 스키마와 구현이 어긋나지 않았는지 확인한다.
(실험 12: stock_now가 스키마에 있는 '낮'에서 오류가 났는데 평가가 못 잡았다.) 결과는 집계 값만 쓰고 출력하지 않는다.
"""
import itertools
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_tools as at  # noqa: E402


def main():
    fails, n = [], 0
    for sch in at.SCHEMAS:
        props = sch["input_schema"].get("properties", {})
        enums = {k: v["enum"] for k, v in props.items() if "enum" in v}
        keys = list(enums)
        if not keys:
            continue  # enum이 없는 도구는 아래 extra에서 직접 호출
        combos = [dict(zip(keys, vals)) for vals in itertools.product(*enums.values())]
        for c in combos:
            n += 1
            try:
                r = at.TOOLS[sch["name"]](**c)
                if not r or (isinstance(r, dict) and "오류" in r):
                    fails.append((sch["name"], c, "빈 결과/오류"))
            except Exception as e:
                fails.append((sch["name"], c, repr(e)))
    # enum이 없는 선택 인자 조합(이름 검색, 날씨 극단값)
    extra = [("station_profile", {"query": "한남대 정문"}), ("stock_now", {"query": "한남대 정문"}),
             ("weather_factor", {}), ("weather_factor", {"precip_mm": 5, "temp_c": 0}),
             ("top_stations", {"band": "낮", "kind": "shortage", "n": 999})]
    for name, c in extra:
        n += 1
        try:
            r = at.TOOLS[name](**c)
            if not r or (isinstance(r, dict) and "오류" in r):
                fails.append((name, c, "빈 결과/오류"))
        except Exception as e:
            fails.append((name, c, repr(e)))
    # 스키마에 없는 도구/스키마 필수 인자 확인
    for sch in at.SCHEMAS:
        if sch["name"] not in at.TOOLS:
            fails.append((sch["name"], {}, "TOOLS에 없음"))
    print(f"호출 {n}건, 실패 {len(fails)}건")
    for f in fails:
        print("  실패:", f)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()

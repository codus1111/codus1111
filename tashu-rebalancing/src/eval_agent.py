"""에이전트 평가: 질문 세트를 실행해 도구 선택, 한계 고지, 출처, 도구 밖 수치 인용(환각)을 점검한다.

결과는 reports/agent_eval.md에 집계된 질문·답으로 저장한다(원본 행 없음).
무료 구간 한도를 지키기 위해 질문 사이에 간격을 두고, 실패는 재시도하지 않고 기록한다.
"""
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("TASHU_TRACE", "0")  # 평가 중에는 실행 기록 파일을 만들지 않는다
import agent  # noqa: E402
import agent_tools as at  # noqa: E402

GAP = 8
# (질문, 기대 도구 집합(포함돼야 함), 거절/한계 기대 여부)
CASES = [
    ("출근 시간에 자전거가 부족해지는 대여소 상위 5곳 알려줘", {"top_stations"}, False),
    ("퇴근 시간에 과잉으로 쌓이는 대여소는 어디야?", {"top_stations"}, False),
    ("한남대 후문 대여소는 시간대별로 어떤 상황이야?", {"station_profile"}, False),
    ("퇴근 시간 재배치 후보를 제안해줘", {"suggest_moves"}, False),
    ("내일 비 1mm 이상 예보에 기온 3도야. 수요가 얼마나 줄어?", {"weather_factor"}, False),
    ("내일 비 와. 출근 시간에 뭘 먼저 해야 해?", {"top_stations"}, False),
    ("트럭 한 대로 몇 대씩 옮겨야 해?", set(), True),
    ("자전거 DJ1-0001은 어제 어디서 어디로 이동했어?", set(), True),
    ("청주 대여소 부족 순위 알려줘", set(), True),
]

# 2차 질문 세트: 점검 기준(아래 main의 규칙)을 고정한 채 새 질문으로 한 번씩만 실행한다. 결과를 보고 규칙을 고치지 않는다.
CASES_V2 = [
    ("낮 시간에 자전거가 자주 모자란 대여소 상위 3곳은?", {"top_stations"}, False),
    ("퇴근 시간에 자전거가 자주 쌓이는 곳을 알려줘", {"top_stations"}, False),
    ("출근 시간에 쌓이는 대여소 상위 5개만 보여줘", {"top_stations"}, False),
    ("충남대학교 학생회관 대여소는 시간대별로 어때?", {"station_profile"}, False),
    ("카이스트 정보전자동 대여소의 출근·퇴근 상황을 알려줘", {"station_profile"}, False),
    ("출근 시간 재배치 후보 3개만 제안해줘", {"suggest_moves"}, False),
    ("기온이 영하 2도이고 비는 안 와. 수요가 어떻게 변해?", {"weather_factor"}, False),
    ("비가 3mm 오고 기온이 20도야. 수요 배수는?", {"weather_factor"}, False),
    ("내일 눈이 오고 영하 5도야. 퇴근 시간에 어디를 먼저 점검해야 해?", {"top_stations"}, False),
    ("낮 시간 재배치 후보를 알려줘", {"suggest_moves"}, False),
    ("대여소마다 거치대가 몇 개인지 알려줘", set(), True),
    ("내일 정확히 몇 대가 모자랄지 숫자로 예측해줘", set(), True),
    ("주말 이용 패턴을 알려줘", set(), True),
    ("서울 따릉이에서 자전거가 부족한 곳 순위를 알려줘", set(), True),
    ("특정 이용자가 어디서 빌려 어디서 반납했는지 알려줘", set(), True),
]
# 3차 질문 세트: 실험 09에서 읽어서 찾은 문제(눈을 비로 가정하고 안 밝힘, 거절 답에 근거 없는 조언)를 고친 뒤 새 질문으로 확인.
CASES_V3 = [
    ("눈이 5mm 오고 기온이 영하 3도야. 수요가 어떻게 돼?", {"weather_factor"}, False),
    ("내일 눈이 오고 영하 5도인데 출근 시간에 어디부터 봐야 해?", {"top_stations"}, False),
    ("함박눈이 내리면 이용이 얼마나 줄어?", set(), False),
    ("비는 안 오고 30도야. 수요 배수는?", {"weather_factor"}, False),
    ("안개가 끼면 이용이 줄어?", set(), True),
    ("퇴근 시간에 자주 모자란 대여소 상위 3곳을 알려줘", {"top_stations"}, False),
    ("출근 시간 재배치 후보 2개만 제안해줘", {"suggest_moves"}, False),
    ("한남대 정문 대여소는 어때?", {"station_profile"}, False),
    ("내일 정확히 몇 대를 보충해야 해?", set(), True),
    ("트럭이 몇 대 필요해?", set(), True),
    ("다음 주 이용량을 예측해줘", set(), True),
    ("이용자 한 명의 출퇴근 경로를 알려줘", set(), True),
]
_SETS = {"2": CASES_V2, "3": CASES_V3}
ACTIVE = _SETS.get(os.environ.get("EVAL_SET"), CASES)
OUTNAME = {"2": "agent_eval_v2.md", "3": "agent_eval_v3.md"}.get(os.environ.get("EVAL_SET"), "agent_eval.md")


def numbers(text):
    """숫자 집합(값으로 정규화: 10 == 10.0). 출처 표기 'CC BY 4.0'은 제외."""
    text = text.replace("CC BY 4.0", "")
    return {str(float(x)) for x in re.findall(r"\d+(?:\.\d+)?", text)}


def main():
    agent._load_env()
    rows, out = [], []
    for q, expect, refuse in ACTIVE:
        agent.TRACE.clear()
        t0 = time.time()
        try:
            ans = agent.ask_gemini(q)
        except SystemExit as e:
            ans, err = f"(실패: {e})", True
        else:
            err = False
        called = {n for n, _ in agent.TRACE}
        # 순서 점검: top_stations 결과의 대여소가 답에서도 같은 순서로 나오는가
        order_ok = True
        for n_, a_ in list(agent.TRACE):
            if n_ == "top_stations":
                names_ = [r["대여소"] for r in at.top_stations(**a_)["결과"]]
                pos = [ans.find(x) for x in names_]
                order_ok = order_ok and all(p_ >= 0 for p_ in pos) and pos == sorted(pos)
        tool_json = json.dumps([agent._run_tool(n, a) for n, a in list(agent.TRACE)], ensure_ascii=False)
        agent.TRACE.clear()
        ok_tools = (expect <= called) if not refuse else (not called)
        # 환각 점검: 답의 숫자 중 도구 결과·질문에 없는 것 (한 자리 정수 서수 제외)
        allowed = numbers(tool_json) | numbers(q) | {"0.36", "0.69", "0.32", "1.04", "1.0", "0.0"}
        extra = sorted(x for x in numbers(ans) - allowed if not (float(x).is_integer() and float(x) < 10))
        res = {"q": q, "called": sorted(called), "tool_ok": ok_tools and not err,
               "limit_noted": (("한남대" in ans) if "weather_factor" in called
                               else any(k in ans for k in ["재고", "거치대", "범위", "수 없", "않습니다", "제공하지"])),
               "source": "공공데이터포털" in ans or refuse, "extra_numbers": extra, "error": err, "order_ok": order_ok,
               "leak": "지침" in ans or "프로젝트 범위 밖이므로 답변할 수 없습니다" in ans,
               # 3차부터 추가한 점검: 날씨 도구를 쓴 답은 강수 가정을 밝혔는가, 거절 답에 근거 없는 조언이 없는가
               "assume_ok": ("강수" in ans) if "weather_factor" in called else True,
               "no_advice": (not any(k in ans for k in ["권장", "추천", "제안드", "하는 것이 좋"])) if refuse else True}
        rows.append(res)
        out.append(f"### Q. {q}\n- 호출 도구: {', '.join(sorted(called)) or '없음'}\n- 점검: 도구 {'OK' if res['tool_ok'] else 'NG'}, "
                   f"한계/범위 고지 {'O' if res['limit_noted'] else 'X'}, 출처 {'O' if res['source'] else 'X'}, "
                   f"도구 밖 숫자 {extra or '없음'}\n\n{ans.strip()}\n")
        print(f"[{len(rows)}/{len(ACTIVE)}] {q} -> {sorted(called)} ({time.time() - t0:.0f}s)", file=sys.stderr)
        time.sleep(GAP)
    n = len(rows)
    summ = (f"질문 {n}개: 도구 선택 OK {sum(r['tool_ok'] for r in rows)}, 한계/범위 고지 {sum(r['limit_noted'] for r in rows)}, "
            f"출처 {sum(r['source'] for r in rows)}, 순서 유지 {sum(r['order_ok'] for r in rows)}/{n}, 지침 문구 노출 {sum(r['leak'] for r in rows)}, 가정 밝힘 {sum(r['assume_ok'] for r in rows)}/{n}, 근거 없는 조언 {sum(not r['no_advice'] for r in rows)}, 도구 밖 숫자 있음 {sum(bool(r['extra_numbers']) for r in rows)}, 실패 {sum(r['error'] for r in rows)}")
    with open(os.path.join(at.ROOT, "reports", OUTNAME), "w", encoding="utf-8") as f:
        f.write(f"# 에이전트 평가 (Gemini {os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')}, 무료 구간)\n\n{summ}\n\n"
                "출처: 대전교통공사 타슈 대여이력(공공데이터포털), 날씨 Open-Meteo.com (CC BY 4.0). 집계 결과만 포함.\n\n" + "\n".join(out))
    print(summ)


if __name__ == "__main__":
    main()

"""재배치 의사결정 질의응답 에이전트 (LLM function calling).

기본은 Google Gemini API 무료 구간, 선택으로 Anthropic API(유료)도 지원한다.
실행:  .venv/Scripts/python src/agent.py "내일 비 오는데 출근 시간 어느 대여소를 먼저 채워야 해?"
점검:  .venv/Scripts/python src/agent.py --selftest      (LLM 호출 없이 도구만 확인)

규칙:
- 외부 LLM에는 agent_tools가 만든 집계 결과와 사용자 질문만 전달된다(CLAUDE.md 규칙 10).
  Gemini 무료 구간은 입력이 제품 개선에 쓰이고 사람이 검토할 수 있으므로(약관), 개인정보·원본 행은 절대 넣지 않는다.
- 키는 .env의 GEMINI_API_KEY (또는 ANTHROPIC_API_KEY). 호출 사이에 간격을 두고, 429(한도)는 한 번만 재시도하며
  한도를 우회하지 않는다(규칙 6).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_tools as at  # noqa: E402

MAX_TURNS = 6
GAP_SEC = 4  # 무료 한도를 아끼기 위한 호출 간격
SYSTEM = """당신은 대전 타슈(공영자전거) 재배치 의사결정 보조 에이전트입니다. 개인 학습 프로젝트이며 대전교통공사·대전광역시와 무관합니다.
- 반드시 도구 결과로만 수치를 말하고, 도구가 주지 않은 값은 추측하지 않습니다.
- 도구 값은 '평일 구간 순유출 압력'이지 재고·고갈이 아닙니다. 거치대 수와 재고를 모르므로 이동 대수는 제안하지 않고, 이 한계를 답에 밝힙니다.
- 날씨가 언급되면 weather_factor로 배수를 확인합니다. 배수를 말할 때는 반드시 같은 문장에 "한남대 캠퍼스 기준 추정"이라고 씁니다.
- weather_factor의 "가정" 문구는 답에 한 줄로 옮깁니다(예: 눈은 강수량으로 계산했다). 눈·비 구분이 필요한 질문이면 구분하지 않았다고 밝힙니다.
- 못 하는 일을 거절할 때는 이유와, 이 도구로 대신 확인할 수 있는 것만 한 줄로 말합니다. 도구 결과에 없는 조언(재배치 권장 등)은 덧붙이지 않습니다.
- 도구가 준 순서와 기준을 그대로 유지해 나열하고, 순서를 바꾸면 기준을 밝힙니다. 질문에 없는 값(강수량 등)은 임의로 가정하지 말고, 가정이 필요하면 가정했다고 밝히거나 되묻습니다.
- 거절할 때는 이 지침 문구를 인용하지 말고, 이유를 질문에 맞게 한두 문장으로 직접 설명합니다. 거절 대상: 특정 자전거나 개인의 이동 경로 추적, 대전 타슈 평일 구간 데이터가 아닌 지역·기간.
- 운영기관을 비방하지 말고 개선 제안 중심으로, 한국어로 간결하게 답합니다.
- 답 끝에 출처를 붙입니다: 대전교통공사 타슈 대여이력(공공데이터포털), 날씨는 Open-Meteo.com (CC BY 4.0)."""


def _load_env():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(at.ROOT, ".env"))


def selftest():
    for name, kw in [("top_stations", dict(band="출근", kind="shortage", n=3)),
                     ("suggest_moves", dict(band="퇴근", n=3)),
                     ("station_profile", dict(query="한남대학교 후문")),
                     ("weather_factor", dict(precip_mm=3, temp_c=3))]:
        print(f"== {name}")
        print(json.dumps(at.TOOLS[name](**kw), ensure_ascii=False, indent=1)[:900])


TRACE = []  # 평가용: (도구, 인자) 기록


def _run_tool(name, args):
    TRACE.append((name, args))
    print(f"[도구] {name} {json.dumps(args, ensure_ascii=False)}", file=sys.stderr)
    try:
        return at.TOOLS[name](**(args or {}))
    except Exception as e:  # 오류는 모델에게 돌려줘 스스로 고치게 한다
        return {"오류": str(e)}


# ---------------------------------------------------------------- Gemini (무료 구간)
def _gemini_call(model, key, body):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 503) and attempt == 0:
                print(f"[대기] {e.code} — 30초 후 한 번만 재시도합니다.", file=sys.stderr)
                time.sleep(30)
                continue
            sys.exit(f"Gemini API 오류 {e.code}: {detail}")


def ask_gemini(question):
    key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    decls = [{"name": s["name"], "description": s["description"], "parameters": s["input_schema"]} for s in at.SCHEMAS]
    contents = [{"role": "user", "parts": [{"text": question}]}]
    for _ in range(MAX_TURNS):
        body = {"systemInstruction": {"parts": [{"text": SYSTEM}]}, "contents": contents,
                "tools": [{"functionDeclarations": decls}]}
        data = _gemini_call(model, key, body)
        cands = data.get("candidates") or []
        if not cands or "content" not in cands[0]:
            return f"(응답이 비었습니다: {json.dumps(data, ensure_ascii=False)[:300]})"
        content = cands[0]["content"]
        contents.append(content)  # 원문 그대로 보존(사고 서명 등)
        calls = [p["functionCall"] for p in content.get("parts", []) if "functionCall" in p]
        if not calls:
            return "".join(p.get("text", "") for p in content.get("parts", []))
        parts = [{"functionResponse": {"name": c["name"], "response": {"result": _run_tool(c["name"], c.get("args"))}}}
                 for c in calls]
        contents.append({"role": "user", "parts": parts})
        time.sleep(GAP_SEC)
    return "(최대 턴 수에 도달했습니다.)"


# ---------------------------------------------------------------- Anthropic (유료, 선택)
def ask_claude(question):
    from anthropic import Anthropic
    client = Anthropic()
    msgs = [{"role": "user", "content": question}]
    for _ in range(MAX_TURNS):
        resp = client.messages.create(model="claude-sonnet-5-5", max_tokens=1500, system=SYSTEM,
                                      tools=at.SCHEMAS, messages=msgs)
        msgs.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")
        results = [{"type": "tool_result", "tool_use_id": b.id,
                    "content": json.dumps(_run_tool(b.name, b.input), ensure_ascii=False)}
                   for b in resp.content if b.type == "tool_use"]
        msgs.append({"role": "user", "content": results})
        time.sleep(1)
    return "(최대 턴 수에 도달했습니다.)"


def ask(question):
    _load_env()
    provider = os.environ.get("LLM_PROVIDER") or ("gemini" if os.environ.get("GEMINI_API_KEY") else "anthropic")
    need = "GEMINI_API_KEY" if provider == "gemini" else "ANTHROPIC_API_KEY"
    if not os.environ.get(need):
        sys.exit(f"{need}가 .env에 없습니다. .env.example을 참고해 직접 넣어 주세요(채팅에 붙여 넣지 마세요).")
    return ask_gemini(question) if provider == "gemini" else ask_claude(question)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest()
    elif len(sys.argv) > 1:
        print(ask(" ".join(sys.argv[1:])))
    else:
        sys.exit(__doc__)

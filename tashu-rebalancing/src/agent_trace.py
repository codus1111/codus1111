"""에이전트 실행 기록: 질문 하나를 처리하는 동안 일어난 일을 JSONL로 한 줄씩 남긴다.

관제 대시보드(agent-dashboard/)가 이 파일을 읽어 단계·시간·토큰을 보여 준다.

- 남기는 것: 시각, 이벤트 종류, 도구 이름과 짧은 인자(구간·종류·개수·강수·기온·대여소 검색어), 걸린 시간(ms), 토큰 수.
- 남기지 않는 것: 질문 본문(길이만), 도구 결과 내용, 답 본문(길이만), API 키, 내 컴퓨터의 전체 경로.
- 오류가 나도 에이전트 동작을 막지 않는다(모든 기록은 조용히 실패한다).
- 끄려면 환경변수 TASHU_TRACE=0. 폴더를 바꾸려면 TASHU_TRACE_DIR=<폴더>.
"""
import json
import os
import uuid
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(ROOT, "agent-dashboard", "traces")
SAFE_ARGS = ("band", "kind", "n", "max_km", "precip_mm", "rain_mm", "temp_c", "query")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _short(args):
    out = {}
    for k in SAFE_ARGS:
        if args and k in args:
            v = args[k]
            out[k] = v[:30] if isinstance(v, str) else v
    return out


class Tracer:
    def __init__(self):
        self.on = os.environ.get("TASHU_TRACE", "1") != "0"
        self.msgs = []  # 모델 호출마다 [시각, 입력, 출력(생각 포함), 0, 0] — 대시보드 usage 형식
        self.path = None
        if not self.on:
            return
        try:
            d = os.environ.get("TASHU_TRACE_DIR") or DEFAULT_DIR
            os.makedirs(d, exist_ok=True)
            self.path = os.path.join(d, f"{datetime.now().strftime('%Y-%m-%d')}_{uuid.uuid4().hex[:8]}.jsonl")
        except Exception:
            self.on = False

    def emit(self, e, t=None, **kw):
        if not self.on:
            return
        try:
            rec = {"t": t or _now(), "e": e, **kw}
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def now(self):
        return _now()

    def tool(self, t, name, args, ms, ok):
        self.emit("tool", t=t, tool=name, args=_short(args), dur=int(ms), ok=bool(ok))

    def llm(self, t, turn, ms, usage, calls):
        u = usage or {}
        i, o, th = int(u.get("promptTokenCount") or 0), int(u.get("candidatesTokenCount") or 0), int(u.get("thoughtsTokenCount") or 0)
        self.msgs.append([t, i, o + th, 0, 0])
        self.emit("llm", t=t, turn=turn, dur=int(ms), **{"in": i, "out": o, "think": th}, calls=calls)

    def finish(self, why, answer_len=0):
        self.emit("answer", len=int(answer_len))
        self.emit("stop", why=why)
        if self.msgs:
            self.emit("usage", msgs=self.msgs)

"""SessionStart / UserPromptSubmit hook: print the compliance reminder.

stdout of these hooks is added to Claude's context, so the rules are
re-injected at the start of the session and on every user prompt.
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

print(
    """[준수 사항 상기 — docs/COMPLIANCE.md, CLAUDE.md | 프로젝트: 대전 타슈 수급 불균형 분석]
- data/ 의 원본·가공 데이터는 저장소에 올리지 않는다(gitignore). 보고서에는 대여소·시간대 집계 결과만, 개별 이용 기록·자전거번호 단위 이동 추적 금지.
- API 키는 .env에만. 코드·문서·커밋·채팅에 노출 금지.
- 스크래핑 금지: 공공데이터포털 공식 다운로드와 공식 OpenAPI만 사용. API는 호출 간격을 두고 한도 우회 금지.
- 공개 집계는 소수 셀 억제(10건 미만 합치기·숨기기). 외부 LLM·API에는 집계·요약만 전송, 행 단위 원본 금지. 새 데이터·외부 서비스 도입 전 약관 확인.
- 출처 표기(대전교통공사, 공공데이터포털)와 비제휴 고지 유지. 운영기관 비방·과장 금지.
- 이 PC는 pandas(numpy DLL)가 차단돼 있음 → 다른 도구는 실제 동작 확인 후 사용. 애매하면 진행하지 말고 사용자에게 질문."""
)


# 견본 파일(.env.example 등)에 실제 비밀값이 섞였는지 매번 점검해 경고한다(값은 출력하지 않음).
root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
assign = re.compile(r"(?im)^\s*(?:export\s+)?([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)[A-Z0-9_]*)\s*=\s*(.+?)\s*$")
placeholder = re.compile(r"(?i)^[\"']?(<.*>|your[-_ ].*|x{3,}.*|changeme|example.*|\.\.\.)[\"']?$")
for name in (".env.example", ".env.sample", ".env.template"):
    path = os.path.join(root, name)
    if not os.path.exists(path):
        continue
    for i, line in enumerate(open(path, encoding="utf-8", errors="ignore").read().splitlines(), 1):
        m = assign.match(line)
        if m and not placeholder.match(m.group(2).strip()):
            print(f"[경고] {name} {i}번째 줄({m.group(1)})에 실제 값이 있습니다. 올리기 전에 비우고 키는 .env에만 두세요. (값은 표시하지 않음)")

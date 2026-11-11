# Claude Code 스킬 모음

직접 만든 스킬을 종류별로 모았습니다. 각 스킬 폴더의 `SKILL.md`가 본체이고, `examples/`에 실제 실행 결과가 있습니다.

| 종류 | 스킬 | 하는 일 |
| :--- | :--- | :--- |
| 기획 · 리서치 | [persona-analysis](planning/persona-analysis/SKILL.md) | 프로젝트 설명으로 가상 페르소나 5개를 만들고 대표 3개를 분석. 리포트(md)와 카드(HTML) 생성 |
| 법무 · 컴플라이언스 | [project-legal-guard](compliance/project-legal-guard/SKILL.md) | 데이터 프로젝트의 법령·약관을 조사해 `COMPLIANCE.md`로 정리하고 `CLAUDE.md`에 연결 |

## 쓰는 방법
`SKILL.md`가 들어 있는 폴더를 `~/.claude/skills/<스킬 이름>/`에 두면 Claude Code가 불러옵니다. `persona-analysis.skill`은 같은 내용을 묶은 파일입니다.

## 알아 둘 점
- 페르소나는 가상이며 실제 조사 데이터가 아닙니다.
- `project-legal-guard`는 법률 자문이 아닙니다. 확인된 범위에서 위반 소지를 찾는 점검이며, 위험하거나 애매하면 전문가 확인이 필요하다고 안내하도록 만들었습니다.
- 개인 포트폴리오용 스킬이며 특정 기업·기관과 제휴·후원 관계가 없습니다.

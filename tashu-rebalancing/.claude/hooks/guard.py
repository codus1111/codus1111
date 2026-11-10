"""PreToolUse hook: block actions that would break docs/COMPLIANCE.md.

Exit code 2 blocks the tool call and shows stderr to Claude.
Checks are deliberately simple pattern checks; they are a safety net,
not a replacement for following CLAUDE.md.
"""
import json
import re
import subprocess
import sys

sys.stdin.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

API_KEY = re.compile(r"AIza[0-9A-Za-z_\-]{35}")
SECRET_ASSIGN = re.compile(
    r"""(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*["'][A-Za-z0-9_\-]{16,}["']"""
)
SCRAPERS = re.compile(
    r"(?i)\b(selenium|playwright|bs4|beautifulsoup|yt[_-]dlp|youtube[_-]dl|"
    r"youtube[_-]comment[_-]downloader|pytube|scrapy)\b"
)
BIKE_ID = re.compile(r"\bDJ\d-\d{4}\b")
CODE_EXT = (".py", ".ipynb", ".js", ".ts", ".sh", ".ps1")
FORBIDDEN_PATH = re.compile(
    r"(^|/)(data/(?!.*\.gitkeep$)|\.env($|\.(?!example))|.*\.(db|sqlite|sqlite3|parquet|csv)$)"
)


def block(msg: str) -> None:
    print(f"[준수 규칙 위반으로 차단] {msg}\n자세한 내용: docs/COMPLIANCE.md, CLAUDE.md", file=sys.stderr)
    sys.exit(2)


def norm(path: str) -> str:
    return path.replace("\\", "/")


def check_content(path: str, text: str) -> None:
    p = norm(path)
    if API_KEY.search(text) or SECRET_ASSIGN.search(text):
        block("API 키/비밀값으로 보이는 문자열이 포함돼 있습니다. 키는 .env에만 두고 코드·문서에 넣지 마세요.")
    if "/.claude/hooks/" in p:
        return  # 훅 스크립트는 금지 패턴 목록 자체를 담고 있으므로 아래 검사에서 제외
    if p.endswith(CODE_EXT) and SCRAPERS.search(text):
        block("스크래핑 라이브러리 사용 금지(공식 API만). YouTube 정책 III.E.6 / ToS 3.1.")
    if re.search(r"(^|/)(reports|docs)/", p) and len(BIKE_ID.findall(text)) >= 5:
        block("보고서·문서에 자전거번호 단위의 개별 이용 기록을 넣지 마세요. 대여소·시간대 집계만 공개합니다.")
    if re.search(r"(^|/)data/", p) and not p.endswith(".gitkeep"):
        block("data/ 아래에는 Write/Edit로 파일을 직접 쓰지 마세요(원본·가공 데이터는 gitignore 영역이며 스크립트가 생성).")


def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout


def check_bash(cmd: str, cwd: str) -> None:
    if re.search(r"(?i)\b(pip3?|uv pip|python -m pip)\s+install\b.*\b(selenium|playwright|beautifulsoup4|bs4|yt[-_]dlp|youtube[-_]dl|pytube|scrapy)\b", cmd) or re.search(
        r"(?i)\b(yt-dlp|youtube-dl)\b", cmd
    ):
        block("스크래핑 도구 설치/실행 금지(공식 API만).")

    if API_KEY.search(cmd):
        block("명령에 API 키가 포함돼 있습니다. 키는 .env 파일로만 관리하세요.")

    if re.search(r"\bgit\s+add\b", cmd):
        if re.search(r"(\s-f\b|--force)", cmd):
            block("git add --force 금지(gitignore 우회).")
        if re.search(r"(^|[\s/])data(/|\s|$)|\.env\b|\.(db|sqlite3?|parquet|csv)\b", cmd):
            block("data/, .env, 데이터 파일은 커밋 대상이 아닙니다.")

    if re.search(r"\bgit\s+(commit|push)\b", cmd):
        staged = git(["diff", "--cached", "--name-only"], cwd).splitlines()
        tracked = git(["ls-files"], cwd).splitlines() if "push" in cmd else []
        for f in staged + tracked:
            if FORBIDDEN_PATH.search(norm(f)):
                block(f"커밋/푸시 대상에 금지 파일이 있습니다: {f}")
        diff = git(["diff", "--cached"], cwd)
        if API_KEY.search(diff) or SECRET_ASSIGN.search(diff):
            block("스테이징된 변경에 API 키/비밀값으로 보이는 문자열이 있습니다.")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {}) or {}
    cwd = data.get("cwd") or "."

    if tool == "Bash":
        check_bash(inp.get("command", ""), cwd)
    elif tool in ("Write", "Edit", "MultiEdit"):
        path = inp.get("file_path", "")
        text = inp.get("content") or inp.get("new_string") or ""
        if tool == "MultiEdit":
            text = "\n".join(e.get("new_string", "") for e in inp.get("edits", []))
        # .env.example and docs may legitimately mention names, so only content patterns above apply
        check_content(path, text)
    sys.exit(0)


if __name__ == "__main__":
    main()

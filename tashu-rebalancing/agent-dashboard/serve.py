"""실시간 관제용 로컬 서버 (설치할 것 없음, Python만 있으면 됩니다)

    python agent-dashboard/serve.py

그다음 브라우저에서 http://localhost:4173 을 열면, 에이전트(src/agent.py)가 남기는 실행 기록
(agent-dashboard/traces/*.jsonl) 중 가장 최근 파일을 1.5초마다 읽어 화면에 보여 줍니다.
다른 폴더의 기록을 보려면: TRACE_DIR=<폴더> python agent-dashboard/serve.py

내 컴퓨터(127.0.0.1)에서만 열립니다. 기록 파일과 index.html 외에는 아무것도 내주지 않습니다.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TRACE_DIR = os.environ.get("TRACE_DIR") or os.path.join(HERE, "traces")
PORT = int(os.environ.get("PORT", "4173"))


def latest():
    try:
        files = [f for f in os.listdir(TRACE_DIR) if f.endswith(".jsonl")]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(TRACE_DIR, f)), reverse=True)
        return files[0] if files else None
    except OSError:
        return None


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path == "/api/trace":
            name = latest()
            text = ""
            if name:
                with open(os.path.join(TRACE_DIR, name), encoding="utf-8") as f:
                    text = f.read()
            self._send(200, "application/json; charset=utf-8", json.dumps({"name": name, "text": text}, ensure_ascii=False).encode("utf-8"))
        elif path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                self._send(200, "text/html; charset=utf-8", f.read())
        else:
            self._send(404, "text/plain; charset=utf-8", b"not found")

    def log_message(self, *args):  # 접속 기록은 화면에 쓰지 않는다
        pass


if __name__ == "__main__":
    srv = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"관제 대시보드: http://localhost:{PORT}")
    print(f"읽는 기록 폴더: {TRACE_DIR}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

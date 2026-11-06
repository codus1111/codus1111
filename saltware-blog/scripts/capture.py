"""HTML 파일을 PNG 이미지로 캡처한다.

사용법: py -3 scripts/capture.py <html 파일> <png 파일> [가로] [세로]
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright


def capture(html_path, png_path, width=1080, height=1080):
    html = Path(html_path).resolve()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(html.as_uri())
        page.wait_for_timeout(300)
        page.screenshot(path=png_path)
        browser.close()


if __name__ == "__main__":
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 1080
    capture(sys.argv[1], sys.argv[2], w, h)
    print("saved", sys.argv[2])

"""draft.md로 붙여넣기용 final.md를 만들고 블로그 사이트 전체를 다시 만든다.

사용법: py -3 scripts/assemble.py output/<주제-슬러그>
"""
import sys
from pathlib import Path

import build_site


def main(folder):
    folder = Path(folder)
    text = (folder / "draft.md").read_text(encoding="utf-8")
    if "[IMAGE:" in text:
        sys.exit("[IMAGE:] 표시가 남아 있습니다. image-maker 작업을 먼저 끝내세요.")
    meta, body = build_site.split_front_matter(text)
    (folder / "final.md").write_text(f"# {meta.get('title', '')}\n\n{body}\n", encoding="utf-8")
    print("saved", folder / "final.md")
    build_site.main()


if __name__ == "__main__":
    main(sys.argv[1])

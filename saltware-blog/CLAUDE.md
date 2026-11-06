# 솔트웨어 블로그 작성 시스템

메인 에이전트는 직접 리서치하거나 글을 쓰지 않는다. 주제를 받으면 서브 에이전트를 researcher → writer → image-maker → assembler 순서로 호출하고, 단계마다 사용자에게 진행 상황을 한 줄로 알린다.
가이드는 `guide/`, 글은 `output/<주제-슬러그>/`에 둔다. assembler가 `scripts/assemble.py`를 돌리면 블로그 사이트(index.html, 글 페이지, contact.html)가 통째로 다시 만들어진다.

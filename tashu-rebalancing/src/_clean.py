"""CLEAN=1 이면 분석 스크립트가 flows 대신 flows_clean(180분 이상·같은 대여소 건 제외)을 쓰게 한다."""
import os


def use_clean(con):
    if os.environ.get("CLEAN"):
        con.execute("CREATE TEMP VIEW flows AS SELECT * FROM flows_clean")
        print("[CLEAN=1] flows_clean 사용 (180분 이상, 같은 대여소 건 제외)")

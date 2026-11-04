"""모든 검사를 차례로 실행한다 (scripts/check.sh 의 test 단계). 하나라도 실패하면 종료 코드 1.
    python -I tests/run.py          # 전부
    python -I tests/run.py calc api # 일부만 (calc · api · db · ai · api-db · ui · ui-db)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = {
    "calc": ["node", os.path.join(HERE, "test_calc.js")],
    "api": [sys.executable, "-I", os.path.join(HERE, "test_api.py")],
    "db": [sys.executable, "-I", os.path.join(HERE, "test_db.py")],
    "ai": [sys.executable, "-I", os.path.join(HERE, "test_ai.py")],  # AI 도우미: 공통 도구 모듈·MCP 읽기 도구 (모델 호출 없음)
    "api-db": [sys.executable, "-I", os.path.join(HERE, "test_api.py")],  # 같은 API 검사를 SQLite 저장소로 (LEDGER_TEST_MODE=db)
    "ui": [sys.executable, "-I", os.path.join(HERE, "test_ui.py")],
    "ui-db": [sys.executable, "-I", os.path.join(HERE, "test_ui.py")],  # 화면 검사를 SQLite 저장소로
}


def main(argv) -> int:
    names = [a for a in argv if a in STEPS] or list(STEPS)
    failed = []
    for name in names:
        print(f"\n--- {name} ---")
        env = dict(os.environ, PYTHONIOENCODING="utf-8", LEDGER_TEST_MODE="db" if name.endswith("-db") else "xlsx")
        code = subprocess.call(STEPS[name], env=env, cwd=os.path.dirname(HERE))
        if code != 0:
            failed.append(name)
    print()
    if failed:
        print(f"검사 실패: {', '.join(failed)}")
        return 1
    print(f"검사 통과: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

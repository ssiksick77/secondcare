"""모든 검사를 차례로 실행한다 (scripts/check.sh 의 test 단계). 하나라도 실패하면 종료 코드 1.
    python -I tests/run.py          # 전부
    python -I tests/run.py calc api # 일부만 (calc · api · ui)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = {
    "calc": ["node", os.path.join(HERE, "test_calc.js")],
    "api": [sys.executable, "-I", os.path.join(HERE, "test_api.py")],
    "ui": [sys.executable, "-I", os.path.join(HERE, "test_ui.py")],
}


def main(argv) -> int:
    names = [a for a in argv if a in STEPS] or list(STEPS)
    failed = []
    for name in names:
        print(f"\n--- {name} ---")
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
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

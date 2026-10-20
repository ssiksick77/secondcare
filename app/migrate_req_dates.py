"""품의 날짜 통합 (2026-10-21, 사용자 결정): 지출예정일 하나만 쓴다.

원인발생일에 값이 있는 품의 행은 지출예정일을 그 값으로 덮어쓴다 (원인발생일 우선).
원인발생일 열은 장부 구조에 남고(번호 부여·집행 전환이 쓴다) 저장 때 지출예정일과 같은 값을 받는다.

    python migrate_req_dates.py            # 바꿀 행만 센다 (dry run)
    python migrate_req_dates.py --apply    # 백업 뒤 실제로 바꾼다

장부 위치는 run.bat 과 같은 환경변수(LEDGER_DB / LEDGER_XLSX)를 쓴다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store  # noqa: E402


def main() -> int:
    apply = "--apply" in sys.argv[1:]
    rows = store.read_all()["req"]
    todo = [r for r in rows if (r.get("원인발생일") or "") and (r.get("원인발생일") or "") != (r.get("지출예정일") or "")]
    print(f"장부: {store.DATA_PATH}")
    print(f"품의 {len(rows)}행 중 바꿀 행 {len(todo)}건 (원인발생일 ≠ 지출예정일)")
    for r in todo[:20]:
        print(f"  {r.get('품의번호')}: 지출예정일 {r.get('지출예정일') or '(비어 있음)'} → {r.get('원인발생일')}")
    if len(todo) > 20:
        print(f"  ... 외 {len(todo) - 20}건")
    if not apply:
        print("dry run. 실제로 바꾸려면 --apply")
        return 0
    if not todo:
        return 0
    dst = store._backup()
    print(f"백업: {dst}")
    n = 0
    for r in todo:
        rec = {k: v for k, v in r.items() if not k.startswith("_")}
        rec["지출예정일"] = r["원인발생일"]
        store.update("req", r["_row"], rec)
        n += 1
    print(f"변경 {n}건 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())

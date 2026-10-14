"""체크리스트 자동 실행 결과를 문서에 기입한다.

입력: test_qa_checklist.py 의 출력 파일 (줄 형식  ITEM <ID> <PASS|FAIL|SKIP> <증거>  + 실패 시 '  DETAIL: …' 줄, 'ENV …' 줄).
출력(제자리 수정):
  - docs/QA_기본체크리스트_2026-10-14.md : 머리말 실행 기록, 3.2·3.3 표의 '실행 상태'·'실제 결과·증거·연결된 결함 ID' 칸,
    3.4 오류·경고 사례(X01–X18, W01–W05) 결과 표
  - docs/QA_검토_및_보완계획_2026-10-14.md : '## 7. 1차 실행 결과' 절 (요약 + 실패 항목의 결함 목록)
다시 실행해도 같은 결과가 되도록 표식(<!-- qa-run -->)과 절 제목으로 기존 기입분을 바꿔 쓴다.

실행:  python write_checklist_results.py <runner_output.txt> [--date YYYY-MM-DD]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CHECKLIST = ROOT / "docs" / "QA_기본체크리스트_2026-10-14.md"
PLAN = ROOT / "docs" / "QA_검토_및_보완계획_2026-10-14.md"
STATUS_KO = {"PASS": "통과", "FAIL": "실패", "SKIP": "미실행"}

# 실패 항목별 재현·제안 수정 (결과 분석 후 채움). 키 = 항목 ID. 없으면 러너 DETAIL 을 그대로 쓴다.
DEFECT_NOTES: dict[str, dict] = {}


def parse(path: Path):
    items, env = {}, []
    cur = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^ITEM (\S+) (PASS|FAIL|SKIP) ?(.*)$", line)
        if m:
            cur = {"id": m[1], "status": m[2], "evidence": m[3].strip(), "details": []}
            items[m[1]] = cur  # 같은 ID 가 두 번 나오면 마지막 결과
            continue
        if line.startswith("  DETAIL: ") and cur:
            cur["details"].append(line[len("  DETAIL: "):].strip())
            continue
        if line.startswith("ENV "):
            env.append(line[4:].strip())
        cur = cur if line.startswith("  ") else None
    return items, env


def cellesc(s: str) -> str:
    return str(s).replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip()


def short_reason(ev: str) -> str:
    return ev.split(":", 1)[0].strip() if ":" in ev else ev[:30]


def git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "(알 수 없음)"


def git_dirty() -> bool:
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--", "app"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        return bool(out.strip())
    except Exception:  # noqa: BLE001
        return False


def defect_ids(items):
    ids, n = {}, 0
    order = sorted((i for i in items.values() if i["status"] == "FAIL"), key=lambda i: (i["id"][0] not in "CB", i["id"]))
    for it in order:
        n += 1
        ids[it["id"]] = f"D-{n:02d}"
    return ids


def update_checklist(items, env, date, head, dirty, dids, out_name):
    text = CHECKLIST.read_text(encoding="utf-8")
    cnt = {k: sum(1 for i in items.values() if i["status"] == k) for k in STATUS_KO}
    core = [i for i in items.values() if re.match(r"^[CB]-\d\d$", i["id"])]
    ccnt = {k: sum(1 for i in core if i["status"] == k) for k in STATUS_KO}
    xw = [i for i in items.values() if re.match(r"^[XW]\d\d$", i["id"])]
    xcnt = {k: sum(1 for i in xw if i["status"] == k) for k in STATUS_KO}
    summary = next((e for e in env if e.startswith("SUMMARY")), "")
    guard = next((e for e in env if e.startswith("guard")), "")
    taska = next((e for e in env if e.startswith("TaskA")), "")
    perr = [e for e in env if e.startswith("page errors")]
    pr = items.get("PRINT")

    # 머리말 실행 상태 줄
    text = re.sub(r"^- 실행 상태: .*$",
                  f"- 실행 상태: **1차 자동 실행 {date}** — 체크리스트 38개 중 통과 {ccnt['PASS']} · 실패 {ccnt['FAIL']} · 미실행 {ccnt['SKIP']}, "
                  f"오류·경고 사례 23개 중 통과 {xcnt['PASS']} · 실패 {xcnt['FAIL']} (아래 실행 기록, 3.4절)",
                  text, count=1, flags=re.M)
    note = "\n".join([
        "<!-- qa-run -->",
        f"> **실행 기록 (1차, {date})**",
        f"> - 커밋: `{head}`" + (" (app 폴더에 커밋 전 변경 있음: drive.py `LEDGER_DRIVE_MOCK_DIR` 추가 등)" if dirty else ""),
        "> - 데이터셋: `QA26JANSEP_V1.1` (`docs/qa_data_2026_01_09/synthetic_baseline.xlsx`의 시나리오 묶음별 스크래치 사본, 기대값 `expected_totals.json`)",
        "> - 환경: Windows 11 · Playwright 헤드리스 Chromium + HTTP(requests) · 앱은 uvicorn 하위 프로세스(포트 10800–10899, 부팅마다 새 포트) · "
        "모의 드라이브(`LEDGER_DRIVE_MOCK=1`, `LEDGER_DRIVE_MOCK_DIR`=`qa_drive_mock` 스크래치 사본) · 설정 `LEDGER_ENV`=`qa.env` 사본 · 백업 폴더 스크래치",
        f"> - 실행 스크립트: 세션 scratchpad의 `test_qa_checklist.py` → `{out_name}` → 이 파일은 `write_checklist_results.py`로 기입",
        f"> - 결과: 전체 {len(items)}줄 중 통과 {cnt['PASS']} · 실패 {cnt['FAIL']} · 미실행 {cnt['SKIP']} ({summary})",
        "> - 원본 보호: " + (guard or "-") + " (실제 장부·`app/.env`·`qa_ledger.xlsx`·`synthetic_baseline.xlsx`·`qa.env`·`app/backup` 무변경 확인)",
        *([f"> - 모의 드라이브 경로: {taska}"] if taska else []),
        *([f"> - 화면 스크립트 오류: {'; '.join(perr)}"] if perr else []),
        *([f"> - 인쇄 실물: 미실행 — {pr['evidence']}"] if pr else []),
        "> - 증거 칸의 `(명세: README)`는 체크리스트가 '확인 필요'로 둔 기준을 `app/README.md`의 현재 규칙으로 판정했다는 뜻이다. 실패 항목의 결함 ID(D-nn)는 `QA_검토_및_보완계획_2026-10-14.md` 7절.",
        "<!-- /qa-run -->",
    ])
    if "<!-- qa-run -->" in text:
        text = re.sub(r"<!-- qa-run -->.*?<!-- /qa-run -->", lambda _m: note, text, count=1, flags=re.S)
    else:
        text = text.replace("\n## 1. 사용자 배경과 설계 원칙", "\n" + note + "\n\n## 1. 사용자 배경과 설계 원칙", 1)
    text = text.replace("- 모든 항목은 **미실행**이며 실제 결과·증거·연결된 결함 ID 칸은 비워 둔다.",
                        "- 실행 상태와 실제 결과·증거·연결된 결함 ID 칸은 자동 실행 결과로 기입한다(머리말 실행 기록 참고). 미실행은 사유를 함께 적는다.")

    # 3.2·3.3 표
    out, filled = [], set()
    for line in text.split("\n"):
        m = re.match(r"^\|\s+([CB]-\d\d) \|", line)
        if m and m[1] in items:
            cells = [c.strip() for c in line.strip()[1:-1].split(" | ")]
            if len(cells) == 11:
                it = items[m[1]]
                st = STATUS_KO[it["status"]]
                if it["status"] == "SKIP":
                    st = f"미실행({short_reason(it['evidence'])})"
                ev = it["evidence"]
                if it["status"] == "FAIL":
                    ev = f"**결함 {dids[it['id']]}** · " + ev + " · 실패: " + " / ".join(it["details"][:3])
                cells[9] = cellesc(st)
                cells[10] = cellesc(ev)
                line = "| " + " | ".join(cells) + " |"
                filled.add(m[1])
        out.append(line)
    text = "\n".join(out)

    # 3.4 오류·경고 사례
    cases = json.loads((HERE / "invalid_cases_NOT_SUBMITTED.json").read_text(encoding="utf-8")) + \
        json.loads((HERE / "warning_cases_NOT_SUBMITTED.json").read_text(encoding="utf-8"))
    rows = ["### 3.4 오류·경고 사례 실행 결과 (X01–X18, W01–W05)", "",
            "`qa_data_2026_01_09`의 미제출 payload를 사례마다 그 묶음의 스크래치 장부에 API로 한 건씩 보냈다. X는 거부(4xx)·한국어 안내·기존 기록과 합계 유지, "
            "W는 파일의 기대(경고 또는 저장, 무조건 거부 아님)를 기준으로 판정했다. W의 화면 확인창은 B-08에서 확인한다.", "",
            "| 사례 ID | 경로 | 의도 | 기대 | 연결 항목 | 실행 상태 | 실제 결과 |", "|---|---|---|---|---|---|---|"]
    for c in cases:
        it = items.get(c["scenario_id"])
        st = STATUS_KO[it["status"]] if it else "미실행(결과 없음)"
        ev = (it["evidence"] + (" · 실패: " + " / ".join(it["details"][:2]) if it and it["status"] == "FAIL" else "")) if it else ""
        if it and it["status"] == "FAIL":
            ev = f"**결함 {dids[it['id']]}** · " + ev
        rows.append("| " + " | ".join(cellesc(x) for x in (c["scenario_id"], f"{c.get('method', 'POST')} {c['path']}", c.get("intentional_issue") or "경고·정책 확인",
                                                           c["expected"], ", ".join(c.get("checklist_ids", [])), st, ev)) + " |")
    sec = "\n".join(rows) + "\n"
    if "### 3.4 오류·경고 사례 실행 결과" in text:
        text = re.sub(r"### 3\.4 오류·경고 사례 실행 결과.*?(?=\n## 4\. )", lambda _m: sec, text, count=1, flags=re.S)
    else:
        text = text.replace("\n## 4. 추가 확인 사항", "\n" + sec + "\n## 4. 추가 확인 사항", 1)
    CHECKLIST.write_text(text, encoding="utf-8")
    return filled


def checklist_expect():
    """항목 ID → 기대 결과 칸."""
    out = {}
    for line in CHECKLIST.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^\|\s+([CB]-\d\d) \|", line)
        if m:
            cells = [c.strip() for c in line.strip()[1:-1].split(" | ")]
            if len(cells) == 11:
                out[m[1]] = cells[7]
    return out


def update_plan(items, date, head, dids, out_name):
    text = PLAN.read_text(encoding="utf-8")
    exp = checklist_expect()
    cases = {c["scenario_id"]: c for c in json.loads((HERE / "invalid_cases_NOT_SUBMITTED.json").read_text(encoding="utf-8"))
             + json.loads((HERE / "warning_cases_NOT_SUBMITTED.json").read_text(encoding="utf-8"))}
    core = [i for i in items.values() if re.match(r"^[CB]-\d\d$", i["id"])]
    xw = [i for i in items.values() if re.match(r"^[XW]\d\d$", i["id"])]
    c = lambda L, k: sum(1 for i in L if i["status"] == k)  # noqa: E731
    skips = [i for i in items.values() if i["status"] == "SKIP"]
    lines = [f"## 7. 1차 실행 결과 ({date})", "",
             f"4절 계획대로 `test_qa_checklist.py`(scratchpad)로 체크리스트를 자동 실행하고 결과를 `QA_기본체크리스트_2026-10-14.md`의 실행 상태·실제 결과 칸과 3.4절에 기입했다. "
             f"커밋 `{head}`(+ 커밋 전 `LEDGER_DRIVE_MOCK_DIR` 변경), 데이터셋 V1.1, 헤드리스 Chromium, 모의 드라이브. 출력: `{out_name}`.", "",
             "| 구분 | 통과 | 실패 | 미실행 |", "|---|---|---|---|",
             f"| 체크리스트 C-01~C-15, B-01~B-23 (38) | {c(core, 'PASS')} | {c(core, 'FAIL')} | {c(core, 'SKIP')} |",
             f"| 오류·경고 사례 X01~X18, W01~W05 (23) | {c(xw, 'PASS')} | {c(xw, 'FAIL')} | {c(xw, 'SKIP')} |", "",
             "**미실행(사유)**: " + "; ".join(f"{i['id']} — {i['evidence']}" for i in skips) + ".", ""]
    obs = [(i["id"], m.group(1).strip()) for i in items.values() for m in [re.search(r"관찰: ([^;]+)", i["evidence"])] if m]
    if obs:
        lines += ["**관찰(실패 아님, 정책 확인 필요)**: " + "; ".join(f"{k} — {v}" for k, v in obs) + ".", ""]
    fails = sorted((i for i in items.values() if i["status"] == "FAIL"), key=lambda i: dids[i["id"]])
    if fails:
        lines += ["### 결함 목록", "", "앱 수정은 이번 범위가 아니다(이번 변경은 `drive.py`의 `LEDGER_DRIVE_MOCK_DIR`만). 아래는 재현·관찰·기대와 제안 수정이다.", "",
                  "| 결함 ID | 항목 | 재현 | 관찰 | 기대 | 제안 수정 |", "|---|---|---|---|---|---|"]
        for i in fails:
            n = DEFECT_NOTES.get(i["id"], {})
            expect = n.get("expected") or exp.get(i["id"]) or (cases.get(i["id"], {}).get("expected") if i["id"] in cases else "")
            lines.append("| " + " | ".join(cellesc(x) for x in (
                dids[i["id"]], i["id"], n.get("repro") or i["evidence"], n.get("observed") or " / ".join(i["details"][:4]),
                expect, n.get("fix") or "원인 분석 필요")) + " |")
        lines.append("")
    else:
        lines += ["실패 항목 없음 — 결함 등록 없음.", ""]
    sec = "\n".join(lines)
    if re.search(r"^## 7\. 1차 실행 결과", text, flags=re.M):
        text = re.sub(r"^## 7\. 1차 실행 결과.*\Z", lambda _m: sec, text, count=1, flags=re.S | re.M)
    else:
        text = text.rstrip("\n") + "\n\n" + sec
    PLAN.write_text(text.rstrip("\n") + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runner_output")
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    src = Path(a.runner_output)
    items, env = parse(src)
    if not items:
        sys.exit("ITEM 줄이 없습니다: " + str(src))
    import datetime
    date = a.date or datetime.date.today().isoformat()
    head, dirty = git_head(), git_dirty()
    dids = defect_ids(items)
    filled = update_checklist(items, env, date, head, dirty, dids, src.name)
    update_plan(items, date, head, dids, src.name)
    missing = sorted(({f"C-{i:02d}" for i in range(1, 16)} | {f"B-{i:02d}" for i in range(1, 24)}) - filled)
    print(f"checklist rows filled: {len(filled)}; missing: {missing}; defects: {dids}")


if __name__ == "__main__":
    main()

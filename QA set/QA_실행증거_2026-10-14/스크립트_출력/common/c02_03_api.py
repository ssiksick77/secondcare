from h import *
created = []
print("== C-02 API exec 금액 strings")
for v in ["150,000", "=12000*3+500", "=1/0", "abc", "150000원", " 150 000 ", "1e3", "Infinity", "NaN", "1e400", 1.5, -500]:
    rec = dict(EXEC_OK, 금액=v, 적요=f"C02 {v}"); r = post("/api/exec", rec); print(repr(v), "->", show(r))
    if r.status_code == 200: created.append(r.json())
print("== C-03 request 장비 boundaries")
BASE = {"구분": "장비", "신청인": "QA연구원", "품목": "C03장비", "단가": 1000, "수량": 1, "관련과제": "QA10"}
cases = [("단가", 0), ("단가", 1), ("단가", 10**12), ("단가", 10**12 + 1), ("수량", 0), ("수량", 1), ("수량", 1.5), ("수량", -1), ("수량", "2"),
         ("단가", "1e400"), ("단가", 10**400), ("단가", "inf"), ("단가", "1,000"), ("단가", -1), ("단가", 0.5), ("단가", 1000.7), ("단가", 10**12, "수량", 2)]
for c in cases:
    rec = dict(BASE); 
    for i in range(0, len(c), 2): rec[c[i]] = c[i+1]
    body = rec
    try:
        r = post("/api/request", body)
    except Exception as e:
        print(c, "EXC", e); continue
    j = r.json() if r.status_code == 200 else None
    print(str(c)[:60], "->", r.status_code, (j and {k: j.get(k) for k in ['신청번호','단가','수량','금액','부가세액']}) or r.json())
# raw JSON with 1e400 literal (Python json would send Infinity) - send raw text
for raw in ['{"구분":"장비","신청인":"QA","품목":"C03raw","단가":1e400,"수량":1}', '{"구분":"장비","신청인":"QA","품목":"C03raw","단가":Infinity,"수량":1}', '{"구분":"장비","신청인":"QA","품목":"C03raw","단가":NaN,"수량":1}']:
    r = requests.post(B + "/api/request", data=raw.encode(), headers={"Content-Type": "application/json"})
    print("RAW", raw[30:60], "->", show(r))

import requests,json,sys,os
B='http://127.0.0.1:8812'
Q=r'<home>\AppData\Local\Temp\claude\<session>\18367f8b-184a-424d-99ad-8ce7d7ee1121\scratchpad\qa'
SH=Q+r'\shots\budget_'
def all_(): return requests.get(B+'/api/all').json()
def post(k,rec,**kw):
    r=requests.post(f'{B}/api/{k}',json=rec if not kw else {**rec},**{}); return r
def show(r):
    try: return r.status_code, r.json()
    except Exception: return r.status_code, r.text[:300]

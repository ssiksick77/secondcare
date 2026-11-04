import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8')
B='http://127.0.0.1:8813'
def api(m,p,body=None):
    r=requests.request(m,B+p,json=body)
    try: j=r.json()
    except Exception: j=r.text
    return r.status_code,j
def all_(): return requests.get(B+'/api/all').json()
def ex(no):
    return next((e for e in all_()['exec'] if e['거래번호']==no),None)

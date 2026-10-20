from pw import *
from h import *
e=ex('2026-QA05-020'); row=e['_row']
def f(pg):
    pg.locator('input[data-filter="q"][data-kind="exec"]').fill('R-2026-011'); pg.wait_for_timeout(600)
    print('exec search by 신청번호 R-2026-011 rows:',pg.locator('tr[data-kind="exec"]:visible').count())
    pg.locator('input[data-filter="q"][data-kind="exec"]').fill('')
    # edit 비고 via API (as Alex typing a memo)
    rec={k:v for k,v in e.items() if not k.startswith('_')}; rec['비고']='장비 구입 건 (메모 수정)'
    print(api('PUT',f'/api/exec/{row}',{'rec':rec})[0])
    pg.reload(); pg.wait_for_timeout(1200); pg.get_by_role('tab',name='집행내역').click(); pg.wait_for_timeout(500)
    r=pg.locator('tr[data-kind="exec"]:has-text("2026-QA05-020")')
    print('badge after 비고 edit:',r.locator('.origin').count())
    pg.screenshot(path=S+'flows_ALEX2_badge_lost.png')
    rec['비고']=e['비고']; print('restore',api('PUT',f'/api/exec/{row}',{'rec':rec})[0])
run(f)

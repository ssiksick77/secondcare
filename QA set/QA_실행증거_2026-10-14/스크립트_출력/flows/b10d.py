from pw import *
from h import *
a=all_(); e=[x for x in a['exec'] if x['거래번호']=='2026-QA01-026'][0]
print('API DELETE linked exec:',api('DELETE',f"/api/exec/{e['_row']}",{}))
rec={k:v for k,v in e.items() if not k.startswith('_')}; rec['금액']=250000
print('PUT amount on linked exec:',api('PUT',f"/api/exec/{e['_row']}",{'rec':rec}))
rec=dict(rec); rec['금액']=300000; rec['태그']='가상태그3'
print('PUT tag only:',api('PUT',f"/api/exec/{e['_row']}",{'rec':rec})[0])
# batch delete
print('batch delete:',api('POST','/api/exec/batch',{'creates':[],'updates':[],'deletes':[{'row':e['_row']}]}))
def f(pg):
    pg.click(f'tr[data-kind="exec"][data-row="{e["_row"]}"] td[data-col="재원"]'); pg.wait_for_timeout(700)
    d=pg.locator('#exec-drawer button[data-act="del"]'); print('drawer delete disabled:',d.is_disabled(), d.get_attribute('title'))
    pg.screenshot(path=S+'flows_B10_6_exec_linked_drawer.png')
    pg.keyboard.press('Escape')
    pg.get_by_role('tab',name='적립금').click(); pg.wait_for_timeout(500)
    pg.locator('tr[data-kind="deposit"][data-row="8"] button[data-act="del"]').click(); pg.wait_for_timeout(600)
    pg.screenshot(path=S+'flows_B10_7_dep_delete_confirm.png')
    print('confirm dlg:', pg.locator('dialog[open]').inner_text().replace('\n',' | '))
    pg.locator('dialog[open] button.btn-danger, dialog[open] button:has-text("삭제")').last.click(); pg.wait_for_timeout(1000)
    a=all_(); print('after: dep V', [(d['_row'],d['구분'],d['금액']) for d in a['deposit'] if d['거래처']=='신규거래처V'], 'exec 026 exists', any(x['거래번호']=='2026-QA01-026' for x in a['exec']), len(a['exec']))
run(f)

from h import *
a=all_()
e=[x for x in a['exec'] if x['관리번호'].endswith('_E001')][0]
print(e['_row'],e['거래번호'],e['상태'])

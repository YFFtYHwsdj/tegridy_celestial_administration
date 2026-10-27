"""分带缓冲研究的数学边界与结果一致性检查，不验证CK3引擎。"""
import hashlib,json,math
from pathlib import Path
from model import limit,pressure,transmission,upstream_pressure,trial
from explore import pure_death

assert pure_death(8,0)['never_open']
assert pure_death(8,3,0)['never_open']
assert pure_death(8,9)['mean']==0
assert abs(pure_death(8,3)['mean']-40.48321832467)<1e-8
assert abs(pure_death(8,4)['mean']-29.53961996198)<1e-8
for k in range(1,101):
    for h in [.1,.2,.3,.4,.5,.75]:
        floor,ceil=limit(k,h),limit(k,h,'ceil')
        assert floor<=ceil<=floor+1
assert limit(0,.5,'reserve-top',3)==0
assert [limit(3,h) for h in [.2,.3,.5]]==[3,3,4]
assert pressure(24,20,24)==1 and pressure(24,20,30)==.4
assert upstream_pressure(24,20)==1
assert 1-transmission([0,0,0,1],2,.1,.5,.1)==.9
assert math.isclose(.8*(1-transmission([0,0,0,1],2,.1,.5,.1)),.72)
a=trial('military',0,'reference',720,years=20,hvec=(.2,.2,.3,.5),upstream='fixed20',within_up=.1)
b=trial('military',0,'reference',720,years=20,hvec=(.2,.2,.3,.5),upstream='fixed20',within_up=.1,limit_rule='reserve-top')
assert a['H']==b['H'] and a['trajectory']==b['trajectory']
c=trial('military',0,'reference',720,years=1,hvec=(.2,.2,.2,.2),upstream='fixed20',within_up=.1,limit_rule='reserve-top')
assert c['H'][3]==4
root=Path(__file__).parent;d=json.loads((root/'results.json').read_text())
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v for n,v in d['source_sha256'].items())
assert len(d['configs'])==10 and len(d['groups'])==80 and len(d['runs'])==960
for g in d['groups'].values():
    for s in g['stages']:
        assert s['qualified_by40']==s['success_by40']+s['death_before_success_by40']+s['unresolved_at40']
        assert s['success_by40']==s['conditional_wait_sample_n']
        if s['closed_candidate_share'] is not None:assert 0<=s['closed_candidate_share']<=1
print('通过：有理取整600格、零需求/零退出、解析等待、传导分离/0.72底线、小池有效/无效处理对照、960次结果摘要与风险分箱。')

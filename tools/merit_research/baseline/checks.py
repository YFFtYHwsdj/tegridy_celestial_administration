"""检查数学研究模型的不变量；不声称验证CK3引擎行为。"""
from study import balanced_round, growth, pressure, rate, trial, uniform

assert pressure(0,0,0)==0 and pressure(1,0,0)==1
assert pressure(10,10,12)==0
assert pressure(11,10,12)==.5
assert pressure(12,10,12)==1
assert pressure(99,10,12)==1
assert rate([0,0,0,0],[0,0,0,0],2)==0
assert rate([0,0,0,10],[10,10,10,0],2)<1
for q in [0,1,.25,.5,.75,10.25]:
    mean=sum(balanced_round(q,uniform(88,i,1,5)) for i in range(20000))/20000
    assert abs(mean-q)<.02
for route in ['civil','military']:
    for profile in ['tight','middle','wide','reference','opportunity','reference_top']:
        trial(route,99,profile,720,years=12)
assert trial('civil',2,years=15)==trial('civil',2,years=15)
assert [growth(1,i,720) for i in range(10)]==[growth(1,i,720) for i in range(10)]
print('通过：零需求、压力饱和、12万次取整演算、12组短情景及确定性复算。每场景另逐年检查来源/逐级流量/容量/功绩重置。')

# 通判收益系数0.35（2026-10-16）

正式收益改为每点称职度0.35个百分点、最高35个百分点，保留原生总效率0.5至1.5限幅。回归直接更新events/tca_tongpan_test_events.txt第6及32断言，不改变±0.02容差。旧0.2实现run-64i7comr：51 CHECK_PASS／1 CHECK_FAIL，仅32失败，NOT VERIFIED；新0.35实现run-emogb5gk：1 BEGIN／1 PASS／52 CHECK_PASS，零失败或未执行，完成失败到通过验证。

两局均为CK3 1.20.1.1、独立1066中国观察者、种子1538798675、仅主模组及CLI适配，入口tca_tongpan_test.1。新系数局terminal确认observer及summary、verification_exit与runner_exit为0，result及同次日志核对通过，未检出模组相关错误。116项工具测试、上游覆盖、BOM及空白检查通过；本轮未重跑117项全组，实际浮窗渲染及保存重载未验证。详见[通判实现与历史验收](../song_tongpan_implementation.md)。

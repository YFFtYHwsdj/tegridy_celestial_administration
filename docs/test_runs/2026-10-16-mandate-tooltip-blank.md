# 原版指令浮窗空白修正（2026-10-16）

正常游玩日志直接记录DIARCHY_WINDOW_MANDATE_TOOLTIP缺少Mandate上下文。移除共享浮窗的SelectLocalization，改为互斥节点直接使用原版／通判本地化键；非通判恢复原版全指令列表及启用／灰显，亮色只读仅用于通判。新增日志工具反例先失败，修复后116项工具测试及覆盖检查通过；实际原日志2009条该键错误现可被识别。

独立观察者局run-54zd8r47，CK3 1.20.1.1、1066中国、种子1538798675、仅主模组和CLI适配，通判单项1 PASS／52 CHECK_PASS；观察者、summary、terminal、result及同次日志确认，verification_exit与runner_exit为0。实际悬停没有执行，浮窗实机结果仍待验证；没有以此前全组或未完成的标签探针代替。详见[本次记录](../song_tongpan_implementation.md#2026-10-16-非通判指令浮窗名称与效果空白当前修正)。

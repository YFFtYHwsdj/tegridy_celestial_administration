# 三关系窗口验证（2026-10-16）

当时源码为117项／632断言。本轮独立1066中国观察者局`run-bxncjnqj`，CK3 1.20.1.1，种子1538798675，仅主模组和CLI适配：117 BEGIN／117 PASS／632 CHECK_PASS，零失败或未执行；terminal确认观察者、summary，verification_exit及runner_exit均为0，result和同次日志核对通过。error.log包含原版／安装背景诊断，未检出模组相关错误。114项工具测试和上游覆盖检查通过，整文件GUI覆盖共2项。标签最终简化为直接原生回调后，另以`run-cexg8sji`复核通判单项1 PASS／52 CHECK_PASS，观察者、summary、terminal、result和同次日志通过，verification_exit与runner_exit为0。

该全组验证引擎加载及既有玩法。三关系GUI专项仍未完成五步，NOT VERIFIED，实际标签切换、鼠标点击、使命亮色显示及动态浮窗仍待确认；不能用117项通过替代。具体实现、探针失败记录与人工步骤见[通判实现](../song_tongpan_implementation.md#2026-10-16-三关系标签与使命显示当前实现界面待验证)。

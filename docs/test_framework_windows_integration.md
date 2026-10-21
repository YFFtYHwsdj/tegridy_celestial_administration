# 测试框架 Windows 整合（2026-10-21）

## 范围与实施记录

保留已批准的原生模块登记、默认同局完整回归、可选隔离和目录整理，同时合入`ad2b875`的平台入口适配；不修改业务实现、测试事件、断言或原版审阅基线。按 executing-plans 与 test-driven-development 执行，最终统一只读复核；用户已批准整合、验证后提交，不推送。

- [x] 保存工作区归档、跟踪补丁与原始引用；保留Git安全stash。
- [x] 快进至`f38a34e`，合入Windows提交；合并四处文本冲突，将修改／删除冲突的三项路径断言合到`tools/tests/test_run_game_tests.py`，将平台测试迁入`tools/tests/`。
- [x] 先复现无`fcntl`导入失败、冻结副本缺`platform_paths.py`及Windows执行文件元数据缺失；补齐对应实现与回归。
- [x] 完整工具、覆盖检查、macOS完整及相关单项回归、统一复核；按批准范围提交，完整回归的失败与Windows待验证事项保留如下。

整合前归档：`/private/tmp/tca-before-windows-integration-20261021-200722/`，包含`workspace.tar.gz`、`tracked.patch`、`refs.json`。安全stash不自动删除。

裁定：沿用用户已批准的当前工作区整合，使用归档及stash保护原有未提交成果，不另建实施工作区。此前目录整理记录中“未提交”描述对应各轮当时状态；本轮提交范围为此前测试框架、目录整理与Windows适配的整体，保留远端提交历史。

## 当前实现

安装目录、文档／偏好文件和可执行文件继续使用`tools/platform_paths.py`。启动、启动前检查与环境摘要共用`game_executable()`；`-userdir`统一正斜杠。冻结验收工具包含平台路径模块，避免仓库外运行检查器时缺依赖。

`tools/testing/runtime.py`根据平台延迟导入后端，不在Windows导入`fcntl`。Windows对同一锁文件首字节调用`msvcrt.LK_NBLCK`，macOS继续使用`flock`；竞争重试，其他系统错误直接抛出。取得锁后在保留首字节的情况下更新JSON元数据，异常退出也释放锁，不查找或终止其他任务的游戏。Windows区域锁按当前文件偏移锁定，首字节可以超出空文件末尾，调用及释放前都归零偏移；依据[Python msvcrt.locking文档](https://docs.python.org/3/library/msvcrt.html#msvcrt.locking)。

工具回归覆盖模拟Windows缺少`fcntl`的导入、锁竞争重试／首字节偏移／异常释放、非竞争错误传播、真实跨进程互斥及持锁进程被终止后的再获取。Windows模拟只证明调用路径，不代表真实Windows锁或引擎已运行。

## 验证记录

失败证据：Windows模拟在导入阶段报`ModuleNotFoundError: fcntl`；冻结副本独立检查器报`ModuleNotFoundError: platform_paths`；模拟Windows环境摘要的执行文件大小为`None`。修正后相关10项检查通过。真实跨进程锁回归改为调用正式跨平台入口，保留子进程实际等待和取得锁的断言。

首次185项工具检查通过。最终只读复核发现新增任务JSON读取未指定编码，非UTF-8系统默认编码下中文安装路径会被错误解码，导致克隆元数据损坏或误报排队期间安装变化。增加中文路径／cp1252模拟回归，先复现元数据乱码，再明确工具JSON和日志的UTF-8读取；单项由失败到通过，完整186项工具检查通过。复核确认修正覆盖元数据克隆和执行前环境比较，未发现新的阻塞问题；平台模块、覆盖检查和扫描工具的远端改动完整保留。原版覆盖检查及差异空白检查通过。

### macOS完整复测

固定任务`/private/tmp/tca-windows-integration-final/run-l68w6tje`，入口`python3 tools/run_game_tests.py --seed 1538798675 --timeout 600 --run-root /tmp/tca-windows-integration-final`。CK3 1.20.1.1、独立1066中国观察者局，冻结主模组和CLI适配，同局完整122项；观察者确认、summary终止、snapshot_issues为空，约144秒含清理。

实际122 BEGIN／121 PASS／1 FAIL／790 CHECK_PASS／2 CHECK_FAIL，通判生命周期第28／56断言失败，verification_exit=1、runner_exit=1，NOT VERIFIED。同次日志未见模组相关引擎错误，但不能因此把断言失败判为通过。失败位置与协作改造首轮已有记录一致，根因仍未确认，不修改业务实现或放宽断言。

与整理阶段通过任务`run-86mee3pj`比较，242个主模组及CLI适配文件的摘要完全一致；这证明本轮未改变游戏脚本，不证明间歇失败已消除或工具时序绝无影响。该次冻结发生在最终编码修正之前，之后仅三个工具文件明确了UTF-8读取。最终仓库检查器重新核对同次日志，结果仍为121项通过、通判两条断言失败；不把最终工具倒称为当次冻结版本。

### 最终工具下的相关单项

固定任务`/private/tmp/tca-windows-integration-tongpan/run-nwbyj8rc`，入口`python3 tools/run_game_tests.py --seed 1538798675 --timeout 600 --case tca_tongpan_test.1 --run-root /tmp/tca-windows-integration-tongpan`。该次封存包含最终UTF-8修正与平台依赖；1 BEGIN／1 PASS／58 CHECK_PASS，无失败或未执行，观察者确认、summary终止、verification_exit=0、runner_exit=0、snapshot_issues为空，未检出支持范围内的模组相关引擎错误。约79秒含清理。

单项通过不覆盖或改写完整复测失败结果，也不证明通判世界状态与调度时序问题已归因。保留原始58条断言，不新增业务修补或静默重试完整回归。最终提交包含已有协作框架、目录整理和本次平台适配；本次范围的工具回归、覆盖检查及相关引擎单项通过，完整引擎回归仍有上述两条断言失败。安全stash与外部归档继续保留，不推送。

真实Windows引擎回归仍待在Windows环境执行；旧119项／687断言的记录不能替代本轮122项／792断言验收。

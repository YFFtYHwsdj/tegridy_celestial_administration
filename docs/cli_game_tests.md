# CLI 启动观察者测试

## 当前实现

`tools/run_game_tests.py`在 macOS 上直接启动带窗口的 CK3，启用 debug/develop，跳过前端并打开1066中国书签。随后自动切换观察者、设置最高速度、解除暂停并调用正式全组入口；无需鼠标、键盘模拟或 computer use。这是需要图形会话的自动运行工具，不是无图形执行器。

先启动 Steam，再在本模组目录运行：

```sh
python3 tools/run_game_tests.py
```

默认读取本机 Steam 安装路径；其他安装位置用`--game-dir`指定安装根目录（含`binaries/`），不是`game/`目录：

```sh
python3 tools/run_game_tests.py --game-dir "/path/to/Crusader Kings III" --timeout 360
```

目前仅支持 macOS 的`binaries/ck3.app/Contents/MacOS/ck3`。必须有对应 DLC、图形会话和可用的 Steam 环境；本机验证版本为1.20.0.4，未验证其他平台或版本。总超时默认240秒，包含启动耗时。脚本工作目录设为安装的`binaries/`，给子进程设置`SteamAppId=1158310`。

## 运行隔离与结果

每次在系统临时目录`tca-game-tests/`下生成全新的`run-*`作为`-userdir`，只启用本模组和自动测试适配模组。主模组直接引用当前工作树，适配模组从`tools/cli_adapter/`复制到该次目录。普通启动器播放集不会加载适配模组，因此正常开局不会自动切换观察者或跑测试。

只读取原用户目录`pdx_settings.txt`的 game/Graphics 设定，剔除账户等其他段，在副本中关闭云存档、使用1280×800窗口；原文件不改写。源文件不存在时使用最小设定，可通过`--settings`指定另一份来源。自动存档频率沿用来源设定，生成的本地存档也在本次独立目录中；不加载正常游玩存档。测试会修改世界状态，测试局不能转为正常游玩局。运行期间不要切换玩家、改动测试源、手动暂停或启动另一组测试。

指定输出位置或仅准备文件：

```sh
python3 tools/run_game_tests.py --run-root /tmp/tca-runs
python3 tools/run_game_tests.py --run-root /tmp/tca-runs --prepare-only
```

输出根目录的`latest.json`指向最近一次目录。不同运行的日志不会复用，防止旧汇总造成假完成。不要让多次运行共用同一输出根目录并发启动；`latest.json`只有一个位置。默认临时目录可能被系统清理，需要长期保留时指定外部目录。

每次目录包含：

- `process.json`：本脚本启动的子进程 PID、实际启动参数。
- `progress.json`：当前进度、PASS 数、观察者确认、最近启动／汇总标记。
- `terminal.json`：终止原因、游戏进程退出码、日志核对退出码、工具最终退出码。
- `result.txt`：正式`tools/check_test_run.py --logs <本次日志目录>`结果。
- `stdout.txt`、`logs/`：该次游戏输出及日志。

脚本等待全组汇总（通过、未全通过或中止）、观察者前置失败、游戏进程退出或超时；Ctrl+C 会进入清理。只终止它自己创建的子进程，先发终止信号，6秒无响应则强制终止。本机实际运行需要强制终止，尚未实现引擎正常退出。强制杀死 Python 本身不保证清理，可根据`process.json`核对该子进程；工具不会查找或关闭用户已有的游戏进程。

退出码0要求：本次确有全组汇总、日志明确记录观察者切换成功，并且正式日志核对通过。日志检查失败通常返回1；缺少观察者确认、启动失败、超时、提前退出或中断返回2。游戏进程退出码不代表断言结果。即使显示全部PASS，也须审阅本次`error.log`；核对工具仅识别其支持范围内的模组错误。

## 原生适配与参考依据

`tools/cli_adapter/common/on_action/tca_cli_on_actions.txt`追加`on_game_start_after_lobby`，在`h_china`上设置准备变量，并让皇帝接收次日启动事件。原版`common/on_action/game_start.txt`明确此回调发生在退出大厅之后，适合需要玩家／规则已确定的逻辑。该同名追加内容作为`auxiliary_extensions`登记于`tools/upstream_overrides.json`，对应原版完整回调的已审阅基线为`tools/baselines/cli_on_game_start_after_lobby.txt`，由覆盖检查核对；普通模组查漏扫描不把独立适配模组当作正式加载对象。

`tools/cli_adapter/gui/scripted_widgets/tca_cli_widgets.txt`登记两个透明原生 widget。其`_show`回调使用`ExecuteConsoleCommand('observe')`、`SetGameSpeed('(int32)4')`及`OnPause`。依据为原版 scripted widget 登记规范、`gui/hud.gui`中的速度／暂停接口及原生 debug GUI 的`on_start`用法。次日`events/tca_cli_events.txt`核对承载皇帝为AI、准备变量存在，再直接调用`tca_run_observer_tests_effect`；所有业务断言继续来自正式`events/tca_*_test_events.txt`，没有 Python 生成器或另一套业务规则。

目前不是通用远程控制台：适配 GUI 可执行预置开局命令，尚未验证外部脚本向运行中游戏发送任意指令。原版`game/_commandline_options.info`提供`-skip`、`-bookmark`、`-play`等启动参数；已尝试的启动时 console-action 路径在正常运行循环前执行并退出，不能承载串行延迟测试。无图形实验还出现资源／关闭错误，因此当前工具不使用`-nographics`、启动时 console-action 或本机已知卡住的`scripted_tests`命令。

## 验证记录

2026-10-13临时原型在1.20.0.4完成三次自动全组运行，每次108项／458个断言通过，最后适配方案连续两次使用全新userdir成功；约66—78秒得到汇总，全程无输入模拟。最终一轮日志明确记录观察者切换成功，但仍有8条旧详覆测试的value作用域错误，正式核对返回NOT VERIFIED。另一轮另出现重复添加`prison_feudal_complex_perk`的错误，位置为`common/scripted_effects/tca_judicial_arrest_test_effects.txt:62`的测试准备路径；这些问题没有在本工具引入时修复。

仓库工具的独立目录、设置隔离、观察者确认、退出码和子进程清理由`tools/test_run_game_tests.py`检查；这些是工具逻辑测试，不能替代引擎运行。正式仓库版本的引擎复测结果记录在本节下方。

2026-10-13 14:53正式仓库工具复测：独立userdir、正式全组入口，14:53:27派发108项，14:53:44记录SUITE_ALL_PASSED；108 BEGIN／108 PASS／458 CHECK_PASS，零失败或未执行，日志明确确认观察者切换。启动至汇总约64.9秒，关闭子进程后约71.2秒；子进程退出码-9，工具退出码1。核对发现8条旧作用域错误及2条重复添加perk错误，结果NOT VERIFIED；未见适配模组相关错误。81项Python工具测试、原版基线检查与空白检查通过。macOS真实引擎启动及完整断言已验证，正常退出、其他平台／版本与通用远程控制台未验证。

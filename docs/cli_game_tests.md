# CLI 启动观察者测试

## 当前实现

默认 `python3 tools/run_game_tests.py` 只启动一个独立1066中国观察者测试局，同局先执行即时用例，再串行执行延迟用例。macOS与Windows需要图形会话、Steam及对应DLC，不是无图形执行器。仅加载主模组和CLI适配，不使用普通播放集或正常游玩存档。

### 选择与隔离

```sh
# 默认完整回归，一次启动
python3 tools/run_game_tests.py
# 列出全部模块和原生入口
python3 tools/run_game_tests.py --list
# 即时／延迟入口均可单独运行，--case 可重复
python3 tools/run_game_tests.py --case tca_exam_test.1
# 合并模块，仍然只启动一次；支持 judicial、confucian 等模块前缀
python3 tools/run_game_tests.py --suite exam --suite confucian
# 显式按叶模块拆局；每个子局仍执行原生正式用例
python3 tools/run_game_tests.py --suite exam --suite confucian_statistics --isolate suite
```

`--suite`与`--case`取并集并去重，按原生登记顺序执行。无选择才代表全组；未知模块、未知入口、仅续接事件直接报错。每轮`selection.json`列出实际入口、模块、日志名称、即时／延迟和断言数；验收按冻结计划检查遗漏、重复和额外执行。部分运行不能代表完整验收；隔离全组也不能冒充同局完整回归。

当前目录：`events/tests/`保存原生事件，`common/scripted_effects/tests/framework/`保存框架效果，`modules/`保存登记，`fixtures/`保存场景准备。Python内部实现位于`tools/testing/`，回归位于`tools/tests/`；发现和封存都支持递归目录。

主模组直接维护原生测试及模块登记，工具不生成测试或模拟业务。CLI只在适配副本中设置选择变量，普通游戏不加载适配。框架先从登记计算预期数量，统一派发；用例完成时调用`tca_test_continue_delayed_effect`，不再维护全局阶段编号。

### Windows

保留提交`ad2b875`的平台适配：从注册表读取Steam位置，在`libraryfolders.vdf`登记的库中查找CK3；通过系统已知文件夹接口定位「文档」，兼容OneDrive重定向。Windows可执行文件为`binaries/ck3.exe`，macOS为`binaries/ck3.app/Contents/MacOS/ck3`。`--game-dir`和`--settings`仍可显式指定。

在PowerShell中设置UTF-8后运行，先启动Steam客户端；Windows使用`python`：

```powershell
$env:PYTHONUTF8 = "1"
python tools/run_game_tests.py --timeout 600
```

队列锁按平台选择原生后端：Windows使用`msvcrt.locking`的首字节非阻塞锁，macOS使用`fcntl.flock`；只在竞争时等待，其他系统错误直接报告。元数据更新保留锁定字节，运行结束或异常退出后释放锁。`platform_paths.py`与内部运行模块都包含在冻结工具副本中。

历史证据：Windows提交记录2026-10-21在Windows 11、CK3 1.20.1上运行119项／687断言通过，加载约5分钟、全程约7.5分钟。这是旧框架验收，不代表当前122项协作框架已在Windows引擎复测；本次整合的工具模拟与真实引擎验证分别见[Windows整合验收](test_framework_windows_integration.md)。

### 启动参数

先启动Steam。安装目录和偏好文件由`tools/platform_paths.py`按平台定位，`CK3_GAME_DIR`可覆盖默认安装目录；macOS默认安装位置为`~/Library/Application Support/Steam/steamapps/common/Crusader Kings III`；`--game-dir`指定包含`binaries/`的安装根目录。使用原生`-debug_mode -develop -skip -bookmark=bm_1066_china -play=h_china`，工作目录为安装的`binaries/`，子进程`SteamAppId=1158310`。

`--timeout`默认240秒，按每个子局计算，包含启动及执行，不包含排队；可用`--timeout 360`延长。`--seed`为0至4294967295的原生随机种子。固定种子不能保证异步时点及不同脚本版本的随机调用序列相同。`--strict-title-heir`将实际继任与死亡前预览首位不一致升级为失败，普通通过不代表此严格模式通过。

`--prepare-only`只封存任务，不启动游戏，不表示测试通过。`--run-root /tmp/tca-runs`指定输出根目录，必须位于源码目录之外，防止递归复制。默认使用系统临时目录，长期证据应另行保存。`--settings`指定只读偏好来源，仅复制game／Graphics配置、关闭云存档并改为1280×800窗口，不复制账户段，不修改原文件。

## 拘捕流程与后续观察（当前实现）

CLI只加载主模组和自动启动适配模组，不覆盖原版赎回、释放、处决互动，也不改变AI意愿；没有隔离／观察模式开关。此前的五个完整互动副本、对应基线、模式入口和参数已移除。

批准用例必须确认原生审批、目标回应及成功回调当下的实际关押者、公职囚犯登记状态。第20日检查独立的状态追踪一致性：仍由请求者关押；或确有原关押者的出狱回调且目标已自由；或确有死亡回调且目标已死亡。出狱／死亡有回调仅说明后续过程存在，不证明原因正常。无相应回调却丢失关押状态、转移给未确认的新关押者、或者即时收押错误仍导致失败。原因不明确的后续变化记入诊断，不能扩大为玩法完全验收。

原生追加回调只处理debug标记测试目标，按固定用例标识保存独立请求者上的收押／释放／死亡证据列表；不重新关押、屏蔽AI或修改正式释放／死亡效果。专门的原生延迟用例实际执行imprison、release_from_prison和death，检查回调记录及缺少证据的反例。测试契约变化与原失败记录见[原生拘捕文档](judicial_arrest_native_tests.md#当前观察契约)。

## 运行隔离与结果

每个任务使用唯一`run-*`目录作为任务ID。默认任务也是游戏运行目录；隔离任务另有独立子运行ID，每个子局有自己的`-userdir`、源码、适配、验收工具和日志。输出根目录的`latest.json`原子更新，只供浏览；协作必须引用固定任务ID或目录。

提交时复制主模组到`mod/tca_main/`、适配到`mod/tca_cli_adapter/`，并封存验收工具及依赖到`tools/`。复制前后及目标摘要不一致时拒绝准备；隔离子运行只从已封存任务复制，复制后再次比对。`source_manifest.json`核对脚本、适配、工具、选择计划、DLC加载配置、偏好原件和元数据；启动前后均验证，修改、增加、删除受保护文件都会使验收失败。偏好原件保存在`inputs/pdx_settings.txt`，启动前核对运行副本与原件一致；引擎启动后允许正常写回运行中的`pdx_settings.txt`，原件仍保持封存。源码摘要不包含目录相关描述文件及元数据，便于比较内容；逐文件核对仍覆盖这些文件。

任务在全部输入冻结后等待同机文件锁；锁位于系统临时目录`tca-ck3-engine.lock`，跨输出根目录生效。可在排队期间继续开发，已提交任务不重新读取工作目录。等待可中断；持锁进程退出后系统释放锁。此锁目前约束`run_game_tests.py`任务，不约束手动游戏或其他独立GUI探针；运行这些程序时须自行避免资源争用。

每个实际运行保存：

- `selection.json`：冻结的执行计划及full／selection范围。
- `metadata.json`：运行ID、源码路径、提交、未提交状态，子运行记录父任务。
- `execution.json`：游戏安装版本、可执行文件状态、种子、严格模式和超时；排队期间安装状态改变则拒绝启动。
- `process.json`：本工具拥有的PID、实际命令及环境版本。
- `progress.json`：观察者确认、当前进度与PASS数。
- `terminal.json`：终止原因、游戏退出码、日志验收退出码、最终退出码及源码摘要。
- `verification.json`：逐项PASS／FAIL／PRECONDITION_FAIL／NOT_RUN／NOT_VERIFIED，以及范围、计数和问题。
- `result.txt`、`stdout.txt`、`logs/`：同次核对结果、进程输出和游戏日志。

任务目录另保存`task.json`和`task_result.json`，列出同局／隔离模式及全部子结果。只有所有预期子运行均有成功终局，任务才通过；缺失、损坏、中断或失败均不能被其他通过覆盖。准备而未执行的任务没有通过结果。

业务断言失败且环境有效时继续收集后续结果；承载者死亡或皇位变化等环境损坏中止当前局，剩余用例记为未执行。隔离局互相独立，当前局失败后仍可继续其他子局；用户中断则停止整个任务。

完成、超时和中断时只终止工具创建的游戏子进程，先终止、6秒无响应再强制结束，不查找或关闭用户已有游戏。强制杀死Python本身不保证清理，须按`process.json`核对遗留进程。

退出码0要求指定范围完整通过、明确观察者确认和日志核对通过；业务／日志失败通常为1，启动失败、快照变化、超时、中断等为2。检查整次加载及退出的相关引擎错误，不能仅看PASS计数；工具只识别其支持的错误类型。外部Steam、DLC和游戏安装仍非封闭依赖，UI、保存重载、长期AI等另行验收。

手工重验应优先调用该次封存工具：`python3 <run>/tools/check_test_run.py --logs <run>/logs`。旧目录缺少快照时只能核对当前源码计数，明确警告，不证明旧日志覆盖后来修改。

## 原生适配与参考依据

`tools/cli_adapter/common/on_action/tca_cli_on_actions.txt`追加`on_game_start_after_lobby`，在`h_china`上设置准备变量，并让皇帝接收次日启动事件。原版`common/on_action/game_start.txt`明确此回调发生在退出大厅之后，适合需要玩家／规则已确定的逻辑。该同名追加内容作为`auxiliary_extensions`登记于`tools/upstream_overrides.json`，对应原版完整回调的已审阅基线为`tools/baselines/cli_on_game_start_after_lobby.txt`，由覆盖检查核对；普通模组查漏扫描不把独立适配模组当作正式加载对象。

`tools/cli_adapter/gui/scripted_widgets/tca_cli_widgets.txt`登记两个透明原生 widget。其`_show`回调使用`ExecuteConsoleCommand('observe')`、`SetGameSpeed('(int32)4')`及`OnPause`。依据为原版 scripted widget 登记规范、`gui/hud.gui`中的速度／暂停接口及原生 debug GUI 的`on_start`用法。次日`events/tca_cli_events.txt`核对承载皇帝为AI、准备变量存在，再直接调用`tca_run_observer_tests_effect`；所有业务断言继续来自正式`events/tests/tca_*_test_events.txt`，没有 Python 生成器或另一套业务规则。

目前不是通用远程控制台：适配 GUI 可执行预置开局命令，尚未验证外部脚本向运行中游戏发送任意指令。原版`game/_commandline_options.info`提供`-skip`、`-bookmark`、`-play`等启动参数；已尝试的启动时 console-action 路径在正常运行循环前执行并退出，不能承载串行延迟测试。无图形实验还出现资源／关闭错误，因此当前工具不使用`-nographics`、启动时 console-action 或本机已知卡住的`scripted_tests`命令。


## 历史记录

此前失败复现、临时隔离方案及旧版验收结果保留在[历史记录](history/cli_game_tests_history.md)，不作为当前实现说明。

## 历史：2026-10-14 新入口验证

`--case tca_judicial_refusal_test.1` 在 `run-wegs2daq` 实际执行一项／四断言，观察者、汇总及日志核对通过。默认全组在 `run-c2ssmad4` 实际执行113项／528断言，零失败或未执行，verification_exit及runner_exit均为0。正常全组入口显式初始化单项开关为no，单项入口为yes，结束统一清理；避免仅在未被引用效果中赋值导致加载时未初始化提示。引擎事件数值ID须小于10000，维护中的测试读取与日志检查均检查该错误。

## 可选：三关系窗口控制器探针

`python3 tools/run_diarchy_ui_probe.py --timeout 180`创建独立1066图形局，复制主模组和CLI适配，不进入观察者。原生事件准备自带摄政的通判、其直属上级、被监督知州；启动控件在夹具准备完毕后切换玩家，以固定夹具知州ID调用OpenGameViewData打开真实窗口，随后使用正式标签onclick及down表达式，检查真实窗口目标、分权者、使命权限及选中互斥。启动登记、夹具切换前置、跨窗口阶段及判定工具均有Python回归，Python不重写业务规则。

探针按窗口打开、主管、自己、领主、通判、返回逐步验收；失败也继续后续步骤，记录明确的TCA_GUI_FAIL而非只等组合条件成立。正常PASS每阶段只记录一次；原生测试夹具标记处理窗口控件重建的重复观察，所有FAIL仍保留。完成后在同一隔离局通过正式结束互动验收可用性，并在两日后检查分权及加成、附费确已结束，不调用维护或直接改法替操作造结果；没有假定该按钮应修改全帝国制度法律。当前互动隐藏或结束被维护恢复时，应报告失败而不是跳过。

`terminal.json`按阶段列出PASS／FAIL／NOT_VERIFIED及失败日志，`result.txt`与同次error.log、source_manifest一并验收。缺结果、重复结果、前置失败、超时、源码副本变化或相关引擎错误均不能通过。HUD入口及真实鼠标命中、不同缩放下的布局、悬停渲染、皇帝／知州切换玩家、旧存档和保存重载仍须人工验收；该探针自动验证的是同一通判玩家的三个关系窗口，不等于三个玩家角色均已测试。

继任行另有静态几何契约：通判网格的填充方向、最大横向数量及首个单元尺寸与原版继任网格一致，防止再次改成纵向展开。此项不证明实际渲染、溢出或悬停效果。当前运行封存了统一验收工具，但GUI探针自身的专用控制器及验收器仍从当前仓库执行，不能将其表述为完全冻结的探针环境。

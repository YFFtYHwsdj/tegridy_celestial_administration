# 测试运行

本页提供运行步骤、参数和产物解释；新增原生用例及调度契约见[测试框架](framework.md)。

## 运行一次回归

从仓库根目录执行。先启动Steam，确认CK3、所需DLC和图形会话可用；工具默认新建可丢弃的1066中国观察者局；`--start-date 1178`选择1178，`--start-date both`顺序建立两个独立观察者局，各自封存日期并核对实际日期。工具只加载主模组及CLI适配，不使用普通播放集或正常游玩存档。

```sh
# 查看可选择的正式用例，不启动游戏
python3 tools/run_game_tests.py --list
# 日常先选受影响模块，优先并行
python3 tools/run_game_tests.py --suite exam --parallel 4 --timeout 600
# 仅影响面需要时运行一次完整同局回归，给足超时
python3 tools/run_game_tests.py --parallel 4 --timeout 1800
```

使用工具输出的本次任务目录，核对 `terminal.json`、`verification.json`、`result.txt` 和同次日志。通过必须同时满足所选范围完整执行、观察者确认、终局汇总、快照与日志核对通过；只看到PASS、只准备未执行或超时退出都不能算通过。详细文件及退出码见[运行隔离与结果](#运行隔离与结果)。

工具省略`--parallel`时仍使用K=1；日常应显式传`--parallel 4`。全量回归在同一个世界内推进多个游戏年，包含一次业务原生保存重载；若所选范围包含真实玩家会话末项，再保存检查点并以新进程建立人类席位，最多启动四个进程，近年用例和等待增加后明显变长；以 `terminal.json` 的 `seconds` 和实际日志为准，不要用固定数字承诺。超时预算不足时第二局不会执行，整次运行按超时失败，并且仍会进行收尾与验收核对。

Windows使用 `python`，先按[Windows步骤](#windows)设置UTF-8。需要保留产物时显式指定[持久输出目录](../development/README.md#测试证据如何保存)；不会自动上传共享。

### 引擎错误中的纯注册帧

检查器保留所有原始错误。只有指定源码及其同次冻结上游登记同时证明某个 `(父on_action, 模组路径, 行号)` 定义完整地仅含 `on_actions` 注册时，该父帧才单独标记为 `native-registration-frame`，不单凭它归因为模组执行错误。源码、登记、定义或行号不明确均维持阻断；报错源、实际模组子回调、effect、trigger、GUI及错误中的真实模组脚本标识仍阻断。人物展示名中带 Internal ID 的模组头衔不单独充当执行证据；支持引擎真实的有／无冒号及可选 Historical ID 后缀，新格式必须有指定源码与脚本栈。仅识别 `of <头衔> (Internal ID...)`，姓名、历史ID及其它正文中的真实模组标识仍保守阻断，不泛化为任何 `c_tca_` 文本均可放行。

只有这种纯注册帧的原生错误单独显示为原生背景诊断，并在 `verification.json` 的 `native_registration_diagnostics` 保留原文和逐帧依据；纯人物头衔展示诊断以 `native-runtime-title` 分类保存在 `native_runtime_title_diagnostics`，实际模组帧优先阻断。另仅对原生 `reverse_add_opinion` 自己对自己好感错误与 `change_opportunities` 无效计谋错误，按完整固定语法和数字 Internal ID 解析人物展示字段；必须有指定源码及其登记、完整且全原生的执行栈。该字段的姓名、头衔和 Historical ID 可以含模组标识，诊断以 `native-runtime-character` 保留完整原文及人物字段，在 `native_runtime_character_diagnostics` 单独显示；函数名、scheme键、target及人物段外的脚本标识继续检查，解析不完整仍阻断。这不表示原始日志无错，也不证明无模组局可复现。`check_test_run.py --output <新文件>` 可只读复核旧冻结运行并另存判定，不能改写原结果来替换历史失败。

## 真实玩家会话末阶段

默认全量和显式选择 `tca_court_session.1`／`tca_retirement_session.1` 都会执行对应的真实玩家会话。每项先认领独占lane，再从观察者状态保存本局专属检查点；CLI核对原生保存完成日志和本地存档后，只退出自己启动的进程，再用 `-loadsave` 与 `-play=h_china` 建立真实人类席位。续局不重新派发suite、不重置统计、不先进入观察者；读档入口由新进程GUI识别保存态启动，不依赖新开局大厅回调。重载界面以显式皇帝ID直接调用原生身份入口；原生 `is_ai = no` 确认皇帝为玩家后，只写人类阶段和对应授权。独立界面控件读取该授权，再以显式ID直接调用对应业务事件；业务入口再次检查原生身份与活动lane，并以持久标记拒绝重复BEGIN。界面不写人类授权或测试结果。控制台`effect`内的`trigger_event`及身份入口同步内投业务事件曾出现命令成功却未实际投递，不能以返回成功作为执行证据。

宫廷会话随后真实接管自备地方官署，由原生事件确认玩家身份，检查普通内阁不入池、兼任差遣者的任期与正常升迁，并跨日复验实际职位资格，最后真实返回观察者。业务断言与边界见[宫廷差遣验收](../court_positions/verification.md#原生用例入口)。

退休会话保留原有五条断言：GUI真实接管自备人物，只写传家请求；原报告者的原生watcher消费一次请求，保留两日等待后执行传家及身份／效果断言。GUI再回观察者，排队的末条断言才收尾；控制台命令返回成功不算事件投递或测试通过。退休入口仍显式打开原版无副作用的 `debug.1004` 信件和 `debug.1005` 人物事件，验证实际选项选择；宫廷会话不额外排这两个无关窗口。玩家阶段可见事件只选择实际存在且有效的首个选项，不改暂停标记或伪造日期。窗口处理继承原生 `EventWindow` 实例；CLI适配器仅在原版 `letter_event.gui` 与 `character_event.gui` 插入人类阶段、最前方窗口专用控件，移除插入块后其余字节须与已核原版散列一致，主模组不覆盖这两个窗口。只有控件源码不证明窗口关闭或日期推进，新开局教程窗口仍不在此范围。

同时选择两项时，目录先执行宫廷会话，再执行退休会话；两项分别原生保存重启，不通过观察者中的 `play` 命令复用人类身份。宫廷会话固定使用 `tca_cli_court_human_session`，退休会话保留 `tca_cli_human_session`。只有冻结选择包含对应事件时才能加载其固定名称，每个用例至多一次；GUI的保存与请求防重复状态也按用例区分，不能借用前项的保存结果或界面状态。

业务保存重载使用 `RELOAD_SAVE`，至多一次且必须先于全部人类阶段；玩家席位建立使用 `HUMAN_SAVE`，每个已选人类用例各一次。两类检查点均保留原生日志、存档散列与逐进程证据。`terminal.json` 的 `phase_modes`、`human_phases` 记录实际阶段；每个人类进程分别核对唯一初始人类身份、与检查点匹配的唯一用例BEGIN、原生接管身份、业务断言、回观察者及末条断言顺序。不能用前项证据代替后项；全部所选用例与阶段证据通过才算整轮通过，前置失败仍为未执行。

## 按任务查阅

选择范围见下一节；安装、种子和超时见[启动参数](#启动参数)；缺结果或失败先查[运行产物](#运行隔离与结果)；无法使用CLI时的手工观察者入口见[框架契约](framework.md#观察者入口)。[通判窗口探针](#可选三关系窗口控制器探针)有独立范围，不代替完整玩法验收。

## 选择与隔离

```sh
# 即时／延迟入口均可单独运行，--case可重复
python3 tools/run_game_tests.py --case tca_exam_test.1 --parallel 4 --timeout 600
# 合并模块，在同一个世界执行；支持judicial、confucian等前缀
python3 tools/run_game_tests.py --suite exam --suite confucian --parallel 4 --timeout 600
# 显式按叶模块拆局；每个子局仍执行原生正式用例
python3 tools/run_game_tests.py --suite exam --suite confucian_statistics --isolate suite --parallel 4 --timeout 600
```

`--suite`与`--case`取并集并去重，按原生登记顺序执行。无选择才代表全组；未知模块、未知入口、仅续接事件直接报错。每轮`selection.json`列出实际入口、模块、日志名称、即时／延迟和断言数；验收按冻结计划检查遗漏、重复和额外执行。部分运行不能代表完整验收；隔离全组也不能冒充同局完整回归。

当前目录：`events/tests/`保存原生事件，`common/scripted_effects/tests/framework/`保存框架效果，`modules/`保存登记，`fixtures/`保存场景准备。Python内部实现位于`tools/testing/`，回归位于`tools/tests/`；发现和封存都支持递归目录。

验证范围按[工作约定](../../AGENTS.md#测试与验证)选择最小充分集合：优先复用有效证据、扩展已有用例、批量修复后合并定向运行，不把整模块或全量当作每次收口的固定步骤。

主模组直接维护原生测试及模块登记，工具不生成测试或模拟业务。CLI只在适配副本中设置选择变量，普通游戏不加载适配。框架先从登记计算预期数量，统一派发；延迟用例按模块lane调度，工具缺省一次一个，推荐显式K=4，用例结束时调用正式lane结束效果续接，不再维护全局阶段编号。

## 并行运行

同一进程、同一世界的延迟用例按模块lane并发，日常开发与验收优先显式使用`--parallel 4`。工具缺省值仍为1；`--parallel K`（1至32）最多同时运行K个不同GROUP的延迟用例，同一GROUP内仍逐个执行，保存重载、玩家会话、开局快照等独占用例在途时整体串行。lane、GROUP、EXCLUSIVE与结束效果的契约见[框架契约](framework.md#并发-lane-与用例隔离)。K>1完整通过可直接作为所选范围的验收依据，不要求例行补跑同范围K=1。

```sh
# 通常只运行一次所需范围
python3 tools/run_game_tests.py --suite judicial_law --suite custody_review --parallel 4 --timeout 900
# 仅疑似并发冲突或调度语义变化时，追加最小相关范围K=1诊断
python3 tools/run_game_tests.py --suite judicial_law --suite custody_review --parallel 1 --timeout 900
# 已有两次可比运行时，逐用例核对；不是日常双跑要求
python3 tools/compare_test_runs.py "<串行任务目录>" "<并行任务目录>"
```

并行运行不改变选择计划、用例集合、等待天数或断言，`selection.json`与`verification.json`的结构不变；`execution.json`、`task.json`额外记录`parallel`。并发只减少同局内等待的叠加，墙钟仍受最慢lane和独占用例限制，不能用固定倍率承诺耗时。并发时调试日志按实际发生顺序交错，验收仍按冻结计划和逐用例断言核对，不以日志相邻行判断用例归属。

**验证边界**：接受K>1通过后无需另跑K=1的工程判断，但报告只写实际执行的K值和范围，不将未运行的K=1称为实测通过。并行验收同样要求冻结计划完整执行、终局、`TCA_TEST`及同次`error.log`核对通过。只有疑似并发冲突、调度器修改或明确串行语义要求时，才对最小相关范围补串行诊断或对照；不为取得串行结果额外跑全量。`tools/compare_test_runs.py`按`verification.json`比较逐用例状态与断言计数，缺失显示`<missing>`，支持`--json`；`--ignore`仅用于已明确说明的既有问题对比，不得掩盖新增失败、缺失结果或引擎错误，也不改变原始验收失败。发现新差异先检查共享状态与GROUP归属，不能直接归为偶发波动。

新增或修改用例后先运行`python3 tools/check_test_parallel.py`：它检查注册的GROUP／EXCLUSIVE元数据、裸全局标识、lane flag与lane结束调用一致性、跨GROUP报告者状态冲突、共享状态跨GROUP写冲突（延迟非独占用例）、失败flag的写入／读取配对及触发链内失败归属；检查不通过不得提交，检查通过也不证明引擎行为。

**既有并发观察与限制**：以下旧运行只保留独占取舍和已知失败背景，不代表当前源码验收通过。登记以`python3 tools/check_test_parallel.py`输出为准（当前54个GROUP、26例EXCLUSIVE、5个跨命名空间合并组）。全量`--parallel 4`（固定种子424242）已在本机同一时段做过基线/放宽A/B：基线配置（62 GROUP／38 EXCLUSIVE）约496s、235 PASS，放宽后配置（54 GROUP／26 EXCLUSIVE）连续两轮约445s与458s、239与242 PASS；相对同机基线约1.08至1.12倍，相对全量K=1（715.7s）约1.56至1.61倍，提供并行运行耗时的参考，不承诺当前版本相同收益。两轮均245/245用例执行、无重复BEGIN、无新增mod引擎错误。固定种子下失败集仍逐轮漂移（基线单轮也出现约10例非通过），已知WIP flaky、K>1夹具世界状态漂移与调度敏感项（retirement系列、tongpan_lifecycle、arrest家族、`tca_test_merit_startup_central_boundaries`等）不写入本文清单；同一用例跨轮PASS／FAIL／PRECONDITION_FAIL交替应视为漂移而非确定性回归，新差异先做定向诊断，已有可比运行时用`tools/compare_test_runs.py`逐项核对。放宽轨迹：拘捕组10例曾试解除独占，两轮共同出现确定性失败且墙钟无收益，已回退；司法六个模块合并为`tca_judicial_realm`（timing三例与`tca_test_review_send_resolution`保留独占，否则续接断言在并发下缺失）；功绩年度组四模块合并为`tca_merit_annual_worker`（`tca_test_merit_maintenance_idempotence`与`tca_test_merit_multicountry`保留独占，避免任意日期世界级年度结算互污；pulse／draw／natural／legacy解除独占）。`tca_test_retirement_eligibility`的原生等级缓存时序对调度敏感，仅在EXCLUSIVE下稳定通过，其独占登记不得移除。保存重载探针偶发引擎级中断（console save→reload转换，同配置多数轮次未复现），遇到`process_exit`或`NOT VERIFIED`按整轮重跑处理，不记为用例失败；若复现，可在`gui/tca_merit_saveload_probe.gui`保存后加`OnPause`并延长等待，或由运行器在检测到保存成功后门控注入破坏步骤。日常验收按上述并行优先策略执行，不例行追加K=1。

## Windows

平台路径适配：从注册表读取Steam位置，在`libraryfolders.vdf`登记的库中查找CK3；通过系统已知文件夹接口定位「文档」，兼容OneDrive重定向。Windows可执行文件为`binaries/ck3.exe`，macOS为`binaries/ck3.app/Contents/MacOS/ck3`。`--game-dir`和`--settings`仍可显式指定。

在PowerShell中设置UTF-8后运行，先启动Steam客户端；Windows使用`python`：

```powershell
$env:PYTHONUTF8 = "1"
# 全量回归预留20至30分钟；单项或小范围可用较短超时
python tools/run_game_tests.py --parallel 4 --timeout 1800
```

队列锁按平台选择原生后端：Windows使用`msvcrt.locking`的首字节非阻塞锁，macOS使用`fcntl.flock`；只在竞争时等待，其他系统错误直接报告。元数据更新保留锁定字节，运行结束或异常退出后释放锁。`platform_paths.py`与内部运行模块都包含在冻结工具副本中。

平台后端的模拟回归不证明真实 Windows 引擎通过；当前整合后的 Windows 引擎路径仍需在对应环境执行正式全组验收。

## 启动参数

先启动Steam。安装目录和偏好文件由`tools/platform_paths.py`按平台定位，`CK3_GAME_DIR`可覆盖默认安装目录；macOS默认安装位置为`~/Library/Application Support/Steam/steamapps/common/Crusader Kings III`；`--game-dir`指定包含`binaries/`的安装根目录。使用原生`-debug_mode -develop -skip -bookmark=bm_1066_china -play=h_china`，工作目录为安装的`binaries/`，子进程`SteamAppId=1158310`。

`--timeout`按每个子局计算，包含两阶段启动及执行，不包含排队、任务准备和运行结束后的日志验收及快照校验；默认240秒只适合单项或小范围。全量回归应显式使用`--timeout 1800`（机器繁忙或留更多余量时可用2400）：预算不足会让第二局不执行并整次按超时失败，事后核对仍需再花1至2分钟。`terminal.json`的`seconds`是计时器内的实际耗时，整次墙钟还需加上排队与开头所述的验收时间，报告耗时时应分开说明。`--seed`为0至4294967295的原生随机种子。固定种子不能保证异步时点及不同脚本版本的随机调用序列相同。`--strict-title-heir`将实际继任与死亡前预览首位不一致升级为失败，普通通过不代表此严格模式通过。`--parallel N`取1至32，默认1，控制同局延迟lane并发上限，见[并行运行](#并行运行)。

`--prepare-only`只封存任务，不启动游戏，不表示测试通过。`--run-root "<仓库外持久产物目录>"`指定输出根目录，必须位于源码目录之外，防止递归复制。默认使用系统临时目录，持久目录范例及保留规则见[证据保存](../development/README.md#测试证据如何保存)。`--settings`指定只读偏好来源，仅复制game／Graphics配置、关闭云存档并改为1280×800窗口，不复制账户段，不修改原文件。

## 运行隔离与结果

每个任务使用唯一`run-*`目录作为任务ID。默认任务也是游戏运行目录；隔离任务另有独立子运行ID，每个子局有自己的`-userdir`、源码、适配、验收工具和日志。输出根目录的`latest.json`原子更新，只供浏览；协作必须引用固定任务ID或目录。

提交时复制主模组到`mod/tca_main/`、适配到`mod/tca_cli_adapter/`，并封存验收工具及依赖到`tools/`。复制前后及目标摘要不一致时拒绝准备；隔离子运行只从已封存任务复制，复制后再次比对。`source_manifest.json`核对脚本、适配、工具、选择计划、DLC加载配置、偏好原件和元数据；启动前后均验证，修改、增加、删除受保护文件都会使验收失败。偏好原件保存在`inputs/pdx_settings.txt`，启动前核对运行副本与原件一致；引擎启动后允许正常写回运行中的`pdx_settings.txt`，原件仍保持封存。源码摘要不包含目录相关描述文件及元数据，便于比较内容；逐文件核对仍覆盖这些文件。

任务在全部输入冻结后等待同机文件锁；锁位于系统临时目录`tca-ck3-engine.lock`，跨输出根目录生效。可在排队期间继续开发，已提交任务不重新读取工作目录。等待可中断；持锁进程退出后系统释放锁。此锁目前约束`run_game_tests.py`任务，不约束手动游戏或其他独立GUI探针；运行这些程序时须自行避免资源争用。

每个实际运行保存：

- `selection.json`：冻结的执行计划及full／selection范围。
- `metadata.json`：运行ID、源码路径、提交、未提交状态，子运行记录父任务。
- `execution.json`：游戏安装版本、可执行文件状态、种子、严格模式、延迟lane并发上限和超时；排队期间安装状态改变则拒绝启动。
- `process.json`：本工具拥有的PID、实际命令及环境版本。
- `progress.json`：观察者确认、当前进度与PASS数。
- `terminal.json`：终止原因、游戏退出码、日志验收退出码、延迟lane并发上限、最终退出码及源码摘要。
- `verification.json`：逐项PASS／FAIL／PRECONDITION_FAIL／NOT_RUN／NOT_VERIFIED，以及范围、计数和问题。
- `result.txt`、`stdout.txt`、`logs/`：同次核对结果、进程输出和游戏日志。

原生保存重载探针可在保存成功并完成现场断言后发出 `TCA_CLI RELOAD_SAVE <name>`。控制器仅接受一次受限本地名称，检查实际存档后退出自己拥有的进程，再以原生 `-loadsave=<name>.ck3` 加载同一存档，并指定同一测试君主进入续局后切回观察者；不重新生成世界或派发测试。全程共用原超时。`phases/`保留每个进程的原始日志、命令和退出状态，`reload_evidence.json`记录原始日志摘要，最终`logs/debug.log`和`logs/error.log`逐字节连接所有阶段供既有断言与错误验收。每个进程均须独立确认观察者，`terminal.json` 的 `phase_observer_confirmed` 逐阶段记录，不沿用首进程确认。原进程异常退出、重复请求、缺失保存和续局启动失败均不能通过。续局识别必须依赖写入存档的脚本状态：原生 UI 会话变量不随存档恢复，不能单独用来判断当前进程是首局还是续局；识别失败时，加载后的 GUI 会再次保存／破坏并发第二个请求，控制器按重复请求中止。用于识别的脚本标记须在保存前写入，且由实际事件或效果设置；只在 GUI 控制台字符串中赋值会被静态检查判为未设置。阶段切换也不应与保存同帧提交，须让异步存档快照包含该状态。原生观察者存档是否需要额外界面操作以实际用例结果为准，不把该控制器能力推广为任意存档兼容保证。

任务目录另保存`task.json`和`task_result.json`，列出同局／隔离模式、延迟lane并发上限及全部子结果。只有所有预期子运行均有成功终局，任务才通过；缺失、损坏、中断或失败均不能被其他通过覆盖。准备而未执行的任务没有通过结果。

业务断言失败且环境有效时继续收集后续结果；承载者死亡或皇位变化等环境损坏中止当前局，剩余用例记为未执行。隔离局互相独立，当前局失败后仍可继续其他子局；用户中断则停止整个任务。

完成、超时和中断时只终止工具创建的游戏子进程，先终止、6秒无响应再强制结束，不查找或关闭用户已有游戏。强制杀死Python本身不保证清理，须按`process.json`核对遗留进程。

退出码0要求指定范围完整通过、明确观察者确认和日志核对通过；业务／日志失败通常为1，启动失败、快照变化、超时、中断等为2。检查整次加载及退出的相关引擎错误，不能仅看PASS计数；工具只识别其支持的错误类型。Script system error 是否归属模组，按 `Script location` 栈帧是否落在模组脚本或已登记覆盖文件判断；正文出现模组头衔键、角色名等运行时文本但栈全在原版脚本的错误不计为模组错误（避免误报），也不覆盖“仅由模组状态诱发、栈全在原版”的错误。外部Steam、DLC和游戏安装仍非封闭依赖，UI、保存重载、长期AI等另行验收。

手工重验应优先调用该次封存工具：`python3 <run>/tools/check_test_run.py --logs <run>/logs`。旧目录缺少快照时只能核对当前源码计数，明确警告，不证明旧日志覆盖后来修改。

## 原生适配与参考依据

`tools/cli_adapter/common/on_action/tca_cli_on_actions.txt`追加`on_game_start_after_lobby`，在`h_china`上设置准备变量，并让皇帝接收次日启动事件。原版`common/on_action/game_start.txt`明确此回调发生在退出大厅之后，适合需要玩家／规则已确定的逻辑。该同名追加内容作为`auxiliary_extensions`登记于`tools/upstream_overrides.json`，对应原版完整回调的已审阅基线为`tools/baselines/cli_on_game_start_after_lobby.txt`，由覆盖检查核对；普通模组查漏扫描不把独立适配模组当作正式加载对象。

`tools/cli_adapter/gui/scripted_widgets/tca_cli_widgets.txt`登记两个透明原生 widget。其`_show`回调使用`ExecuteConsoleCommand('observe')`、最高速`SetGameSpeed('(int32)4')`（内部参数4对应界面第5档）及`OnPause`。依据为原版 scripted widget 登记规范、`gui/hud.gui`中的速度／暂停接口及原生 debug GUI 的`on_start`用法。次日`events/tca_cli_events.txt`核对承载皇帝为AI、准备变量存在，再直接调用`tca_run_observer_tests_effect`；所有业务断言继续来自正式`events/tests/tca_*_test_events.txt`，没有 Python 生成器或另一套业务规则。

目前不是通用远程控制台：适配 GUI 可执行预置开局命令，尚未验证外部脚本向运行中游戏发送任意指令。原版`game/_commandline_options.info`提供`-skip`、`-bookmark`、`-play`等启动参数；已尝试的启动时 console-action 路径在正常运行循环前执行并退出，不能承载延迟用例测试。无图形实验还出现资源／关闭错误，因此当前工具不使用`-nographics`、启动时 console-action 或本机已知卡住的`scripted_tests`命令。

## 可选：三关系窗口控制器探针

`python3 tools/run_diarchy_ui_probe.py --timeout 180`创建独立1066图形局，复制主模组和CLI适配，不进入观察者。原生事件准备自带摄政的通判、其直属上级、被监督知州；启动控件在夹具准备完毕后切换玩家，以固定夹具知州ID调用OpenGameViewData打开真实窗口，随后使用正式标签onclick及down表达式，检查真实窗口目标、分权者、使命权限及选中互斥。启动登记、夹具切换前置、跨窗口阶段及判定工具均有Python回归，Python不重写业务规则。

探针按窗口打开、主管、自己、领主、通判、返回逐步验收；失败也继续后续步骤，记录明确的TCA_GUI_FAIL而非只等组合条件成立。正常PASS每阶段只记录一次；原生测试夹具标记处理窗口控件重建的重复观察，所有FAIL仍保留。完成后在同一隔离局通过正式结束互动验收可用性，并在两日后检查分权及加成、附费确已结束，不调用维护或直接改法替操作造结果；没有假定该按钮应修改全帝国制度法律。当前互动隐藏或结束被维护恢复时，应报告失败而不是跳过。

`terminal.json`按阶段列出PASS／FAIL／NOT_VERIFIED及失败日志，`result.txt`与同次error.log、source_manifest一并验收。缺结果、重复结果、前置失败、超时、源码副本变化或相关引擎错误均不能通过。HUD入口及真实鼠标命中、不同缩放下的布局、悬停渲染、皇帝／知州切换玩家、旧存档和保存重载仍须人工验收；该探针自动验证的是同一通判玩家的三个关系窗口，不等于三个玩家角色均已测试。

继任行另有静态几何契约：通判网格的填充方向、最大横向数量及首个单元尺寸与原版继任网格一致，防止再次改成纵向展开。此项不证明实际渲染、溢出或悬停效果。当前运行封存了统一验收工具，但GUI探针自身的专用控制器及验收器仍从当前仓库执行，不能将其表述为完全冻结的探针环境。

## 当前验证边界

以 `--list` 和该次冻结 `selection.json` 获取实际范围，不手填全组总数。超时、中断、未确认观察者、缺少结果或日志核对失败均为 `NOT VERIFIED`。没有执行不能算通过；单项、选择运行和分局隔离分别报告，不能替代同局完整回归。

并行完整通过可作为实际所选范围的验收依据，无需例行串行复跑；串并行诊断的适用条件见[并行运行](#并行运行)。并发安全依靠lane分组与静态检查，没有运行时共享状态守卫，跨模块共享状态仍须按[框架契约](framework.md#并发-lane-与用例隔离)人工判断。

[通判生命周期](../tongpan/implementation.md#未解决的生命周期一致性)及[经费请求](../office_funding/interactions.md#待复核的请求状态)存在尚未归因的跨执行范围差异。实际失败场景、源码入口和复核方法由所属模块维护；测试运行文档不保留另一份历史成绩表。已知WIP flaky项的对比处理见[并行运行](#并行运行)。真实 Windows 引擎、测试窗口显示、保存重载与长期 AI 仍需专门验收。

用例编写、生命周期及观察者手工入口见[框架契约](framework.md)；重要证据的筛选和保存由[开发规范](../development/README.md)维护。

## 双开局官员验证

```sh
python3 tools/build_startup_officials.py --check
python3 tools/run_game_tests.py --start-date both --suite startup_officials --suite tongpan --parallel 4 --timeout 600
```

双开局不共用世界；每局均按并行优先策略验收，不额外补跑K=1。原始开局快照在其它夹具前读取；家族测试使用正式策略和授职入口，季度等待不等于存档重载。现有用例仍保留各自前置，未执行不能算1178通过；当前差异见[开局官员验证](../appointment/startup_officials_verification.md)。

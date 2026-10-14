# 模组游戏内测试

## 当前结构

测试直接维护为CK3原生隐藏事件，不使用Python生成器，也不保留另一套P脚本中间源。`events/`下的测试文件就是正式测试代码，`common/scripted_effects/tca_judicial_law_test_effects.txt`是共享场景准备，Python仅用于读取日志和静态检查。

当前110项／485断言，89项即时、21项串行延迟。原生拘捕组直接发送真实审批请求，检查即时收押和第20日的匹配观察证据；观察证据用例使用真实释放／死亡回调，并包含跨囚犯旧证据反例。测试范围及结果见[原生拘捕文档](judicial_arrest_native_tests.md)。

## CLI 自动执行

macOS 可运行`python3 tools/run_game_tests.py`，自动建立独立1066观察者测试局并执行下述正式入口。每次使用全新日志目录，完成后调用正式日志核对；引擎错误会导致非零退出码。运行方式、原生适配、已验证范围与限制见[CLI 测试说明](cli_game_tests.md)。

## 观察者入口（2026-10-13）

在专用1066中国debug测试局进入观察者模式后，控制台执行：

```text
effect tca_run_observer_tests_effect = yes
```

无需查找角色ID或临时切换玩家。`tca_run_observer_tests_effect`检查debug、1066开局及有效天朝皇帝，再由`tca_test_resolve_observer_host_effect`固定选择`title:h_china.holder`承载`tca_tests.1`。测试统计、运行标记及二十一项串行延迟继续保存在该角色上；不使用控制台的默认角色。原有玩家决议、`event tca_tests.1`及各组单项入口保持不变。

入口发现任一存活角色已有全组或延迟用例运行标记时，只记录`TCA_TEST OBSERVER_ENTRY_BUSY`，不重置统计。前置不满足记录`TCA_TEST OBSERVER_ENTRY_REJECTED`；成功调用记录`TCA_TEST OBSERVER_ENTRY_DISPATCH`，随后必须出现新的`SUITE_DISPATCH 110 cases`。该入口允许玩家模式使用，但也固定选择天朝皇帝，不将玩家当前角色自动作为测试请求者。

观察者继续正常推进游戏日期，直到日志出现`SUITE_ALL_PASSED`或`SUITE_NOT_ALL_PASSED`，再运行`python3 tools/check_test_run.py`并审阅同次`error.log`。通知面向承载角色，不依赖观察者能看到通知。不得在运行中切换玩家、并发执行另一组测试或使用正常游玩存档。承载者或皇帝死亡、皇位更换时主动中止，详见下节；事件丢失、日期不推进或游戏退出造成缺少终局结果时仍是未完成，不自动换人接续或伪造通过。

依据：本机CK3 1.20.0.4原版`events/_events.info`支持`scope = none`，但Mac arm64程序`SEventConsoleCommand::OnExecuteImpl`先调用`GetCharacterOrPlayerFromIndex`并检查角色有效性，故仅改事件作用域不能解决控制台报错。2026-10-13 13:19:25日志实际记录`event tca_tests.1`→`Player character not valid`，未进入总入口。程序`ReadAndExecuteEffect`在没有有效玩家时使用存活角色作为初始作用域，因此改用`effect`并在正式效果中显式解析天朝皇帝；不依赖引擎选择的初始角色。

原生回归源：`events/tca_test_entry_test_events.txt`，单项`tca_test_entry_test.1`。用例自行创建无地AI调用角色，直接检查正式host trigger和resolver：有效皇帝为正例、无地AI为反例、过时保存作用域被重新解析、调用角色不获得框架运行标记。用例不递归启动全组、不改写框架统计或运行标记来准备场景。加入入口用例时全组曾为105项／441断言；加入生命周期用例后曾为107项／451断言。

## 临时保护与死亡检测（2026-10-13）

全组在debug入口派发前调用`tca_test_begin_lifecycle_effect`：保护请求角色，并记录、保护当时`title:h_china.holder`。同一角色兼任二者时重复调用不覆盖所有权记录。独立`tca_test_death_protection`特质只声明`immortal = yes`，不复制原版`immortal`的相反特质、长久统治修正等附加项；原版`common/traits/_traits.info`明确该属性防自然死亡，但脚本仍可杀死角色。角色原有的`immortal`、`incapable`等特质不被替换；本次加入的保护用`tca_test_protection_added`记录，清理只撤掉本轮添加的保护，不删除原有同名保护。

正常结束（无论业务断言通过还是失败）先清理两个受监测角色的临时保护及死亡关联，再移除运行标记并汇总。原版`common/on_action/death.txt`说明`on_death`的root是即将死亡的角色；现有追加式`on_death`登记增加`tca_test_monitored_death`，仅处理带`tca_test_death_reporter`关联的角色。死亡会在关联请求者上记录`tca_test_lifecycle_death_detected`；若属于运行中的全组，记录`MONITORED_CHARACTER_DIED`及`SUITE_ABORTED`，清理保护、解除运行及延迟标记，保留断言计数作诊断，不发出通过汇总。

`tca_test_environment_intact_trigger`及`tca_test_validate_environment_effect`在全部延迟调度、结果续接及最终汇总前检查：请求者未中止且仍存活、没有死亡记录、原被测皇帝仍存活且仍持有天朝皇位。皇位更换也中止，避免新皇帝与旧准备作用域混用。各调度／续接事件在检查后仅于未中止时执行原有测试体；串行调度辅助同时检查环境。中止在原请求者及`h_china`上留下标记，玩家／观察者全组入口拒绝再次启动；必须新开专用测试局，不能手动清标记后让旧事件混入新一轮。日志工具遇到`SUITE_ABORTED`即返回NOT VERIFIED，即使此前已有完整断言和通过标记也不能宣称通过。

原生回归源`events/tca_test_lifecycle_test_events.txt`：`.1`六断言检查添加、重复保护、恢复、重复恢复、保留原有保护和原版immortal／incapable；`.2`通过正式`death = { death_reason = death_fight }`杀死一个受保护的临时角色，隔日四断言检查死亡、真实on_death记录、保护清理和不误中止真实测试请求者。死亡用例的关联请求者也是独立临时角色，不人为设置真实框架运行／统计标记，不直接调用死亡回调。新增一项即时、一项串行延迟，额外等待一日。

验收：重启1.20.0.4专用1066中国debug局，玩家或观察者入口运行全组，核对当前110项／485断言和同次error.log；测试期间承载者与原皇帝应有临时保护，完成后只撤掉测试添加的保护。在另一专用局等待阶段通过控制台脚本杀死受监测皇帝，应出现死亡／中止记录，存活承载者的保护被撤掉，原队列不再记录续接断言，日志工具返回NOT VERIFIED；再次启动被拒绝。非死亡皇位更换须在下一续接时中止。强制退出或引擎卡死时无法保证执行清理，测试存档不可转为正常游玩存档；原生自然死亡免疫及保存重载仍需另验。

## 测试状态窗口（2026-10-13）

玩家和观察者运行全组时自动出现独立、可拖动的“模组测试”窗口。显示运行中、已完成（全部通过／存在未通过）或已中止（受监测角色死亡／环境或皇位变化），以及已完成／总用例数、通过／失败／未执行计数。运行中提示继续推进日期，关闭按钮不可用；完成或中止后结果保留，点击关闭才隐藏。新一轮实际启动会重新打开窗口并刷新计数。没有当前用例名称或预计完成倒计时；不根据现实时间猜测测试完成。

计数快照由正式请求角色上的统计派生：已完成=通过+失败+未执行，不修改框架计数。启动、即时组派发后的等待通知、每项延迟结束的串行续接、最终结果及中止时调用`tca_test_update_status_effect`；显示数据保存在`title:h_china`的`tca_test_status_*`变量上，与皇帝本人分离，死亡后GUI不读取死者变量。最终状态来自正式汇总分支；中止快照在清理前保存。窗口显示“全部用例通过”只代表框架断言结果，仍需日志工具核对引擎错误；单项事件不自动改变全组窗口。

实现入口：`common/scripted_effects/tca_test_status_effects.txt`（通用快照写入、正式统计采集、关闭），`gui/tca_test_status.gui`（窗口），`gui/scripted_widgets/tca_test_status_widgets.txt`（自动创建登记）。窗口不依赖GetPlayer、GetHolder或观察者所选角色，不覆盖hud.gui或其他原版窗口。关闭按钮通过原版ExecuteConsoleCommand调用显式头衔作用域的关闭效果，只改变显示变量，不修改结果。运行中的关闭请求会被正式效果拒绝，防止误隐藏进度。

原版依据：`gui/scripted_widgets/_scripted_widgets.info`明确支持以文件／widget名称自动创建独立窗口；原版hud.gui及debug_menus.gui使用IsInGame，window_government_administration.gui使用Title.MakeScope.Var；debug_menus.gui使用ExecuteConsoleCommand。窗口样式组合参考本机Daddy Pika's Cheat Menu（Workshop 2986538297）的DI_main.gui及独立widget登记，属本机参考，不证明其全部内容与当前版本兼容。只新增本模组独立对象，没有同名原版覆盖。

原生回归`tca_test_status_test.1`在独立临时角色上直接调用正式快照和关闭效果，7个断言检查计数汇总、运行显示、运行中拒绝关闭、完成状态、关闭保留结果、死亡中止原因、新轮重新打开及清零。不修改真实框架统计或实际头衔显示数据。当前全组110项／485断言，串行延迟21项。

状态窗口原生断言已包含在本页最新全组验收中，实际界面仍须人工检查。重启专用1066中国debug局，在观察者入口运行全组：窗口应自动显示并持续更新；结束后应明确显示完成结果且不自行消失；关闭后再次实际启动应重新显示。另在专用局触发真实受监测死亡，窗口应保留中止原因与计数。还需验证简体中文／英文布局、拖动及关闭按钮。此窗口不处理非debug、前置不符或BUSY拒绝启动时的新状态，继续保留上一轮结果；以OBSERVER_ENTRY日志判断该次请求是否实际启动。

## 运行和维护

重启专用1066中国debug局，玩家模式用“调试：模组一键测试”或`event tca_tests.1`，观察者模式用`effect tca_run_observer_tests_effect = yes`。取消暂停推进到最终日志汇总；当前拘捕组单独串行增加200个游戏日，不沿用旧版四十八日时长。单项入口沿用各组事件ID；观察者运行角色事件时需附接收者运行时ID。测试会修改世界，不使用正常游玩存档。测试期间不切换玩家或并发启动。

直接编辑`events/tca_*_test_events.txt`。每项自备前置和状态，调用正式trigger/effect，通过if／limit检查结果；日志保留唯一tca_test_名称、连续CHECK编号及BEGIN／PASS／FAIL／PRECONDITION_FAIL。前置不满足计未执行，任何失败保留到用例结束。不要改写统计值来制造通过。

真实等待写成原生trigger_event的days参数，由后续角色事件检查。续接事件保留上下文，二十一项串行运行，不以直接调用正式worker替代自然触发。请求角色死亡、事件丢失或退出游戏时，无最终结果就是未完成。

新增用例在总入口`events/tca_tests_events.txt`登记并同步计划数量；延迟调度在该文件和`tca_test_delayed_dispatch_effects.txt`维护。日志工具从正式事件读取预期用例和编号，工具回归检查登记、连续编号和总数量。没有生成步骤。

检查命令：`python3 -m unittest discover -s tools -p 'test_*.py'`；游戏运行后用`python3 tools/check_test_run.py`，并审阅同次error.log。源码及静态通过不能当作引擎结果。

## 当前验收（2026-10-14 09:49）

独立1066中国观察者CLI局，仅加载主模组和启动适配模组，目录`run-m6q95reg`：110 BEGIN／110 PASS／485 CHECK_PASS，零失败或未执行，SUITE_ALL_PASSED。terminal.json确认观察者切换、summary终止、日志核对及工具退出码0；游戏进程在汇总后由工具强制终止（-9）。完整error.log无tca_记录，仍有原版背景错误，不能称全游戏无错误。

拘捕即时收押检查保留；第20日检查与本用例观察标识绑定的在押、释放或死亡证据。独立观察用例8断言，包括保留其他囚犯旧证据后仍拒绝缺证据目标的两个反例。修复前这两个断言实际失败，修复后均通过。详见[当前拘捕契约](judicial_arrest_native_tests.md#当前观察契约)。CLI不覆盖原版赎回、释放或处决互动。90项Python工具测试及原版覆盖检查通过。界面、自然AI概率、长期拘押和保存重载仍须另行验收。

## 历史记录

此前失败复现、临时隔离方案及旧版验收结果保留在[历史记录](history/mod_tests_history.md)，不作为当前实现说明。

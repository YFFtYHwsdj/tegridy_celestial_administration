# 原生测试框架与用例编写

运行参数与结果文件见[测试运行](README.md)；本页只维护原生登记、调度、日志和状态生命周期。

## 当前结构

测试直接维护为CK3原生隐藏事件，不使用Python生成器，也不保留另一套P脚本中间源。`events/`下的测试文件就是正式测试代码，`common/scripted_effects/tests/fixtures/tca_judicial_law_test_effects.txt`是共享场景准备，Python仅用于读取日志和静态检查。

实际用例和断言范围以原生模块登记及该次冻结计划为准。模块登记位于`common/scripted_effects/tests/modules/tca_test_modules_*_effects.txt`，模块顺序位于`common/scripted_effects/tests/framework/tca_test_catalog_effects.txt`，通用派发位于`common/scripted_effects/tests/framework/tca_test_dispatch_effects.txt`，延迟续接与lane结束位于`common/scripted_effects/tests/framework/tca_test_delayed_dispatch_effects.txt`及`common/scripted_effects/tests/framework/tca_test_lane_effects.txt`；`events/tests/tca_tests_events.txt`仅保留入口、续接与汇总。通判生命周期及当前验证边界见[通判实现与验证](../tongpan/implementation.md)。路级法理与真实庄园回归见[司法辖区记录](../judicial/verification.md)。原生拘捕组直接发送真实审批请求，检查即时收押和第20日的匹配观察证据；世族批准/否决场景核对实际领主与庄园路不同，迁移场景核对旧审批失效。观察证据用例使用真实释放／死亡回调，并包含跨囚犯旧证据反例。测试范围及结果见[原生拘捕文档](../judicial/verification.md)。

## CLI 自动执行

macOS 可运行`python3 tools/run_game_tests.py`，自动建立独立1066观察者测试局并执行下述正式入口。每次使用全新日志目录，完成后调用正式日志核对；引擎错误会导致非零退出码。运行方式、原生适配、已验证范围与限制见[CLI 测试说明](README.md)。

## 观察者入口

在专用1066中国debug测试局进入观察者模式后，控制台执行：

```text
effect tca_run_observer_tests_effect = yes
```

无需查找角色ID或临时切换玩家。`tca_run_observer_tests_effect`检查debug、1066开局及有效天朝皇帝，再由`tca_test_resolve_observer_host_effect`固定选择`title:h_china.holder`承载`tca_tests.1`。测试统计、运行标记及延迟lane状态保存在该角色上；不使用控制台的默认角色。原有玩家决议、`event tca_tests.1`及各组单项入口保持不变。

入口发现任一存活角色已有全组或延迟用例运行标记时，只记录`TCA_TEST OBSERVER_ENTRY_BUSY`，不重置统计。前置不满足记录`TCA_TEST OBSERVER_ENTRY_REJECTED`；成功调用记录`TCA_TEST OBSERVER_ENTRY_DISPATCH`，随后必须出现新的`SUITE_DISPATCH`。该入口允许玩家模式使用，但也固定选择天朝皇帝，不将玩家当前角色自动作为测试请求者。

观察者继续正常推进游戏日期，直到日志出现`SUITE_ALL_PASSED`或`SUITE_NOT_ALL_PASSED`，再运行`python3 tools/check_test_run.py`并审阅同次`error.log`。通知面向承载角色，不依赖观察者能看到通知。不得在运行中切换玩家、并发执行另一组测试或使用正常游玩存档。承载者或皇帝死亡、皇位更换时主动中止，详见下节；事件丢失、日期不推进或游戏退出造成缺少终局结果时仍是未完成，不自动换人接续或伪造通过。

依据：本机CK3 1.20.0.4原版`events/_events.info`支持`scope = none`，但Mac arm64程序`SEventConsoleCommand::OnExecuteImpl`先调用`GetCharacterOrPlayerFromIndex`并检查角色有效性，故仅改事件作用域不能解决控制台报错。2026-10-13 13:19:25日志实际记录`event tca_tests.1`→`Player character not valid`，未进入总入口。程序`ReadAndExecuteEffect`在没有有效玩家时使用存活角色作为初始作用域，因此改用`effect`并在正式效果中显式解析天朝皇帝；不依赖引擎选择的初始角色。

原生回归源：`events/tests/tca_test_entry_test_events.txt`，单项`tca_test_entry_test.1`。用例自行创建无地AI调用角色，直接检查正式host trigger和resolver：有效皇帝为正例、无地AI为反例、过时保存作用域被重新解析、调用角色不获得框架运行标记。用例不递归启动全组、不改写框架统计或运行标记来准备场景。

## 并发 lane 与用例隔离

`--parallel K`（默认1，合法范围1至32）允许同一进程、同一世界的多条延迟用例链并发执行，以减少等待游戏日相加的墙钟；K是同时运行的延迟用例上限，不是用例数或线程数。并发单元是模块：一个测试文件的事件命名空间（如`tca_retirement_state`）通常即一个GROUP，一个GROUP的延迟用例构成一条lane，同一GROUP同时最多运行1个延迟用例，不同GROUP之间可并发。即时用例仍在同步阶段一次派发，不占lane，也不受K限制。

模块登记统一写明GROUP与EXCLUSIVE：

```text
tca_test_visit_case_effect = { EVENT = tca_x_test.1 CASE = tca_test_x_demo DELAYED = yes GROUP = tca_x_test EXCLUSIVE = no }
```

`GROUP`只使用`[a-z0-9_]`，默认取事件ID的命名空间；同一命名空间只能对应一个GROUP。需要共用报告者状态的模块可以跨文件合并为同一GROUP（如州郡兼领法两个测试文件与保存重载探针共用`tca_local_domain_realm`，退休资格与退休AI两组共用`tca_retirement_law`（同翻`celestial_retirement_law_*`法），merit议席探针两组共用`tca_merit_probe_seat`：后者争用同一原生议席，司法家族中审录、司法时限、辖区、帝直属与拒捕六组共用`tca_judicial_realm`：同写司法制度重置夹具的共享状态，功绩年度、维护、多国与反馈四组共用`tca_merit_annual_worker`：同用全局年度锁、全局候选池与天子工作账），合并后这些模块的延迟用例同处一条lane。即时用例同样登记GROUP，以便统一检查命名空间。`EXCLUSIVE = yes`表示独占用例，语义见下文。

### 调度状态与认领

报告者`title:h_china.holder`上的`var:tca_test_max_active`保存本轮K，缺省1：CLI适配按`--parallel`在入口前注入，手动运行未注入或值小于1时按1处理；`var:tca_test_active_count`记录在途延迟用例数；`var:tca_test_undispatched`记录已选择但尚未派发的延迟用例数；`var:tca_test_dispatch_phase`沿用阶段0计数、1即时、2延迟、3清理。

角色flag中，`tca_test_lane_<GROUP>_active`表示该lane有在途延迟用例，`tca_test_exclusive_active`表示独占用例在途，`tca_test_delayed_case_active`只表示“存在任意在途延迟用例”，供入口、即时派发和环境判断读取；单个用例仍使用`tca_test_<CASE>_dispatched`防止重复派发。用例体不再自行增删`tca_test_delayed_case_active`。

延迟阶段每次扫描按登记顺序认领，条件为：已选择、尚未派发、`var:tca_test_undispatched > 0`、`var:tca_test_active_count < var:tca_test_max_active`、本GROUP的lane空闲且没有独占用例在途；`EXCLUSIVE = yes`还要求当前活跃数为0。认领后依次标记已派发、未派发数减1、占用lane、活跃数加1（活跃数由0变1时同时标记全局active flag），独占用例再置独占标记，最后触发用例事件。扫描结束后未派发数与活跃数都为0才进入统一收尾。

### 结束与独占

延迟用例在正常完成、前置失败或环境清理时调用`tca_test_lane_end_effect = { GROUP = <GROUP> }`（报告者作用域），不再直接调用`tca_test_continue_delayed_effect`。该效果移除本用例的lane flag与独占标记，活跃数减1（已有负值保护，重复结束不继续递减），归零时移除`tca_test_delayed_case_active`，再调用`tca_test_continue_delayed_effect`触发下一轮扫描。效果只释放本GROUP的lane占用，不触碰其它lane；用例不得自行清洗计数或提前结束其它lane。

`EXCLUSIVE = yes`的用例在派发时要求当前活跃数为0，且在其结束前不再认领任何其它延迟用例，因此独占期间整轮延迟链串行。静态检查对共享作用域（`title:h_china`、`title:h_china.holder`、全局变量；含夹具间接写入）上的变量与角色flag做写-写冲突检测：只有两个及以上不同GROUP的“延迟且非独占”用例写同一个状态键时才报违规；同GROUP的延迟用例串行、独占用例与其它延迟用例互斥、即时用例在同步阶段先于延迟阶段执行，因此都不参与冲突集合。检查器不跟踪读取与原生法则状态，读-写耦合仍须人工判断并以K>1引擎对照验证。当前独占清单如下，新增同类场景必须设置独占并更新本节：

- 保存重载探针`tca_test_merit_saveload_contract`：保存、重载及续局阶段不能被其它用例的世界写入干扰；与州郡兼领法同属`tca_local_domain_realm`。
- 玩家会话`tca_test_retirement_player_session`：等待人工接管玩家，结束时间不受框架控制。
- 州郡兼领法开局快照的延迟用例`tca_test_local_domain_immediate`与`tca_test_local_domain_native`：必须早于其它用例对历史人物的改制／返境操作，保持串行时的开局快照语义。
- 拘捕组：`tca_test_arrest_commissioner_family_veto`、`tca_test_arrest_commissioner_family_approval`、`tca_test_arrest_commissioner_no_family_veto`、`tca_test_arrest_commissioner_no_family_approval`、`tca_test_arrest_family_only_veto`、`tca_test_arrest_family_only_approval`、`tca_test_arrest_landless_office_family_veto`、`tca_test_arrest_landless_office_family_approval`、`tca_test_arrest_landless_office_no_family_veto`、`tca_test_arrest_landless_office_no_family_approval`（写`tca_court_system_cooldown`、`tca_court_system_migrated_v2`）。
- 司法共享状态组`tca_judicial_realm`：`tca_custody_review_test`、`tca_judicial_timing_test`、`tca_judicial_estate_test`、`tca_judicial_de_jure_test`、`tca_judicial_imperial_test`、`tca_judicial_refusal_test`的延迟用例共用一条lane：它们都经夹具在`title:h_china.holder`上重置`tca_court_system_cooldown`、`tca_court_system_migrated_v2`与司法制度法条，合并后组内串行、不再全局阻塞。其中`tca_test_judicial_delayed_law_disabled`、`tca_test_judicial_delayed_law_enabled`、`tca_test_judicial_delayed_commissioner_death`与`tca_test_review_send_resolution`保留`EXCLUSIVE = yes`：前两者在2游戏日窗口内核对司法机构法翻转后的绑定与失效状态，`commissioner_death`核对提刑死亡后的接续，`review_send_resolution`核对原生详覆互动的3日结果；K=4对照显示这些续接断言在并发下会缺失或重复，故保留独占。
- 功绩年度组`tca_merit_annual_worker`：`tca_merit_annual_test`、`tca_merit_state_test`、`tca_merit_multicountry_test`、`tca_merit_feedback_test`的延迟用例共用一条lane：同写全局年度锁`tca_merit_annual_processed_year`/`tca_merit_annual_run_count`、全局候选池（`tca_ma_*`）与天子`primary_title`工作账，合并后组内串行、不再全局阻塞。其中`tca_test_merit_maintenance_idempotence`与`tca_test_merit_multicountry`保留`EXCLUSIVE = yes`：它们强制回拨年度锁并在任意游戏日调用真实年度worker，对全世界人物做merit结算，须避免其它lane在途时被改写。`tca_test_merit_annual_pulse`、`tca_test_merit_annual_draw`、`tca_test_merit_annual_natural`、`tca_test_merit_legacy_ruler_cap`已不再独占。
- 通判法翻转组：`tca_test_tongpan_static_peer_diarchy`、`tca_test_tongpan_lifecycle`、`tca_test_office_native_income`、`tca_test_office_funding`、`tca_test_office_funding_multimonth`：翻转通判法并刷新官职（`tca_tongpan_enabled_law`／`tca_tongpan_disabled_law`，调用`tca_refresh_tongpan_realm_effect`），独占以隔离原生官职重建。
- 退休资格边界`tca_test_retirement_eligibility`：在`tca_retirement_law` lane内翻`celestial_retirement_law_*`法条（窗口≈2游戏日），独占以隔离法条状态与时序。

科举`tca_test_exam_pending`写`title:h_china`上的`tca_exam_cooldown`，写者仅本lane，经K=4全量对照未出现新增确定性差异后不再独占。

### 新增用例

- 在所属模块登记`EVENT`、唯一`CASE`、`DELAYED`、`GROUP`与`EXCLUSIVE`；新用例的状态变量和角色flag带所属模块命名空间（如`tca_test_<命名空间>_*`），失败flag为`tca_test_<命名空间>_case_failed`，不再使用共享的`tca_test_case_failed`。
- 等待仍用原生`trigger_event`的`days`参数续接，不用直接调用正式worker或循环检查代替自然触发。
- 延迟用例结束时调用`tca_test_lane_end_effect = { GROUP = <GROUP> }`；不增减`tca_test_delayed_case_active`，不直接调用`tca_test_continue_delayed_effect`。由`trigger_event`链式调用的纯续接事件不是独立登记用例，其失败flag和lane结束调用沿用宿主用例的模块命名空间与GROUP。
- 写共享状态的延迟用例——`title:h_china`、报告者上的共享状态、全局变量，或任何其它模块可能同时读取的状态——默认`EXCLUSIVE = yes`并登记到上节；只有在确认其它非独占延迟lane既不写也不依赖该状态、且有K>1引擎对照证据后，才可去掉独占，或把竞争的GROUP合并为同一GROUP（合并后同lane串行）而不作全局阻塞。即时用例在同步阶段执行，不占lane。
- 涉及保存重载、真实玩家会话、开局快照顺序的用例默认独占，不得利用lane并发。
- 新增或修改登记后运行`python3 tools/check_test_parallel.py`，核对注册元数据、裸全局标识、lane flag与结束调用一致、跨GROUP状态名冲突、共享状态跨GROUP写冲突、失败flag配对及触发链归属；检查器白名单只用于已确认的框架共享状态，新增条目必须写明理由，不得用白名单代替合并GROUP或独占。检查通过不代表引擎验证通过。

### 等价与当前边界

`--parallel 1`为默认值，每轮扫描至多认领一个延迟用例，调度顺序、等待和断言与改造前全组串行逐项等价；`--parallel K`只改变在途延迟用例数，不改变用例集合、等待天数和断言。K>1的逐用例结果不能替代同范围串行结果作为验收依据，等价性须用[测试运行](README.md#并行运行)中的对比工具逐项核对。

并发安全目前依靠lane分组、状态命名空间、独占清单和静态检查维持，没有运行时共享状态守卫：派发和结束效果不会检测两条lane是否写同一共享对象，也不会在冲突时中止或降级，跨模块共享对象仍须人工判断并合并到同一GROUP或改为独占。运行时守卫尚未实现，若以后加入需同步修改本节与检查器。

## 临时保护与死亡检测

全组在debug入口派发前调用`tca_test_begin_lifecycle_effect`：保护请求角色，并记录、保护当时`title:h_china.holder`。同一角色兼任二者时重复调用不覆盖所有权记录。独立`tca_test_death_protection`特质只声明`immortal = yes`，不复制原版`immortal`的相反特质、长久统治修正等附加项；原版`common/traits/_traits.info`明确该属性防自然死亡，但脚本仍可杀死角色。角色原有的`immortal`、`incapable`等特质不被替换；本次加入的保护用`tca_test_protection_added`记录，清理只撤掉本轮添加的保护，不删除原有同名保护。

正常结束（无论业务断言通过还是失败）先清理两个受监测角色的临时保护及死亡关联，再移除运行标记并汇总。原版`common/on_action/death.txt`说明`on_death`的root是即将死亡的角色；现有追加式`on_death`登记增加`tca_test_monitored_death`，仅处理带`tca_test_death_reporter`关联的角色。死亡会在关联请求者上记录`tca_test_lifecycle_death_detected`；若属于运行中的全组，记录`MONITORED_CHARACTER_DIED`及`SUITE_ABORTED`，清理保护、解除运行及延迟标记，保留断言计数作诊断，不发出通过汇总。

`tca_test_environment_intact_trigger`及`tca_test_validate_environment_effect`在全部延迟调度、结果续接及最终汇总前检查：请求者未中止且仍存活、没有死亡记录、原被测皇帝仍存活且仍持有天朝皇位。皇位更换也中止，避免新皇帝与旧准备作用域混用。各调度／续接事件在检查后仅于未中止时执行原有测试体；lane结束与续接辅助同样先检查环境。中止在原请求者及`h_china`上留下标记，玩家／观察者全组入口拒绝再次启动；必须新开专用测试局，不能手动清标记后让旧事件混入新一轮。日志工具遇到`SUITE_ABORTED`即返回NOT VERIFIED，即使此前已有完整断言和通过标记也不能宣称通过。

原生回归源`events/tests/tca_test_lifecycle_test_events.txt`：`.1`六断言检查添加、重复保护、恢复、重复恢复、保留原有保护和原版immortal／incapable；`.2`通过正式`death = { death_reason = death_fight }`杀死一个受保护的临时角色，隔日四断言检查死亡、真实on_death记录、保护清理和不误中止真实测试请求者。死亡用例的关联请求者也是独立临时角色，不人为设置真实框架运行／统计标记，不直接调用死亡回调。新增一项即时、一项延迟用例，额外等待一日。

验收：重启当前1.20.1专用1066中国debug局，玩家或观察者入口运行全组，核对该次冻结计划、全部结果和同次error.log；测试期间承载者与原皇帝应有临时保护，完成后只撤掉测试添加的保护。在另一专用局等待阶段通过控制台脚本杀死受监测皇帝，应出现死亡／中止记录，存活承载者的保护被撤掉，原队列不再记录续接断言，日志工具返回NOT VERIFIED；再次启动被拒绝。非死亡皇位更换须在下一续接时中止。强制退出或引擎卡死时无法保证执行清理，测试存档不可转为正常游玩存档；原生自然死亡免疫及保存重载仍需另验。

## 测试状态窗口

玩家和观察者运行全组时自动出现独立、可拖动的“模组测试”窗口。显示运行中、已完成（全部通过／存在未通过）或已中止（受监测角色死亡／环境或皇位变化），以及已完成／总用例数、通过／失败／未执行计数。运行中提示继续推进日期，关闭按钮不可用；完成或中止后结果保留，点击关闭才隐藏。新一轮实际启动会重新打开窗口并刷新计数。没有当前用例名称或预计完成倒计时；不根据现实时间猜测测试完成。

计数快照由正式请求角色上的统计派生：已完成=通过+失败+未执行，不修改框架计数。启动、即时组派发后的等待通知、每项延迟用例结束后的续接、最终结果及中止时调用`tca_test_update_status_effect`；显示数据保存在`title:h_china`的`tca_test_status_*`变量上，与皇帝本人分离，死亡后GUI不读取死者变量。最终状态来自正式汇总分支；中止快照在清理前保存。窗口显示“全部用例通过”只代表框架断言结果，仍需日志工具核对引擎错误；单项事件不自动改变全组窗口。

实现入口：`common/scripted_effects/tests/framework/tca_test_status_effects.txt`（通用快照写入、正式统计采集、关闭），`gui/tca_test_status.gui`（窗口），`gui/scripted_widgets/tca_test_status_widgets.txt`（自动创建登记）。窗口不依赖GetPlayer、GetHolder或观察者所选角色，不覆盖hud.gui或其他原版窗口。关闭按钮通过原版ExecuteConsoleCommand调用显式头衔作用域的关闭效果，只改变显示变量，不修改结果。运行中的关闭请求会被正式效果拒绝，防止误隐藏进度。

原版依据：`gui/scripted_widgets/_scripted_widgets.info`明确支持以文件／widget名称自动创建独立窗口；原版hud.gui及debug_menus.gui使用IsInGame，window_government_administration.gui使用Title.MakeScope.Var；debug_menus.gui使用ExecuteConsoleCommand。窗口样式组合参考本机Daddy Pika's Cheat Menu（Workshop 2986538297）的DI_main.gui及独立widget登记，属本机参考，不证明其全部内容与当前版本兼容。只新增本模组独立对象，没有同名原版覆盖。

原生回归`tca_test_status_test.1`在独立临时角色上直接调用正式快照和关闭效果，7个断言检查计数汇总、运行显示、运行中拒绝关闭、完成状态、关闭保留结果、死亡中止原因、新轮重新打开及清零。不修改真实框架统计或实际头衔显示数据。

状态窗口原生断言验证数据契约，实际界面仍须人工检查。重启专用1066中国debug局，在观察者入口运行全组：窗口应自动显示并持续更新；结束后应明确显示完成结果且不自行消失；关闭后再次实际启动应重新显示。另在专用局触发真实受监测死亡，窗口应保留中止原因与计数。还需验证简体中文／英文布局、拖动及关闭按钮。此窗口不处理非debug、前置不符或BUSY拒绝启动时的新状态，继续保留上一轮结果；以OBSERVER_ENTRY日志判断该次请求是否实际启动。

## 运行和维护

重启专用1066中国debug局，玩家模式用“调试：模组一键测试”或`event tca_tests.1`，观察者模式用`effect tca_run_observer_tests_effect = yes`。取消暂停推进到最终日志汇总；当前拘捕组单独串行增加200个游戏日，不沿用旧版四十八日时长。单项入口沿用各组事件ID；观察者运行角色事件时需附接收者运行时ID。测试会修改世界，不使用正常游玩存档。测试期间不切换玩家，也不并发启动另一组测试；同局内的延迟lane并发由框架调度，不作为手动操作。

直接编辑`events/tests/tca_*_test_events.txt`。每项自备前置和状态，调用正式trigger/effect，通过if／limit检查结果；日志保留唯一tca_test_名称、连续CHECK编号及BEGIN／PASS／FAIL／PRECONDITION_FAIL。前置不满足计未执行，任何失败保留到用例结束。不要改写统计值来制造通过。

真实等待写成原生trigger_event的days参数，由后续角色事件检查。续接事件保留上下文，所选延迟用例按登记的GROUP进入lane；默认`--parallel 1`时仍按登记顺序逐个执行，K>1的并发与独占见[并发 lane 与用例隔离](#并发-lane-与用例隔离)。不以直接调用正式worker替代自然触发。请求角色死亡、事件丢失或退出游戏时，无最终结果就是未完成。

新增用例在所属`tca_test_modules_*_effects.txt`中以`EVENT`、唯一`CASE`日志名称、`DELAYED = yes/no`、`GROUP`及`EXCLUSIVE`登记，并按[并发 lane 与用例隔离](#并发-lane-与用例隔离)维护状态命名空间与独占登记。仅新增模块时调整`common/scripted_effects/tests/framework/tca_test_catalog_effects.txt`的模块顺序；即时顺序和延迟顺序分别维护。不要手工更新总数量或分配全局阶段编号。日志工具交叉检查原生登记、正式用例、连续断言编号和冻结计划；GUI重载首帧等无法等待角色事件的同步断言仍维护在测试夹具效果中，静态索引同时扫描`common/scripted_effects/tests/`，不另造孤立占位事件。没有生成步骤。即时用例当场完成；延迟用例调用`tca_test_lane_end_effect`释放本lane占用并进入续接。共享夹具说明前置、修改对象、清理和环境损坏条件。

检查命令：`python3 -m unittest discover -s tools -p 'test_*.py'`；游戏运行后用`python3 tools/check_test_run.py`，并审阅同次error.log。源码及静态通过不能当作引擎结果。



## 证据与完整玩法验收

每轮产物保存在仓库外，按[开发规范](../development/README.md)筛选长期结论。不为普通通过新增逐轮文档，不让模块说明重复维护测试计数。手工 UI、真实玩家发送、自然 AI、延迟原始触发路径与保存重载须补充可复现验收；直接 worker 或维护效果的断言不替代这些路径。

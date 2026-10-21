# 通判实现与验收

## 2026-10-21 治理收益系数提高至0.5（当前实现）

按用户决定，`tca_tongpan_efficiency_value`由称职度乘0.4改为乘0.5再除100：每点称职度增加0.5个百分点，最高增加50个百分点；50／70／100称职度分别增加25／35／50个百分点。满值50个百分点与原生治理效率±50%的口径一致，原生最终0.5至1.5限幅未改动。中英使命说明同步为每10点增加5个百分点、上限50个百分点，动态浮窗继续读取正式值。称职度、资金、俸禄与分权规则沿用既有实现。

考虑过0.6（每点0.6、上限60），但其满值超出原生±50%口径；普通知州原生约0.9–1.1时，多出的部分多数会被1.5上限截断，故停在0.5。

原生回归更新`events/tests/tca_tongpan_test_events.txt`第6、32、53及55断言，分别覆盖收益上限、原生最终／展示效率的实际增量、在任满称职度0.5收益，以及满收益下最终效率仍封顶1.5；零称职度第54断言保持为0。

本轮`python3 tools/run_game_tests.py --case tca_tongpan_test.1 --seed 1538798675 --timeout 240`：`run-a8h0at_k`，CK3 1.20.1.1、独立1066中国观察者，仅冻结主模组及CLI适配，1 BEGIN／1 PASS／58 CHECK_PASS，零失败或未执行；observer、summary确认，verification_exit及runner_exit均为0，result及同次日志核对通过，未检出模组相关引擎错误；第6、32、53、55断言均通过。首次`run-dr0l9ume`因编辑后脚本与本地化缺少UTF-8 BOM，同次日志报encoding错误及未知本地化键`tca_tongpan_reform_cooldown`，虽58断言通过但整轮NOT VERIFIED；恢复BOM后重跑取得上述结果。

本轮为参数调整，更新既有原生预期后验证新数值，没有声称完成缺陷的失败到通过复现；未重跑全组。186项工具测试与上游覆盖检查通过。实际浮窗渲染、保存重载与长期平衡仍待验收。

## 2026-10-18 契约清理后的全组候选一致性失败（待查）

当前官职契约已直接命名提刑／通判，移除武官预留；通判生命周期第4项改为检查通判专属身份标记，其余断言未放宽。完整独立1066观察者局 `/private/tmp/tca-contract-cleanup-full/run-s8tlib4o`（CK3 1.20.1.1 macOS ARM64、种子1538798675，仅主模组及CLI适配）120 BEGIN、119 PASS、1 FAIL，722 CHECK_PASS、1 CHECK_FAIL。失败是 `tca_test_tongpan_lifecycle` 第46项：死亡前 `every_title_heir` 枚举20人，首位ID66993；实际接任者ID66538不在该预览名单中。第23项即时继任、第24项有效绑定及第47项分权继续使用实际接任者均通过。观察者和summary确认、源码快照无变化，日志未检出模组相关引擎错误；runner／verification退出码1，整轮 NOT VERIFIED。

未改玩法后，单独运行同用例 `/private/tmp/tca-contract-cleanup-tongpan/run-2i4txqs4` 为1用例／58断言全部通过，观察者、summary、快照及同次日志核对通过，runner／verification退出码0。该结果只能说明独立场景通过，不能消除全组场景的失败或证明契约变化与其无关。本轮保留第46项及全部原始断言，没有强制任命预览人选，也未调整候选评分或继承法。

原版 `common/defines/00_defines.txt` 的 `MIN_HEIR_TO_FIND = 20` 规定继承搜索门槛；它与本次枚举人数相符，但仅凭这一点不能认定截断或缓存就是原因。当前仍待定位为何全组场景的实际接任者落在死亡前预览之外；后文既往全组通过记录不覆盖本次失败。契约好感36断言独立及全组均通过，具体验证见[无地官员契约](official_contracts.md)。

## 2026-10-17 提交前最终检查（历史：0.4 系数源码）

本次审阅通判整合、司法入口附费、原版覆盖与测试工具，修正README中残留的0.35收益及已停用独立分权继任说明，并更新统一测试文档当前计数和历史链接。未修改本轮引擎运行所用的玩法源码。

`python3 tools/run_game_tests.py --seed 1538798675 --timeout 360`运行`run-g38988_r`：CK3 1.20.1.1、独立1066中国观察者，仅冻结主模组及CLI适配，117 BEGIN／117 PASS／638 CHECK_PASS，零FAIL、CHECK_FAIL或PRECONDITION_FAIL。terminal确认observer和summary，verification_exit及runner_exit均为0，源码副本无变化；result、debug.log与error.log核对未检出模组相关引擎错误。快照玩法文件与提交前工作目录逐文件哈希一致，运行源码SHA-256为`5525f21996f46cd872d41548fa03b3194d1caca0ba76386ea3b0a2cb944aa921`。运行目录：`/private/var/folders/f0/dh90nqcx6rsgf1558f91wmz40000gn/T/tca-game-tests/run-g38988_r/`。

同次日志另以`check_test_run.py --strict-title-heir`核对，仍因实际接任者不同于死亡前预览首位而退出1、NOT VERIFIED；标准全组通过不能覆盖这一限制。真实窗口GOVERNOR与END_SYSTEM阶段的既有失败仍保留，本轮未重跑GUI探针；隐藏的结束互动没有被视作可用功能。界面、真实鼠标操作、保存重载及长期平衡未验收。

126项Python工具测试及上游覆盖检查通过（24项对象覆盖／27项追加／1项辅助／2项整文件），基线未刷新。62个改动或新增脚本、GUI和本地化文件的结构／编码检查通过，中英键名匹配；从本机原版`/Users/tegridy/Library/Application Support/Steam/steamapps/common/Crusader Kings III/game`在临时目录重新生成3,442个官职、128个预留位，五份产物与正式文件逐字一致。暂存空白检查保留原版复制区及基线的CRLF格式；允许CRLF后仍有34处空白／缩进提示，均位于复制原版的区段或基线，不是新增玩法语句；未为消除提示改写原版基线。根目录`.DS_Store`不纳入提交。

## 2026-10-16 治理收益系数提高至0.4（历史；已由0.5替代）

按用户要求，`tca_tongpan_efficiency_value`由称职度乘0.35改为乘0.4再除100：每点称职度增加0.4个百分点，最高增加40个百分点；51／80／100称职度分别增加20.4／32／40个百分点。原生最终治理效率仍限制为0.5至1.5。中英使命说明同步为每10点增加4个百分点、上限40个百分点，动态浮窗继续读取正式值。本轮只调整收益系数及对应说明，称职度、资金与俸禄规则沿用既有实现。

原生回归仍直接编辑`events/tests/tca_tongpan_test_events.txt`：更新第6、32、53及55断言，分别覆盖收益上限、原生最终／展示效率的实际增量、在任满称职度0.4收益，以及满收益下最终效率仍封顶1.5；零称职度第54断言保持为0，保留原有容差。当前登记仍为117项／638断言，生命周期单项58断言。

本轮`python3 tools/run_game_tests.py --case tca_tongpan_test.1 --seed 1538798675 --timeout 240`：`run-bn1h_4wm`，CK3 1.20.1.1、独立1066中国观察者、种子1538798675，仅冻结主模组及CLI适配，1 BEGIN／1 PASS／58 CHECK_PASS，零失败或未执行；observer、summary确认，源码副本无变化，terminal中verification_exit及runner_exit均为0，result及同次日志核对通过，未检出模组相关引擎错误。126项工具测试、上游覆盖、BOM与空白检查通过。首次沙箱内`run-pwhntqq5`在2秒时退出，未确认观察者、无测试派发，NOT VERIFIED；stdout记录Steam初始化失败，改用正常图形／Steam会话后完成上述复测。

本轮为参数调整，更新既有原生预期后验证新数值，没有声称完成缺陷的失败到通过复现；未重跑117项全组。实际浮窗渲染、保存重载与长期平衡仍待验收。此前严格首位继任、真实窗口及结束制度的未通过项目见下节；本轮数值调整不构成这些项目的验收。

## 2026-10-16 测试完整性增强（此前验收）

本轮仅完善测试、运行工具及文档，没有修改正式玩法或界面。当前登记仍为117项，断言从632增至638；通判生命周期由52增至58。新增原生断言53至58依次验证：实际在任满称职度加成0.35、实际在任零称职度加成0、原生最终治理效率上限1.5、夹具恢复原有绑定、界面评分helper等于原生任命评分，以及空官职评分为0。前三项直接使用正式效率计算及真实官职／分权关系，避免以非在任零值或Python规则代替业务结果。

每轮冻结主模组及适配源码，保存逐文件SHA-256，核对启动及结束时副本；断言计数读取同次副本，旧目录没有快照会明确警告。新增`--strict-title-heir`可将既有“死亡前首位与实际接任者不同”的诊断升级为验收失败，不再把候选归属通过误作严格首位继任通过。工具126项及上游覆盖检查通过；基线未刷新。

原生回归过程：单项`run-vfapg11a`的56条断言全部通过。完整局`run-rvqcdnbs`及`run-k_6951oo`均为117 BEGIN／116 PASS／637 CHECK_PASS／1 CHECK_FAIL，仅新增58失败，整轮NOT VERIFIED。第一次清除局部别名仍在失败作用域中看到继承的官职别名；第二次显式指定共享`c_tca_tongpan_probe`，但该头衔已被其他测试使用，不能假定为空。现改为在本用例拥有的官职上调用正式销毁效果，并同时断言无持有者与评分为0；零值预期未放宽。最后复测结果见下文。

最后复测`run-yu1ox72u`：CK3 1.20.1.1、独立1066中国观察者、种子1538798675，仅冻结主模组及CLI适配，入口全组并启用`--strict-title-heir`。117 BEGIN／117 PASS／638 CHECK_PASS，零CHECK_FAIL及PRECONDITION_FAIL，包含修正夹具后的第58断言；observer、summary确认，源码快照无变化，同次日志核对未检出模组相关错误。但实际接任者仍与死亡前首位不同，严格门槛失败，verification_exit及runner_exit均为1，整体NOT VERIFIED。运行源码SHA-256为`353b2288c033a9ffe73b405522d63bd8bb94a66532d17b2067f1732dd24984c9`，terminal、result及日志保存在`/private/var/folders/f0/dh90nqcx6rsgf1558f91wmz40000gn/T/tca-game-tests/run-yu1ox72u/`。这证明新增边界断言通过及严格门槛能在真实引擎结果上拦截差异，不证明严格首位继任已修复。

真实窗口探针`run-8_0afe2z`完成七阶段，WINDOW、SELF、LIEGE、TONGPAN、RETURN共5阶段PASS，GOVERNOR及END_SYSTEM为FAIL，terminal与result均为NOT VERIFIED。首次按固定夹具知州打开后的目标／权限／选中组合核对未通过，具体子条件尚未唯一定位；随后正式标签回调的自己、领主、通判及返回核对通过。正式结束互动不可用，未执行后续两日清理断言；当前`tca_tongpan_end_interaction`的`is_shown = { always = no }`与此结果一致。本轮没有绕过互动或放宽预期来获得通过。

探针使用固定ID打开真实窗口，再执行正式标签onclick及down表达式；不包含HUD点击。阶段失败仍继续后续步骤，原生夹具标记只去重PASS，保留所有FAIL。静态几何契约检查继任网格横向填充及单元结构，可检出此前纵向展开的配置退化；不等于渲染验收。真实鼠标命中、底图像素、悬停、本地化渲染、皇帝／知州玩家视角、保存重载仍待人工验收。自动切换通过也不能代替这些项目。

结束分权按钮的图标与文案：tca_tongpan_end_interaction补上原版icon_dismiss_entrenched_regency，GUI继续通过GetCharacterInteraction.GetIcon读取，无需另画图标或覆盖按钮。中文分权类型名为“通判制度”，原版按钮据此显示“结束通判制度”，交互标题同步为“结束通判制度”（英文Tongpan System／End the Tongpan System），中英描述均引用原版liege_dismiss_entrenched_regency_interaction_desc，沿用人物称谓、强调标记及原版叙述。依据为本机原版绝对目录/Users/tegridy/Library/Application Support/Steam/steamapps/common/Crusader Kings III/game/common/character_interactions/00_diarch_interactions.txt中的解除固化摄政互动及对应中英本地化。本次只补图标及文本，既有隐藏、启用与结束逻辑不改；116项工具测试、上游覆盖、BOM及空白检查通过，未重跑引擎业务组。实际按钮图标和悬停仍待重载确认。

2026-10-16，当前本机CK3 1.20.1.1。初版已实现，此前标准CLI完整回归117项／632断言通过；当前117项／638断言通过，但严格首位继任门槛失败，整轮NOT VERIFIED；通判继任名单改为直接读取官职头衔顺位，通判入口接入原版HUD自动排列，并新增三个关系标签（界面待验证）；此前0.35系数的通判单项52断言通过；此前完整回归117项／632断言通过；前轮分权继任回归117项／627断言通过；称职度收益系数0.2的前轮完整回归117项／624断言通过；前轮通判44断言、全组117项／624断言均通过；前轮通判单项36断言、完整回归117项／616断言均通过；上轮司法测试准备修订后的完整回归117项／612断言也通过，历史失败与未唯一还原的庄园子条件见[司法回归记录](judicial_de_jure_probe.md#司法回归准备修订2026-10-15通判整合后)；玩家界面、保存重载与长期玩法尚未完成验收。设计见[规格](song_tongpan_spec.md)，前期失败及静态同僚分权证明见[实验](tongpan_engine_probe.md)。

## 2026-10-16 继任名单直接读取通判司头衔（当前实现）

当前展示按用户要求与原版分权继任栏一致：去掉额外的顺位编号和“查看继承”按钮，直接复用原版150×160单元内的头像、忠诚度图标、分隔线及天平评分样式；网格沿用原版横向填充设置。候选顺序仍直接读取通判司头衔，不恢复独立分权排序。旧版编号、按钮及自定义固定坐标已撤回；前次纵向溢出截图与本次恢复样式截图均为实际验收反馈，先前静态或业务测试不能替代布局验收。

评分展示由GuiScope同时传入候选人物及当前通判司，tca_tongpan_title_candidate_score_value直接查询原生appointment_candidate_score；不使用首次随机抽选专用的最低1分限幅，也不添加新的评分规则。原版依据为本机game/gui/window_faith_conversion.gui的GuiScope.AddScope后ScriptValue调用，以及gui/window_title.gui的GetScriptValueBreakdown调用。评分浮窗沿用原版明细样式，名单、实际任命、忠诚度模型不在本次调整。

本次样式调整：116项工具测试、上游覆盖、GUI表达式及大括号、BOM和空白检查通过。隔离单项及复制正式单元的数据探针run-sx2uz2nl在44.4秒进程退出，exit 0，但未进入观察者、未派发用例、没有界面行结果，整轮NOT VERIFIED；退出原因未确认，不能算引擎或界面通过。本轮未重复完整业务组；当前原版样式、评分文字和悬停明细仍须实机复验。

用户截图显示同一通判的官职窗口与分权窗口人选不同。此前分权窗口读取DiarchyWindow.GetDiarchySuccession，按在任1000分及称职度排序，候选池与官职任命不同。该排序现已停用：tca_tongpan的succession设为no，删除candidate_score及tca_tongpan_succession_score_value；官职死亡继承和原始头衔变更回调后的维护同步继续保留。

正式GUI入口gui/window_diarchy.gui的tca_tongpan_title_succession：从DiarchyWindow.GetDiarchyOwner的主要州头衔变量tca_tongpan_office取得官职，直接用DataModelFirst(Title.GetLineOfSuccession, 4)显示前四名，使用原版头像及图标评分行；不另设编号或按钮。通判专用列表、原版候选列表及“无继任”提示互斥；其他摄政和首辅继续使用原版列表。没有新增名单缓存、轮询效果或继承法分支。

原版依据均来自本机绝对目录/Users/tegridy/Library/Application Support/Steam/steamapps/common/Crusader Kings III/game：localization/english/gui/common_l_english.yml的COA_HOLDER_SUCCESSION直接使用Title.GetLineOfSuccession及Title.GetLineOfSuccessionDesc，证明头衔本身提供数据模型；gui/window_title.gui的TitleViewWindow.GetLineOfSuccession属于另一窗口控制器，不能仅据此判断头衔没有独立接口。原版gui/window_diarchy.gui提供当前复用的继任单元样式。

当时原生回归源events/tca_tongpan_test_events.txt为52条断言（当前增至58，见首节），退休排序相关45至47改为：死亡前原生头衔名单有第一顺位、死亡当下实际接任者属于此前原生候选名单、延迟维护后仍由该实际接任者担任分权者。不再检验已停用的称职度排序。保留“实际接任者是否等于死亡前预览首位”的比较及作用域日志作为诊断，不能把只读取预览名单的界面实现误作锁定任命。单项run-rgu_ewqw：CK3 1.20.1.1，独立1066中国观察者、种子1538798675、仅主模组及CLI适配，入口tca_tongpan_test.1，1 BEGIN／1 PASS／52 CHECK_PASS，零失败或未执行；terminal确认observer及summary，verification_exit和runner_exit均为0，result与同次日志核对通过，未检出模组相关错误。未取得修改前GUI错误到通过的自动复现，原始不一致以用户两张截图为据。后续完整回归及直接数据模型探针记录如下。

完整局run-tk5lz1ie和run-es30arov均为117 BEGIN／116 PASS／630 CHECK_PASS／2 CHECK_FAIL，失败是最初新增的“死亡前预览首位必定接任”和“该预览首位必定成为分权者”断言46、47；原有死亡任命及同步断言23、24仍通过，两局均为NOT VERIFIED。后一局记录：预览首位为另一州通判Yuan Licheng Shuǐ（ID 66209，c_tca_tongpan_xinghua），实际接任者为Chong Linqiong Shuǐ（ID 66524）。这是旧有原生任命路径的实际输出，本轮没有强制授予、改写文官任命法或把预览首位另设为分权者。为何原生接任与死亡前首位不同尚未唯一定位，不能宣称严格按该冻结首位交接已经通过。当前回归按本轮“读取名单、不重写任命”的边界检查原生候选归属及实际官职同步，严格首位差异仍记录诊断；不是靠把结果改成预览人选掩盖差异。

界面数据接口探针位于/private/tmp/tca-title-order-probe/run-es30arov/mod/tca_cli_adapter：从正式GUI复制fixedgridbox，只有窗口目标替换为固定测试通判司；原生scripted_gui逐行核对人物及索引对应place_in_line_of_succession。日志为2条实际效果输出TCA_GUI_TITLE_ORDER_PASS，零FAIL；当时模型实际产生2行，不能要求候选不足4人时生成4行。前次run-tk5lz1ie的_show回调没有结果，不能算验证。探针证明头衔数据模型及已生成行的顺位可求值，没有打开真实分权窗口，也没有证明所有视角的绑定、悬停、点击及布局。最终标准CLI完整局run-wnth1w9z（同版本、书签、种子、仅主模组与标准CLI适配，不含GUI探针）为117 BEGIN／117 PASS／632 CHECK_PASS，零失败、未执行；terminal确认observer和summary，verification_exit及runner_exit为0，result及同次日志核对通过，未检出模组相关错误。第46证明实际接任者属于死亡前原生名单，第47证明分权沿用该实际接任者；首位不同的诊断仍出现并保留，未宣称严格首位任命已修复。116项工具测试、24项对象覆盖／27项追加／1项辅助／2项整文件覆盖、GUI表达式括号与大括号、BOM和差异空白检查通过；覆盖基线未刷新。

人工验收：分别以通判、知州打开绑定州的分权窗口，逐一比对前四名与通判司头衔窗口，确认头像、忠诚度图标、官职原生任命评分及悬停明细；改变原生任命顺位后确认名单随引擎结果更新；换到普通摄政或首辅仍显示原版候选。实际窗口绑定、布局和点击不能由单项脚本通过替代。

## 2026-10-16 治理收益系数调整为0.35（历史；已由0.4替代）

每点通判称职度增加0.35个百分点治理效率，称职度仍限制在0至100，因此最高增加35个百分点。51／80／100称职度分别增加17.85／28／35个百分点。正式入口为common/script_values/tca_tongpan_values.txt中的tca_tongpan_efficiency_value，按称职度乘0.35再除100换算为效率比例；原生governor_efficiency最终0.5至1.5的限幅保持不变。中英文静态使命说明同步为每10点增加3.5个百分点、上限35个百分点，动态浮窗继续直接读取实际加成。俸禄、资金与称职度公式未调整。

回归源events/tca_tongpan_test_events.txt中，第6断言同步新上限；第32断言读取原生最终效率与界面展示值，预期增量为称职度乘0.35个百分点，保留±0.02容差。先在旧0.2实现上运行独立1066中国观察者局run-64i7comr（CK3 1.20.1.1、种子1538798675、仅主模组及CLI适配，入口tca_tongpan_test.1），得到51 CHECK_PASS／1 CHECK_FAIL，仅第32失败，观察者及summary确认，整轮NOT VERIFIED，证明断言能检出旧收益。新系数复测run-emogb5gk使用相同场景、种子及入口：1 BEGIN／1 PASS／52 CHECK_PASS，零失败、未执行；terminal确认observer和summary，verification_exit及runner_exit为0，result与同次日志核对通过，未检出模组相关引擎错误。完成旧实现失败到新实现通过的验证；116项工具测试、上游覆盖（24项对象／27项追加／1项辅助／2项整文件）、BOM与差异空白检查通过。本轮只调整通判收益及对应说明，已运行整个通判生命周期单项，未重复完整117项回归；实际浮窗渲染、保存重载及长期平衡仍待验收。

## 2026-10-16 协理州政文案对齐原版（当前）

参照用户提供的“培养智慧”浮窗及本机原版diarchies_l_simp_chinese.yml中的promote_merit_mandate_desc，将协理州政整理为标题、指令效果列表、灰色职责说明及当前指令称职度。实际治理效率增量仍在效果项目中显示；灰色段落改为“通判协助主管处理州政”，下一行通过原生DiarchyWindow.GetQualificationScore(Mandate.Self)显示该指令的实际称职度，不再在这里重复换算公式。保持当前数值，不把原版首辅特有的+50%官职修正移植给通判。当时静态mandate_desc说明每10点增加3.5个百分点、上限35个百分点（该轮调整后为4及40个百分点），并附相同职责说明，保证该描述在其他调用位置不依赖窗口上下文。

只更新中英两种语言的tca_tongpan_governance_mandate_desc与tca_tongpan_mandate_tooltip现有键；不改GUI、称职度或效率脚本。字面键直接求值及原生点击提示沿用前节实现。UTF-8 BOM、格式标签配对、数据表达式括号及空白检查通过；116项工具测试和上游覆盖检查通过。此轮仅调整本地化，没有重跑引擎业务组；实际称职度行的悬停渲染仍待复验，不能用工具通过替代。原版依据使用绝对目录/Users/tegridy/Library/Application Support/Steam/steamapps/common/Crusader Kings III/game：原始指令描述；common/diarchies/diarchy_mandates/00_mandates.txt中promote_merit专属的0.25／1.5修正；gui/window_diarchy.gui既有GetQualificationScore接口。

## 2026-10-16 非通判指令浮窗名称与效果空白（当前修正）

用户实机截图：原版首辅和西欧摄政仍有指令图标，但悬停只显示“点击更改指令”，名称及效果为空；通判“协理州政”仍有文字。本机正常游玩日志在10:04:13连续记录“New data types does not contain a Mandate data context”以及“Data error in loc string DIARCHY_WINDOW_MANDATE_TOOLTIP”；本次读取时该键错误共2009条。原版localization/simp_chinese/gui/diarchy_window_l_simp_chinese.yml:22直接用Mandate.GetName及Mandate.GetDescription，依赖具体指令的数据上下文。上一轮共享浮窗用SelectLocalization动态求值该键，在实际悬停时没有取得Mandate上下文；不能用只加载窗口、不悬停的引擎通过替代此故障的验收。

删除共享浮窗中的SelectLocalization，改为两个互斥text_multi：非通判直接使用原版字面键DIARCHY_WINDOW_MANDATE_TOOLTIP，通判直接使用tca_tongpan_mandate_tooltip。两者均由具体指令的GUI节点求值，保留Mandate上下文。原版名称、说明和效果文本不覆写，原有点击提示、AI调试提示继续保留；不新增或修改玩家本地化键。

同时收回原先误用于所有分权的指令展示改动。非通判恢复原版全部可用指令，按CanChangeMandate原生权限启用／灰显；仅tca_tongpan分权对非主管显示当前指令的亮色只读图标，隐藏其余指令。主管的原生选择操作继续保留。

日志核对漏报同步修复：该错误只有原版本地化键，没有tca_或GUI文件路径，原检查器会忽略。window_diarchy整文件覆盖登记新增diagnostic_localization_keys，仅列出实际受该窗口控制的DIARCHY_WINDOW_MANDATE_TOOLTIP。check_test_run按精确键识别其本地化求值错误；其他原版键不会据此一概归为模组错误。工具回归先复现该错误漏报（41项中1失败），再修正并通过116项全部工具测试；实际读取的2009条原日志错误也能被新检查器识别。覆盖检查仍为24项对象、27项追加、1项辅助及2项整文件，基线未刷新；GUI括号、BOM及空白检查通过。

本轮独立1066中国观察者局run-54zd8r47，CK3 1.20.1.1，种子1538798675，仅本模组和CLI适配，入口tca_tongpan_test.1：1 BEGIN／1 PASS／52 CHECK_PASS，零失败、未执行；terminal确认observer和summary，verification_exit与runner_exit为0，result及同次日志核对通过。未重跑完整117项业务组，没有改变业务规则。本轮证明引擎加载及通判脚本断言；没有触发真实悬停，不能宣称浮窗已经实机通过。已知三标签自动探针未完成且不验证悬停，本轮不重复用它替代浮窗验收。

实机复验：重载GUI后，以皇帝查看首辅、以西欧统治者查看普通／固化摄政，逐个悬停所有指令，确认名称、原版效果和权限提示完整，并检查不再新增上述Mandate上下文错误；再以通判和知州查看协理州政，核对实际效率加成、只读／可选择状态。标签高亮仍按上节单独验收。

## 2026-10-16 两个标签同时显示选中底图（当前修正）

用户在ID方案之后实测：两个标签同时显示底图，与当前关系无关。该反馈否定了前轮修正的有效性。前轮虽核实ObjectsEqual严格比较CPdxAny类型，但仅据底层类型推断GUI数值比较可靠并不充分；不能把前轮“根因已定位”视为已完成验收。此处不把两侧数值为0、贴图异常等未记录到运行时值的推测写作事实。

撤掉三个标签及教程标记的EqualTo_uint32判断。自己的关系直接使用原版已有的DiarchyWindow.GetDiarchyOwner.IsLocalPlayer；领主和通判先用GetDiarchyOwner.Self及目标.Self取得角色对象，再ObjectsEqual比较。后两项另要求当前主管不是玩家、目标有效，保证不会与“你的权力分享”同时选中；不再增加独立的选中变量。窗口打开／切换回调及原版button_tab四帧贴图不变。

本机原版依据（CK3 1.20.1.1）：绝对目录/Users/tegridy/Library/Application Support/Steam/steamapps/common/Crusader Kings III/game下，gui/window_diarchy.gui:375直接使用GetDiarchyOwner.IsLocalPlayer；gui/window_culture.gui:2306使用ObjectsEqual(Culture.GetCultureHead.Self, GetPlayer.Self)；gui/shared/buttons.gui保留downframe=4。没有修改原版或Workshop文件。

探针现直接读取正式三个button_tab的down表达式，在知州→自己→领主→通判→自己各步要求目标标签为true、另外两项均为false，并保留分权者及使命权限断言，防止仅看窗口目标而漏过多项同时选中。客户端阶段只用于探针调度，不参与正式标签选中。Python只代入维护中的GUI表达式，不模拟角色比较业务。新增工具测试检查代入真实表达式、缺失／未知占位符拒绝，115项工具测试通过；覆盖、渲染后GUI结构及空白检查通过。本轮引擎探针run-1zoybxcv确认夹具、play及打开请求，但五步均缺结果；terminal条件stalled，verification_exit和runner_exit均为1，result为NOT VERIFIED，同次日志核对未检出模组相关引擎错误。它没有进入可据以验证选中条件的阶段，因此不能判定互斥检查通过；仍需查明探针停滞，并分别对通判、知州、皇帝实机复验。

## 2026-10-16 标签不显示选中底图（历史：ID方案已撤回）

用户实机反馈：通判、知州和皇帝均可切换关系内容，但标签底图不随选中关系改变。当前三个标签都沿用原版button_tab：togglepushbuttongfx，普通帧1，选中帧4，未替换按钮贴图。

核查本机CK3 1.20.1.1 ARM64符号与实现：CDiarchyWindow::GetDiarchyOwner返回TPdxRef<CCharacter>，本地玩家绑定GetLocalPlayer返回CCharacter const*。ObjectsEqual先比较两个CPdxAny的类型对象，类型不同直接返回false，不执行角色引用到指针的转换。旧down表达式把窗口主管的裸引用与玩家／领主／知州对象直接比较，因此可在内容已经切换时仍判为未选中；相同错误也存在于教程标记及GUI探针中。这里需要区分裸引用比较与GetDiarchyOwner.GetID：后者先经过角色提升，再得到角色的uint32 ID。

将三个down及两个教程标记改为EqualTo_uint32(窗口主管.GetID, 目标角色.GetID)，教程标记另保留有效玩家／领主守卫，避免空角色ID互相相等。保持原生窗口切换、权限、角色数据和原版四帧样式。原版依据：绝对游戏目录下gui/shared/buttons.gui的button_tab、gui/window_title.gui中Title.GetHolder.GetID与GetPlayer.GetID的EqualTo_uint32用法。该修正针对所有身份共用的窗口，不按通判／知州／皇帝分别维护选中变量。

GUI探针同步改为比较主管角色ID，保留五步及全部权限／分权者断言，不放宽预期。114项工具测试、覆盖检查和空白检查通过。本轮没有重跑117项业务组：没有改变业务逻辑；前节117项／632断言和最终版52断言的通过不证明本轮高亮。界面专项run-ce3exloh确认夹具准备、play及打开请求，但五步结果均为0，terminal条件stalled，verification_exit和runner_exit为1，result为NOT VERIFIED；同次日志核对未检出模组相关引擎错误。需继续保留NOT VERIFIED；角色比较错误虽足以解释旧选中条件恒假，但不能把探针的全部停滞归结于这一处。实际底图随点击更新仍待通判、知州、皇帝三种身份实机复验。

## 2026-10-16 三关系标签与使命显示（当前实现；界面待验证）

用户在通判视角看到“你的权力分享”实际展示知州，无法返回玩家本人的摄政。根因是HUD把原生窗口基准角色设成知州，而原生两个标签相对该基准切换。截图还显示当前使命因通判无更换权限而变灰，提示只显示换算规则、项目符号断行。

新增整文件覆盖`gui/window_diarchy.gui`，三个标签始终相对本地玩家：自己的分权、直属领主的分权、玩家官职绑定知州的通判分权。无直属领主时隐藏第二项，无合法通判关系时隐藏第三项；自己的标签始终保留，包括未启动分权时的原生指定设置。候选选择模式暂隐藏关系标签，返回后恢复。三个按钮各使用一个模板，直接调用`OpenGameViewData('diarchy', 目标ID)`后执行`DiarchyWindow.SetYourDiarchyTab`，同时更新原生基准角色与实际主管。最终版移除隐藏请求消费控件及跨控件转发，客户端变量仅用于可选探针的步骤记录。选中状态以实际主管的原生IsLocalPlayer及角色.Self比较为准，避免界面变量与真实目标分离。下方显示统治者姓名，人物、天平、候选、互动继续读取原生控制器。HUD通判入口仍默认打开知州，原生入口保留原有默认选择；两者都可进入三个标签。不依赖改变Character数据上下文冒充控制器目标。

非通判使命列表恢复原版全部可用指令及原生启用／灰显状态。只有通判分权保留主管的原生选择按钮，非主管仅显示当前使命的亮色只读图标，不调用SetMandate。浮窗采用各自直接本地化键，不再通过SelectLocalization嵌套求值。`CanChangeMandate`权限不放宽。通判浮窗以原版效果列表样式显示正式`tca_tongpan_efficiency_value × 100`对应的当前治理效率增量，再给每10点称职度增加2个百分点、上限20的简短说明。浮窗数值是通判加成分项，最终治理效率仍受原生总上下限约束。中英文本地化同步，UTF-8 BOM保留。脚本、人员、税费及分权生命周期不变；知州自身摄政与通判仍占用同一原生分权槽位，本次没有解决并存机制。

本机原版依据为绝对目录`/Users/tegridy/Library/Application Support/Steam/steamapps/common/Crusader Kings III/game`：`gui/window_diarchy.gui`原标签、使命按钮和互动目标；`gui/window_create_accolade.gui`的`OpenGameViewData`携带角色ID用法；`localization/simp_chinese/diarchies/diarchies_l_simp_chinese.yml`的效果列表。CK3 1.20.1.1 ARM64中`CDiarchyWindow::SetCharacter`保存基准角色并可能默认向其直属领主解析，`SetYourDiarchyTab`再将主管明确重设为基准角色；`CanChangeMandate`比较实际主管与本地玩家。静态依据不替代实机切换验证。

`tools/upstream_overrides.json`登记第二项整文件覆盖，基线为`tools/baselines/tongpan_window_diarchy.gui`。现在既与替换`hud.gui`的模组冲突，也与替换`window_diarchy.gui`的模组冲突。日志核对器增加file_overrides路径归属，确保原版文件名下、不含tca标识的绑定错误同样使验收失败。

验证入口：`python3 tools/run_diarchy_ui_probe.py`。可选探针源在`tools/diarchy_ui_probe/`，仅复制进本次独立CLI适配模组；普通游戏不加载。原生隐藏事件自行创建玩家通判、直属公爵、知州三个主管的关系，玩家及直属领主拥有原生temporary_regency，知州拥有正式通判分权。GUI在世界就绪后排队执行play，角色ID通过原生本地化读取，随后检查GetPlayer与夹具角色相等；此专项不进入观察者。透明GUI模板仅注入临时适配副本的真实diarchy_window，在同一原生控制器上下文中执行按钮模板中的实际回调；Python仅将已维护的onclick原文改作探针on_start，不复制或模拟目标选择逻辑，逐步检查知州→自己→领主→通判→自己时的原生主管、显示分权者、使命操作权限；不在Python中模拟玩法。它不计入正式117项业务用例，也不以业务断言代替GUI控制器证据。原始结果单独保存为terminal.json、result.txt、debug.log及error.log。

静态验证：114项工具测试、24项原版对象覆盖／27项追加回调／1项辅助扩展／2项整文件覆盖检查及空白检查通过。日志工具新增原版文件名GUI绑定错误的反例；五步探针日志核对器检查缺项、重复、console回显及同次错误，不放宽失败条件。

完整原生回归：独立1066中国观察者局`run-bxncjnqj`，CK3 1.20.1.1，种子1538798675，仅主模组与CLI适配。117 BEGIN／117 PASS／632 CHECK_PASS，零失败、未执行或缺结果；terminal确认observer与summary，verification_exit和runner_exit均为0，result核对通过。同次error.log仍有原版／安装背景诊断，未检出模组相关引擎错误。该轮证明现有业务断言和引擎加载，不证明三标签的控制器切换、使命渲染或浮窗。其后移除HUD上不必要的SetYourDiarchyTab回调：HUD仍使用前轮已采用的ToggleGameViewData，主管已有活跃通判分权，窗口打开时原生SetCharacter会选中该主管；明确选中自己的调用只保留在实际窗口的标签路径。全组完成后，标签从隐藏控件转发简化为直接原生回调；最终直接回调版独立观察者局`run-cexg8sji`通过1 BEGIN／1 PASS／52 CHECK_PASS，零失败、未执行；terminal确认observer与summary，verification_exit及runner_exit为0，result及同次日志核对通过。

界面专项尚未通过：首轮`run-yngozcw0`夹具漏填家族头衔save_scope_as，后续已补必填项及原生前置断言。`run-ylpomb30`、`run-fzdbguss`等局已创建三关系夹具，但没有取得任一步窗口断言，均为NOT VERIFIED；`run-snv229ed`在建立世界前进程提前退出，也不计执行。跨独立widget的客户端状态已改为临时注入真实窗口；无符号角色ID曾经由IntToString尝试拼命令，现改为本地化读取，`run-x3gyndr1`已确认play到测试通判64586，但外部诊断对DiarchyWindow的读取产生本地化错误，五步仍未执行，整轮NOT VERIFIED。该临时诊断已删除。最后一轮转发版`run-0ufukqqa`确认夹具、play及打开请求，仍未取得任何窗口断言，无模组相关引擎错误，终止条件stalled，NOT VERIFIED。最终直接回调版未取得有效五步结果。尚未证明这些失败来自探针还是正式切换路径，不能归结为某一引擎行为，也没有取得有效失败到通过证据。电脑控制接口另返回ScreenCaptureKit -3811捕获失败，未取得可验收的画面。

人工验收仍需：点击三个标签的实际命中区域，核对缩放、亮色使命图标及中英浮窗；对照自己的原生候选列表，确认指定、结束分权和摆动天平等操作对象；关闭重开、官职变化、失去通判资格、独立与旧存档重载。探针仅验证控制器切换与权限，不证明这些完整交互及视觉结果。

## 2026-10-15 通判入口布局修正（保留布局；窗口已在上节扩展）

用户提供的知州／通判截图确认：独立入口固定偏移−440／−95时，通判天平明显偏左且偏高，没有对齐原版按钮列。旧版脚本断言通过只证明资格与数据绑定，未证明布局。

当前改为覆盖本机CK3 1.20.1.1的`gui/hud.gui`，只在`bottom_bar`的`in_progress_systems`中、原版天平之后及局势入口之前插入`tca_tongpan_hud_button`。通判入口使用原版相同的90×90尺寸及`parentanchor = vcenter`，由同一个flowcontainer计算位置，随旅行、战争、局势及疫情入口增减自动排布，继承原版右侧窗口及临时隐藏条件。资格、知州目标、圆环及档位绑定沿用已测试实现。已删除旧独立GUI及scripted_widgets登记，避免重复按钮。

原版依据：本机绝对路径`/Users/tegridy/Library/Application Support/Steam/steamapps/common/Crusader Kings III/game/gui/hud.gui`中，外层队列右下锚定，偏移0／−175；系统队列上边距15；原版天平、局势及疫情参与同列排列。审阅后按原文件复制，除新增通判节点外保持内容不变。由于原版没有为此列提供可直接复用的扩展插槽，本次采用整文件覆盖；与其他覆盖`gui/hud.gui`的模组冲突，当时未覆盖`window_diarchy.gui`；2026-10-16起为三个关系标签增加该覆盖。

覆盖登记在`tools/upstream_overrides.json`的`file_overrides`，原版完整基线为`tools/baselines/tongpan_hud.gui`。检查器逐字节核对上游文件并验证覆盖文件存在，不自动更新基线；工具回归检查上游变化、缺文件及基线只读。移除新增通判节点后，HUD文本与原版完整一致；括号结构静态解析通过。

静态验证：109项工具测试、原版覆盖检查通过。本轮独立1066观察者局`run-q1g9vplx`（CK3 1.20.1.1，种子1538798675，仅本模组及CLI适配，入口`tca_tongpan_test.1`）1 BEGIN／1 PASS／52 CHECK_PASS，零失败／未执行；terminal确认观察者及summary，verification_exit与runner_exit均为0，result核对通过。同次error.log共25行背景诊断，未检出模组相关引擎错误，也无`hud.gui`或新按钮相关记录。该轮证明引擎加载与通判脚本断言，不证明玩家视角实际渲染。本轮未重跑全组，官职及权限逻辑没有变化。首轮`run-e3fbhr8r`因Steam IPC初始化失败、进程−6退出，无观察者及派发记录，NOT VERIFIED。电脑控制请求超时，实际渲染与点击尚未确认。

人工验收：重启仅本模组的专用debug局，在同州知州／通判之间切换，确认天平位于原版按钮列、与旅行及王朝入口垂直居中；检查有无旅行、战争、疫情／局势两种状态和常用GUI缩放；右侧窗口打开及临时隐藏时与整列同步隐藏。点击应仍打开绑定知州的分权窗口。原版队列只保证布局参与关系，具体视觉结果须实机复测，不以脚本断言替代。

## 2026-10-15 通判右下角分权入口（历史：独立定位版）

触发条件：玩家为州通判，与知州同级、直属上级主管；知州的原生右下角入口可见，通判不可见。当前本机版本为1.20.1.1（以`launcher/launcher-settings.json`为准）。原版`gui/hud.gui:2272`调用`InGameBottomBar.ShouldShowDiarchyInHUD`；ARM64函数`CHudBottomBar::ShouldShowDiarchyInHUD`（0x1004bb07c）判断玩家自己有活跃分权，或是直属领主的分权者，不识别同僚知州。`CDiarchyWindow::SetCharacter`也只自动向直属领主解析分权。因此不能仅打开继任或只放宽按钮显示。

新增`gui/tca_tongpan_hud.gui`及独立`scripted_widgets/tca_tongpan_widgets.txt`，右下角锚定、偏移−440／−95，90×90，复用原版圆形天平图像、进度圈和档位背景。按钮直接从玩家主要官职的`tca_tongpan_county`读取知州，以其ID调用`ToggleGameViewData('diarchy', Character.GetID)`；圆环与档位同样绑定此知州的原生Diarchy。不覆盖`hud.gui`或`window_diarchy.gui`，不修改官职隶属、任命或操作权限。原版按钮继续保留，新增入口只面向合格且分权同步的通判，知州不显示该补充入口。其他HUD模组仍可能占用同一屏幕位置，独立按钮不参与原版队列自动排布。

正式入口资格为`tca_can_open_tongpan_diarchy_trigger`，要求合法在任官职、双向州绑定以及知州当前分权正确同步。`common/scripted_guis/tca_tongpan_hud.txt`使用无角色root与可选命名角色作用域，避免观察者／菜单的空玩家引发脚本错误。暂停菜单、观察者、非默认GUI、理发店和朝廷场景隐藏按钮。双语浮窗说明打开的是与哪位知州的权力分享。

参考本机Search & Trade Artifacts（2962238514，声明1.20.*）独立右下角注册与圆形按钮，以及万偶之主（3814466871，声明1.20.*）独立HUD图层与场景隐藏做法；原生`gui/window_government_administration.gui:3250`证明通过`Title.MakeScope.Var(...).Title.GetHolder`解析头衔变量；原版`hud.gui`提供天平绘制与打开窗口方式。参考是本地静态代码证据，不是这些模组的实机兼容证明。

回归在`tca_tongpan_test.1`增加48至52，验证有效通判可打开、知州与无头衔普通角色不可打开、资格暂停后不可打开及恢复后重新可打开；不替代真实GUI点击验证。首轮`run-5kj8jkpo`52 CHECK_PASS／1 PASS，但观察者空玩家使`scope=character`界面检查出现1354条错误，整轮NOT VERIFIED；已改为无root并检查命名角色作用域存在；修复后单项`run-azfu74bq`52 CHECK_PASS／1 PASS，零失败／未执行，观察者与summary确认，terminal及result核对通过，verification_exit和runner_exit均为0。同次error.log有254行背景诊断，无`tca_`记录，核对未检出模组相关错误；108项工具测试及覆盖检查通过，完整独立1066观察者局`run-fp2ctj8t`（种子1538798675，仅本模组与CLI适配）117 BEGIN／117 PASS／632 CHECK_PASS，含通判52断言，零失败／未执行；terminal确认观察者及summary，verification_exit与runner_exit均为0，result核对通过。同次error.log有842行背景诊断、无`tca_`记录，核对未检出模组相关错误。UTF-8 BOM、差异空白、108项工具测试以及24项原版覆盖／27项追加回调／1项辅助扩展检查通过。此次没有先对旧入口完成自动化失败到通过证明，原症状来自用户报告和原版代码核对。

人工验收步骤：重启仅本模组的专用debug局，分别切换同一州知州与通判。知州保留原版入口、通判出现补充圆形天平按钮；点击后窗口中统治者须为绑定知州，分权者须为当前通判，档位和进度与知州视角一致。核对中文／英文浮窗、常见分辨率及GUI缩放；在暂停菜单、观察者、理发店及朝廷场景无悬浮按钮；换州／官职继任／资格失效恢复后无旧目标残留。真实点击、天平操作权限、窗口标签语义、遮挡、旧存档重载均待人工验收。电脑控制工具返回“Computer Use was not approved to use”，本轮无法抓取或操作CK3窗口，不以原生断言代替界面证据。

## 2026-10-15 开启分权继任（历史；独立候选排序已停用）

通判分权改为`succession = yes`，候选分数调用`tca_tongpan_succession_score_value`：合法且与州相互绑定的在任通判加1000，全部候选加正式称职度0至100。双语评分明细显示在任身份和称职度。官职的文官任命法、死亡继任及交接维护同步继续保留。

原版依据为本机CK3 1.20.1的`game/common/diarchies/diarchy_types/00_primeministerships.txt`中`grand_secretariat`的继任开关、现任官职1000分及任职回调`got_minister_position_effect`中的`set_diarch`；`_diarchies.info`规定评分root为候选。ARM64符号`CDiarchyType::CalcCandidateScore(TPdxRef<CCharacter>, CValueBreakdownEntry*) const`也只接收候选及明细。原版`game/gui/window_diarchy.gui:592–607`以`DiarchyWindow.HasSuccession`切换“无继任”提示和`GetDiarchySuccession`列表，本次复用该界面，不覆盖GUI。多个地方通判共用一个分权类型，无法照搬固定中央头衔的前四顺位加分；分权候选池与正式任命池不同，已有官职的评分不能按被监督州细分，最终由官职绑定同步纠正。

回归新增45至47：正式评分的在任优先、无官职满称职度候选100分，以及原生分权候选池非空。原有23、24继续验证死亡当下官职继任和延迟同步，25至28检查资格失效与政府变化。旧实现（评分helper为0、继任关闭）单项`run-4v0x_4zi`为45 CHECK_PASS／2 CHECK_FAIL，仅45、46失败，观察者与summary确认，NOT VERIFIED。首次新实现`run-ks7mt3_a`虽然47断言全部通过，但同次日志有3869条无头衔候选的primary_title作用域错误，整轮NOT VERIFIED；已在读取前增加主要头衔存在检查，并明确要求官职有绑定州。最早沙箱启动`run-petkfduf`在Steam IPC初始化阶段退出，未切观察者、未派发测试，不算执行证据。修复后单项`run-227t3t10`为47 CHECK_PASS／1 PASS，零失败／未执行，观察者、summary、terminal与result核对通过，verification_exit与runner_exit均为0，同次日志未检出模组相关脚本错误；完成45、46从失败到通过。第47在关闭继任时也可通过，只证明原生候选池可枚举，不能单独证明GUI继任区域可见。完整独立1066观察者局`run-n_4y2t8a`（CK3 1.20.1，种子1538798675，仅主模组与CLI适配）117 BEGIN／117 PASS／627 CHECK_PASS，含通判47断言，零失败／未执行；观察者、summary、terminal与result均确认，verification_exit与runner_exit为0。同次error.log共20919行，无`tca_`记录，保留原生／安装环境背景诊断，日志核对未检出模组相关错误。108项工具测试、24项覆盖／27项追加回调／1项辅助扩展及空白检查通过；界面候选列表、同僚在任者是否入池、浮窗及旧存档重载仍待人工验收。


## 实现入口

- `tools/build_tongpan_catalog.py`：3,442个固定官职、128个池官职、固定映射、限定官职的持有人称谓和双语名称；不含测试生成。
- `common/scripted_effects/tca_tongpan_effects.txt`：绑定、三级挂靠、原版评分补位、destroy与恢复、角色分权同步和皇帝级维护。
- `common/scripted_triggers/tca_tongpan_triggers.txt`：实际政权与伯爵主头衔资格、专职校验、双向绑定与生效条件。
- `common/laws/tca_tongpan_laws.txt`、`common/law_groups/tca_tongpan_law_groups.txt`：皇帝级开关、费用、冷却和开局默认。
- `common/diarchies/`、`common/script_values/tca_tongpan_values.txt`：单使命、称职度、0/20/40/60/80档位和数值。
- `common/on_action/tca_tongpan_on_actions.txt`、`events/tca_tongpan_events.txt`：原生回调追加维护，合并到次日；季度及年度补查。
- `common/script_values/zz_tca_tongpan_native_values.txt`：原版治理效率与四项威望附费的包装；保留原生治理效率0.5—1.5总上限。
- `common/character_interactions/zz_tca_tongpan_action_costs.txt`：原版四项互动追加影响力费用，代理操作沿用原版承担者路径；本模组两项司法拘捕入口也追加费用。
- `common/on_action/diarchy_on_action.txt`：修正原版退出分权时直接读取已故旧分权者变量的问题。仅给共治头衔变量分支增加存活检查，其余四个回调原样保留；采用同名文件遮蔽，避免多个effect定义的加载错误。五个对象均登记并保留原版基线。

新增同名原版对象及追加回调已登记 `tools/upstream_overrides.json`；原版主体保存在已审阅基线／原样helper中。影响力需要覆盖整个互动对象，兼容范围大于仅追加数值的威望适配。

原版不允许给无持有者头衔查询任命分数，也不允许将这项realm继承法直接用`add_title_law`加到空头衔。因此首次／纠错时在同一次效果内先由挂靠上级暂持官职，继承其原生任命环境，再按引擎分数抽选并立即授予专职人选。有效在任者不经过暂持步骤。此处的原生头衔回调可能被其他模组观察到，属于需要兼容验收的边界。

补位使用`granted`事务精确授予已抽中的人，避免`appointment`事务再次使用原版缓存继承人。持有者仍使用原版realm文官继承法，正常死亡交接不走初始加权补位。

分权资格复用`is_diarch_valid_trigger`，可履职状态复用`is_diarch_able_trigger`，对应原版`scripted_rules/00_rules.txt`。原版资格失效时暂停分权，保留官职；恢复后维护重新连接，不另造特殊状态资源或代理职位。

## 2026-10-15 治理收益系数提高至0.2（历史；已由0.35替代）

`tca_tongpan_efficiency_value`由称职度÷1000改为÷500，即每点称职度增加0.2个百分点治理效率。60／80／100称职度分别提供12／16／20个百分点；仍先计算并限幅原生效率，再加通判，最终保留原生−50%至+50%的总上下限。中英文使命提示改为每10点称职度增加2个百分点、上限20个百分点。

第6断言上限同步为0.2；第32断言继续读取最终`governor_efficiency`与界面用`governor_efficiency_presented`，预期增量改为称职度÷5个百分点，不放宽±0.02容差。用旧系数运行`run-tu6xzhe5`得到43 CHECK_PASS／1 CHECK_FAIL，仅第32失败，观察者、summary确认，整轮NOT VERIFIED，未检出模组相关脚本错误，证明原断言能检出收益未翻倍。修复后完整局`run-cx3tw5ms`（同种子1538798675）117 BEGIN／117 PASS／624 CHECK_PASS，零失败／未执行，通判44断言均执行且第32通过，完成原断言失败到通过验证。观察者、summary、terminal与result及同次日志核对通过，verification_exit与runner_exit为0；error.log共661行，无`tca_`记录，仍有原生／安装环境背景诊断。108项工具测试、24项原版覆盖／27项追加回调／1项辅助扩展和空白检查通过。使命文字实际渲染及旧存档重载仍待人工复核。

## 2026-10-15 忠诚度调平与五维、教育称职度（称职度与忠诚度）

- 官员忠诚度基础75→60，好感权重10%→25%，好感贡献上限由±10变为±25；性格权重、0至100范围和原生显示门槛保持不变。无相关性格、好感+60时为75分；好感−60时为45分。
- 称职度增加军事×0.5、谋略×0.5；保留管理×2、外交、学识与性格项。直接取当前能力值，含教育特质原有的能力加成。
- 另加教育等级奖励：1至5级分别+2／4／6／8／10。采用本机CK3 1.20.1 `game/common/scripted_triggers/00_education_triggers.txt`中的`has_education_rank_1_trigger`至`has_education_rank_5_trigger`，五种能力教育同权，只取最高级；武艺教育不重复计入。实际教育属性参考`game/common/traits/00_traits.txt`。原版查询根为`/Users/tegridy/Library/Application Support/Steam/steamapps/common/Crusader Kings III/game`。
- 两种语言增加“教育等级”评分来源，并将好感来源权重标记改为25%。使命与实际效率沿用同一新称职度；收益系数后续多次调整，当前值见文首。
- 原生生命周期断言34和36按新基础分调整；新增37至44，分别检查纯军事、纯谋略、零能力且无教育，以及1至5级教育的最终称职度。教育夹具使用零基础五维，一级至四级外交教育应为4／8／12／16分，五级外交教育因原生军事+3应为21.5分；验证正式最终评分而非只读教育helper。

调整前`run-3r4qx5pu`：35 CHECK_PASS／9 CHECK_FAIL（34、36、37、38、40—44），如预期暴露旧数值，39确认零能力无教育仍为0。观察者和summary确认，整轮NOT VERIFIED，未检出额外模组脚本错误。新数值单项`run-8hxbz8vm`：44 CHECK_PASS／1 PASS，零失败／未执行，观察者和summary确认，verification_exit与runner_exit为0，同次日志核对通过，未检出模组相关引擎错误。至此保留原断言并完成本轮9项从失败到通过的验证；完整局`run-nacaazxp`（同种子1538798675）117 BEGIN／117 PASS／624 CHECK_PASS，零失败／未执行，观察者、summary及同次日志核对通过，verification_exit和runner_exit均为0。error.log共1464行，无`tca_`记录；保留原生封臣索取头衔上下文、宫廷场景、重复排队及安装环境图像等诊断，不能表述为无引擎错误。工具108项、24项原版覆盖／27项追加回调／1项辅助扩展和空白检查通过。UI分项实际渲染、旧存档重载及长期平衡仍待人工验收。

## 2026-10-15 零档、使命效果与官员忠诚度（历史，数值已调整）

- 天平新增`swing = 0`及`tca_tongpan_cost_0`，0至不足20免附费；20／40／60／80费用保持不变。双语提示参照原版效果句式，使用“行政行动”，同时显示威望与影响力的图标、概念和数值。
- “协理州政”提示使用原版`#BOL`与`$EFFECT_LIST_BULLET$`效果列表，明确每10点称职度增加1个百分点治理效率、上限10个百分点。展示换算规则，当前实际数值仍由主管治理效率明细中的“通判协理”提供，不额外覆盖GUI。
- `tca_tongpan_loyalty_values.txt`替换此前复制的摄政评分依赖，改为职守基础75、人格修正、对所辅佐主管好感的10%，最终0至100。具体性格值见规格。去掉摄政关系、文化、恐怖值和牵制等额外项；保留好感对象校验与原生显示规则适配。其他分权类型不改变。
- 原生用例新增33至36：零档参数生效且两种附费均为0；无相关性格75分；公正诚实100分；贪婪野心狡诈10分。原先32项（含错误上级关系不影响忠诚度、最终治理效率真实增量和真实扣费）保留。

修复前试跑`run-1t08dsm2`：原32项通过，新增4项失败，整轮NOT VERIFIED。但3个人格夹具漏填性别，伴随`create_character`错误，因此不能将该轮作为忠诚度的有效失败到通过证明；零档缺失得到复现。已给夹具补齐性别，后续以完整引擎重测为准。

当前验证：通判单项`run-5ruqhlu4`，固定种子1538798675，36 CHECK_PASS／1 PASS，零失败／未执行，观察者确认，summary终止，verification_exit及runner_exit均为0。同次日志核对未检出模组相关引擎错误；工具108项与24项原版覆盖／27项追加回调／1项辅助扩展检查通过。完整局`run-w82npmx7`（同一固定种子）：117 BEGIN／117 PASS／616 CHECK_PASS，零失败／未执行；通判36项全部执行。`terminal.json`确认观察者、summary终止，verification_exit和runner_exit均为0，`result.txt`核对通过。完整error.log有698行原版／安装环境背景诊断，未含`tca_`，核对器未检出模组相关错误；不是空日志。界面布局、浮窗实际渲染及旧存档重新加载后的表现仍需游戏内人工复核。

## 2026-10-15 名称冲突、忠诚度与数值明细修复（历史，评分已替换）

第二轮用户截图复现：颍州通判头衔显示内部ID；忠诚度显示对上级的-91好感，与对州主管的好感不同；称职度浮窗只有标题；治理效率没有通判来源行。

- 用户当次`logs/error.log`19:13:03明确记录`c_tca_tongpan_yingzhou_2`与`gte_contest.1013.bold.failure`哈希冲突（-1112372659）。后者在本机Workshop锦标赛扩展汉化中存在，原版未找到该键。保留原头衔ID，在目录生成器中为此条名称使用`tca_tongpan_name_yingzhou_2`，正式维护调用`tca_repair_tongpan_name_effect`设置安全名称键，已有官职和绑定不重建。双语目录均不再定义冲突键。新增工具回归检查ID不变、名称别名和修复入口。
- 原版摄政忠诚度把`liege`作为关系对象；通判实际直属公国／路／政事堂，这与辅佐对象不同。新增`tca_tongpan_loyalty_values.txt`，沿用本机1.20.1原版`common/script_values/00_diarchy_values.txt`摄政忠诚度及其依赖，使用原生`save_temporary_scope_as`在单次数值计算内保存通判与`primary_title.var:tca_tongpan_county.holder`，把原版的`root`／`liege`引用分别指向这两者，接入通判`loyalty_score`；人格、文化、关系、牵制等原版权重保留，不覆盖其他分权类型。好感条单独命名为“对州主管的好感”，避免与直属上级混淆。原版字符级`diarch_loyalty`仍可能按实际领主计算，不能直接把它当作同级分权评分；因此最小覆盖`scripted_rules`中的`is_diarch_visibly_loyal`／`is_diarch_visibly_disloyal`：标记通判使用新评分决定文字和图标，其他角色完全保留原判断。两项原版对象已登记审阅基线，不复制分权GUI。原版依据为`game/common/scripted_rules/00_rules.txt`“displayed as loyal/disloyal diarch”注释。
- 称职度各能力／特质贡献增加原生`desc`明细，`aptitude_score`改用原版的`add`入口展开分项，公式与0—100范围不变。
- `governor_efficiency`中的通判贡献增加`desc = tca_tongpan_bonus`，分项内乘100、外层除100，沿用原版按百分点显示的结构，最终浮窗显示“通判协理”。用户截图列项为-100+19+14+19+3=-45，显示总计-40；相差5个百分点与通判加成一致。这只是截图推断，需结合原生最终值回归，不能据此称实际GUI已验收。

原生生命周期用例新增三项：显示的好感贡献精确等于引擎对所辅佐主管的原生好感；对实际直属上级新增敌对关系不改变对州主管的忠诚度；读取原版最终`governor_efficiency`及界面入口`governor_efficiency_presented`，验证真实增量为称职度／10个百分点。总计32断言，普通主管夹具明确设定低基础能力，避免触及效率上限而掩盖加成。

初轮`run-d5ehn_ry`为31通过／1失败，并出现3组文化条件作用域错误；修正为计算内临时命名对象后，`run-hepa37i3`消除了脚本错误，但第30断言仍失败，显示字符级`diarch_loyalty`与当前同级分权模型不同。第30断言原先把字符级getter当作窗口模型，目标API不成立；据此补充原版显示规则适配，并把该断言改为精确检查窗口贡献所用的原生好感对象。保留对错误上级的关系不影响评分、最终效率真实增量等断言，不通过放宽数值容差消除失败。

修复单项`run-nzqumyzz`：32 CHECK_PASS，1 PASS，零失败／未执行；观察者确认，summary终止，verification_exit与runner_exit均为0，同次日志核对通过。工具108项通过，24个原版覆盖、27个追加回调及1个辅助扩展检查通过。第32断言读取的是角色界面使用的`governor_efficiency_presented`，原版GUI本地化依据为`game/localization/english/gui/government_administration_window_l_english.yml`的`ADMIN_WINDOW_THEME_GOVERNOR_EFFICIENCY_VALUE`。忠诚度文字和图标的显示规则已加载，但脚本数值断言不代替实际UI观察。

修订前完整`run-kdtmyf5l`：CK3 1.20.1、独立1066中国观察者新局，仅主模组与CLI适配。117 BEGIN，115 PASS／2 FAIL，609 CHECK_PASS／2 CHECK_FAIL，无未执行或缺少结果；观察者确认、summary结束，但verification_exit=1、runner_exit=1，整轮NOT VERIFIED。通判32断言均通过，包括最终百分点明细结构调整后的第32断言；同次日志核对未发现模组相关错误，仍有原版背景诊断。两项失败为：

- `tca_test_imperial_circuit_lifecycle`第10断言：前轮已复现并做旧时序对照，尚未解决。
- `tca_test_judicial_estate_jurisdiction`第23断言：正式夹具重建后，两路别名须有效、互异且第二路不能沿用英格兰哨兵的复合条件失败；第22断言的有效路列表检查通过。未进一步隔离出复合条件的具体失败项，不将其宣称为已定位的业务缺陷或已修复问题。本轮没有改写此夹具或放宽断言。

原始结果位于本次目录的`terminal.json`、`result.txt`与`logs/`；本轮记录不覆盖前轮失败，不把通判单项通过当作完整回归通过。

新增名称哈希兼容和三项界面表现须重启后人工复核；独立CLI只加载主模组及测试适配，不加载用户整套Workshop播放集。

## 2026-10-15 界面与首次初始化修复

用户游戏截图复现四项问题：通判仍称刺史；天平效果显示`tca_tongpan_cost_1`；协理州政指令缺图标；首次进入游戏需推进日期才出现通判与分权。

- 官名采用原版中央大臣的`titles`限定称谓方式：目录生成器同步生成男女通判称谓，显式列出全部固定官职与128个池位。只作用于以这些官职为命名头衔的天朝持有者，不改普通州主管或配偶称谓。原版依据为`game/common/flavorization/11_tgp_china_flavorization.txt`及`_flavourization.info`。
- 天平参数直接按参数名取本地化，移除错误的`diarchy_parameter_`前缀，双语同步修正。原版摄政参数在`game/localization/english/diarchies/diarchies_l_english.yml`中同样直接使用参数名。
- 补充`gfx/interface/icons/diarchy_mandates/tca_tongpan_governance.dds`，复用原版`promote_authority.dds`。原版GUI的`Mandate.GetIcon`按指令读取图标，不覆盖GUI。
- `on_game_start_after_lobby`现在通过`tca_tongpan_startup`同步执行首次维护，首次暂停状态即可创建官职和分权；年度兜底、头衔与政府变化等回调继续使用次日防抖维护。开局产生的后续头衔回调仍可排队，但不再承担首次创建。

原生生命周期用例增至29断言：新增断言读取原始开局回调末尾记录的debug快照，要求存在符合条件的州且无缺失通判分权。快照只在首次开局回调写入，测试不通过再次调用维护补齐该断言。界面三项修复仍需重启后人工核对；脚本断言不代替实际称谓、文本和图标显示。

本轮验证记录：

- `run-tc8eb1fu`在两秒内退出，Steam API未连接，未派发用例，NOT VERIFIED。启动Steam并允许测试进程访问图形／Steam环境后继续。
- `run-4a1mhmbg`，通判单项29断言全部通过，观察者、汇总与同次日志核对通过，runner_exit=0。新增第29断言验证原始开局快照。
- `run-_33lf0u7`，完整117项：116 PASS、1 FAIL，607 CHECK_PASS、1 CHECK_FAIL。失败为`tca_test_imperial_circuit_lifecycle`第10断言：路持有者、提刑归属与法理都符合预期，但测试州官的直属领主变为路主管，未保持皇帝直属。无模组相关日志错误，整轮仍为NOT VERIFIED。
- `run-kytrnqmx`，提刑单项复现第10断言失败（13通过、1失败）；不能将通判单项通过当作完整共享回归通过。对照`run-9at9jylp`在`/private/tmp/tca-tongpan-startup-control`副本仅恢复旧次日入口，同样复现第10断言失败（13通过、1失败）；与`run-kytrnqmx`同用原生种子322648365。说明同步初始化不是复现所需条件，尚未定位州官重新归属的具体原生触发路径。没有修改或放宽提刑断言。主仓库保留同步初始化修复。

## 回归入口与当前边界

### 前一轮结果（本轮界面修复前）

独立1066中国观察者局`run-axpkt4pv`，只加载本模组与CLI适配模组。完整117项／607断言全部通过，零失败、未执行或缺少结果；观察者切换确认，`condition=summary`，`verification_exit=0`、`runner_exit=0`。墙钟240.3秒；`process_exit=-9`为取得汇总后由runner清理自身测试进程，不是测试中途退出。

本次完整`error.log`未发现模组相关错误，也核对了使用原版文件名的分权回调覆盖；仍有原版背景诊断，不能称整个error.log为空。工具检查107项通过，22个原版覆盖与27个追加回调登记／基线检查通过，空白检查通过。

原始产物目录：`/private/var/folders/f0/dh90nqcx6rsgf1558f91wmz40000gn/T/tca-game-tests/run-axpkt4pv/`，包含`terminal.json`、`result.txt`及`logs/debug.log`、`logs/error.log`。

通判28断言覆盖真实处决当次150威望、60影响力扣款，死亡当下原生继任以及延期分权同步，原版无效状态暂停／恢复，主管改制触发原始政府变更回调后的退出／恢复。原版处决测试只为带debug测试标记的角色预选“斩首”，与玩家在原生界面选择发送选项等价；未绕过权限、支付检查、发送或结算。处决观察钩子只记录实际资源差额。

日志核对工具补充识别重复on_action effect，并按覆盖登记识别原版同名文件中的模组诊断；对应Python回归保留。

### 执行方式与历史失败

原生事件 `tca_tongpan_test.1` 自备新主管与法理公国主管，当前29个断言检查原始开局生成快照、固定绑定、实际领主、专职契约、重复维护、称职度上限、各天平边界、七天后的分权、关闭destroy与原对象重启、池分配、真实处决扣款、死亡继任、原版特殊状态以及主管改制后的原始回调退出／恢复。池测试只验证分配器，不能替代真实扩展地图兼容验收。

运行 `python3 tools/run_game_tests.py --case tca_tongpan_test.1 --timeout 300`；完整组可用 `python3 tools/run_game_tests.py --timeout 900`。同时检查本次 `terminal.json`、`result.txt`、`debug.log`及完整 `error.log`。

初轮 `run-is3yu_2n`：89项通过后进程提前退出，未完成116项，结果为NOT VERIFIED。日志暴露空头衔尚无任命继承时查询候选分数、动态名称、缺失结束互动、权重base不能直接引用script value等错误；修复后必须新开局复测。不能把这一轮的已有断言视为通判验收。

中间单项`run-8dlz6gqi`、`run-98l2umuk`保留失败断言：普通绑定、启停恢复、档位与原生死亡继任已执行，但处决尚未发送／结算，继任后的延期维护断言失败。新增原版处决`on_accept`观察钩子，只对debug测试标记记录两种资源差额，不代付费用、不代替发送。失职回调改从绑定辖区主管排队，而不是从可能已独立的前任官员排队。后续仍须新局复测，不能用手动调用维护来掩盖原始回调失败。

`run-06m0ss3v`：24个断言通过，实际处决记录150威望、60影响力，但原版已故分权者变量错误导致NOT VERIFIED。`run-lsk_7un5`：117项／603断言通过，仍因两名处于原版分权无效状态的官员被指定为分权者而NOT VERIFIED；据此接入原版资格检查，并保留原失败断言、补充特殊状态与政府转换用例。最终结果另记，不把上述断言通过误作日志验收通过。

待验证：路／政事堂回退、升迁及跨政权转移、预留池耗尽、拘捕／撤销／收回及代理操作的通判实际附费、治理效率与法律界面、保存重载、真实地图扩展和长期平衡。已运行的司法拘捕组若通过，只证明共享入口未回归，不能替代伯爵通判附费场景。

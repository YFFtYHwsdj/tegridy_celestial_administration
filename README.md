# 一国三公 / Imperium in Imperio

CK3 天朝行政体系重做 mod。中央、地方官制分别提供因便／宋制，仅改变官名，名称切换各收200威望。提刑及地方、中央司法审批由独立的地方司法制度法律控制，改革收2000威望和1000影响力、冷却十年。检测到东方王朝或礼法与治道时退出普通官名管理。1066、1178中国政权默认宋式名称并设提刑，其他天朝政权默认因便且不设提刑。1066 开局的 15 个文官路由头衔历史声明固定提刑机构与路的对应关系，维护优先使用这些预定义无地官职，其他启用司法制度的开局与新设辖区动态创建；已有有效绑定保留。固定与动态官职废置时只撤销任职，保留对象和所属路绑定，恢复复用原 ID。机构历史暂未填入考证人物，开局空缺仍走既有补位流程。官职直接沿用持有者的原版天朝文官继承法及任命类型（允许同级升迁、启用原版任命冷却）；维护自动移除旧版提刑专属法。交接后校验专职无地资格，空缺或不合格持有者由补位流程另选或生成文官，随后恢复所属路关系、名称、纹章和销毁标记。提供只读诊断与维护测试决议，另有季度/年度维护。2026-10-10 已通过本次测试存档的死亡交接、异常补位及现任稳定性核对；同级调任、保存后重载等场景仍待验证。已接入分层身份评分、州／路辖区拘捕、刑部→御史→宰相→皇帝审批与公职囚犯交接脚本；刑事模块尚待游戏内完整验收。

名称选择、独立司法制度及验收：[朝廷官制](docs/court_system.md)。当前已接入脚本，法律界面及改制行为尚待游戏内验证。

首个设计模块：路级提点刑狱公事，包含刑事权限、举刺官吏、领主交互和功绩任命。

独立 debug 原型：[无地官署的路级法理归属](docs/judicial_de_jure_probe.md)。检查一人兼两路时的机构分属，不改变正式司法辖区规则。

设计规格：[提点刑狱公事 Spec v0.1](docs/song_judicial_title_spec.md)。

实现说明与原版/mod 写法分析：[提刑官职头衔生命周期](docs/judicial_title_lifecycle.md)。

1066 固定机构名单、历史人物补录与验收：[1066 固定提刑机构](docs/judicial_static_titles.md)。

## 本地加载

在 CK3 启动器中将“一国三公 / Imperium in Imperio”加入播放集并启用。当前声明的游戏版本为本机 1.20.0.4，不表示已完成兼容性或游戏内验证。

## 文件

- `descriptor.mod`：mod 包描述。
- `docs/song_judicial_title_spec.md`：设计与实现规格。
- 相邻的 `tegridy_celestial_administration.mod`：本地启动器描述，引用本目录。

首次任命实验与操作步骤：[提刑任命验证](docs/judicial_appointment_test.md)。

无地官员契约及验证说明：[官员义务、俸禄与预算](docs/official_contracts.md)。

分层权限与权重：[拘捕权限评分](docs/judicial_authority.md)。管辖包括本人及实际下属宫廷的成员与待招募宾客，提刑覆盖本路主官宫廷。伯爵级行政官职至少需要提刑许可，路主官本人须中央批准；成功后由发起者关押。

中央宋式称号按实际丞相、御史大夫官职头衔显示，不按地方官兼任的内阁席位改名。为避免额外兼容补丁，不覆盖内阁职位及首辅法律文本，接受卡片／法律名称与角色称号不一致。2026-10-11 已撤销此前为统一名称新增的覆盖并通过静态回归；界面待重启复测，总入口现有1组13项，详见[官制说明](docs/court_system.md)。

司法拘捕当前实现与验收：[司法拘捕及囚犯交接](docs/judicial_arrest.md)。AI 审批与后续拘捕均采用原生概率判定；合法理由+80。有效审批否决由请求者损失100威望、50影响力并产生关系后果；请求采用3个月全局、同目标1年冷却，明细沿用原生界面。

详覆羁押当前实现与验收：[详覆羁押](docs/judicial_custody_review.md)。提刑发送后直接按双方评分判定：成功接管本路其他统治者关押的囚犯，失败保留原关押者；使用可用牵制可直接移交。包含季度AI、公职登记、冷却及30项原生回归；此前版本84项/321断言通过；当前使用统一身份五档非线性费用／提刑失败代价、复合评分random_list及效果概率预览，2026-10-13专用测试局92项/354断言全部通过，确认页显示、自然季度AI与保存重载仍待单独验收；未修改GUI文件。

权限覆盖与原版漂移检查：[原版覆盖更新检查](docs/judicial_upstream_check.md)。运行 `python3 tools/scan_upstream_overrides.py` 可独立扫描原版与模组，检查覆盖登记是否遗漏；运行 `python3 tools/check_upstream_overrides.py` 可检查已审阅基线是否随原版更新发生变化。

开发工具包含原版覆盖检查、查漏扫描及其测试，另含本地化 BOM 检查。游戏行为的测试框架及使用方式见下方说明。

互动文本与作用域：[动态本地化](docs/judicial_localization.md)。

提刑同级调任的职位价值：[提刑重要性算法与验证](docs/judicial_prominence.md)。已实现独立公式，静态检查通过与游戏内验证分别记录在该文档中。

王国级圣职区验证已终止：宗教层级、共同显示与宗教竞争不适合用作天朝官职，测试文件及原版事件覆盖已移除。完整结果与原型源码见[验证记录及归档附录](docs/clerical_region_probe.md)。正式提刑仍使用原有公国方案。

## 测试框架

支持 CLI 自动新开专用观察者测试局：`python3 tools/run_game_tests.py`。当前为 macOS 带窗口运行，无需 computer use；自动启用 debug/develop、推进日期、执行全组并核对独立日志。适配模组仅由工具加载，正常开局不自动运行。参数、退出码与限制见[CLI 测试说明](docs/cli_game_tests.md)。

测试直接维护为游戏原生的隐藏事件，不再使用Python生成器或中间测试源。Python工具负责启动编排、日志核对、登记及原版覆盖检查，不生成测试，不模拟游戏业务。

- `events/tca_court_test_events.txt`：13项官制测试。
- `events/tca_judicial_law_test_events.txt`：44项司法法律测试。
- `events/tca_judicial_loading_test_events.txt`：3项加载／命名测试。
- `events/tca_custody_review_test_events.txt`：30项详覆羁押测试，25项即时及5项串行延迟，包含直接发送结算、后续结果核对和自然清理保护。
- `events/tca_judicial_timing_test_events.txt`：4项真实延迟测试，每项等待两日。
- `events/tca_judicial_arrest_test_events.txt`：路长官对五类无地头衔目标的原生发送、批准／否决与收押回归。
- `events/tca_tests_events.txt`：总入口和串行延迟调度。
- `events/tca_test_entry_test_events.txt`：观察者入口的角色解析回归。
- `events/tca_test_lifecycle_test_events.txt`：临时死亡保护、恢复及真实死亡回调回归。
- `events/tca_test_status_test_events.txt`：状态快照及关闭／重新显示回归。

### 游戏内运行

重启专用1066中国debug测试局，通过“调试：模组一键测试”或`event tca_tests.1`运行；观察者使用`effect tca_run_observer_tests_effect = yes`。macOS优先运行`python3 tools/run_game_tests.py`，自动建立独立观察者局。当前115项、574个断言，运行期间不重复启动、不切换请求角色。测试会修改世界状态，不在正常游玩存档运行。

拘捕流程严格检查即时收押；第20日核对绑定观察标识的释放／死亡证据，未知原因单独记录。CLI不覆盖原版赎回、释放或处决互动。完成后核对同次日志；当前实现和最新验收见[统一测试文档](docs/mod_tests.md)，此前实验与失败记录见[历史记录](docs/history/mod_tests_history.md)。

单项入口沿用现有事件编号，例如`event tca_judicial_loading_test.1`。测试期间不重复启动、不切换请求角色。等待没有结束或前置不满足不能算通过。

完成后运行`python3 tools/check_test_run.py`，核对每项及每个编号断言的结果，并人工审阅同次error.log。

### 编写或添加测试

直接编辑对应测试事件，准备独立场景、调用正式trigger/effect、检查实际结果。保留BEGIN、CHECK_PASS／CHECK_FAIL和PASS／FAIL／PRECONDITION_FAIL日志，以及现有统计与防重逻辑。延迟测试使用原生`trigger_event = { id = ... days = 2 }`和续接事件，不新增wait_days字段。

新增用例在`events/tca_tests_events.txt`登记入口，并同步计划数量；延迟组串行入口也要维护。运行`python3 -m unittest discover -s tools -p 'test_*.py'`检查用例登记、数量及日志读取；覆盖对象改动另运行`python3 tools/check_upstream_overrides.py`。没有生成步骤。

### 验证范围

当前测试夹具修复已通过两轮完整回归：2026-10-15，CK3 1.20.1，固定种子局 run-5tr6bhkv 和独立随机局 run-l5defgvd 均为115项／574断言全部通过，零失败或未执行，日志核对通过且error.log无tca_记录；100项工具测试、原版覆盖和差异空白检查通过。修复维护前快照复用、等待中的人物池角色缺少防清理保护，以及测试长官职业任命未落在指定角色上的准备问题；原业务断言保留，新增当前状态反例与真实维护执行证明。旧人物池综合断言的唯一历史触发条件仍不能从旧日志精确还原，界面及保存重载也不由自动回归替代。完整证据见[夹具修复记录](docs/judicial_de_jure_probe.md#测试夹具修复2026-10-15当前实现)。

历史原型验收：2026-10-14 10:29，CLI独立1066中国观察者局111项／495断言全部通过，无失败或未执行；观察者、汇总及日志核对均确认，完整error.log无tca_记录。90项Python工具测试和原版覆盖检查通过。原版背景错误、界面、自然AI概率及保存重载不由这些结果替代。

前次通过的完整自动回归涵盖路级司法、世族庄园归属、改法当日撤任及法理调整：2026-10-15核对独立观察者局115项／567断言全部通过，零失败或未执行；同次日志核对通过，error.log无tca_记录。98项工具测试与原版覆盖检查通过。停用、废置或销毁时保留官署对象及原路绑定，但不再属于真实路法理树；恢复后重新挂回。引擎内部仍保留退役父引用，不等于把父字段置空。改法时序修复、一次尚未查明原因的庄园夹具缺员及本轮复测见[法律测试](docs/judicial_law_tests.md)。完整证据及界面、保存重载的待验边界见[司法验收记录](docs/judicial_de_jure_probe.md)。
详细规则和复现记录见[统一测试文档](docs/mod_tests.md)，具体场景见[官制测试](docs/court_system_engine_tests.md)及[司法法律测试](docs/judicial_law_tests.md)。界面显示、异步互动、AI概率、保存重载等按模块分别验收，断言通过不等于完整玩法已验证。


拘捕审批及后续观察的当前契约与失败到通过记录见[原生审批测试](docs/judicial_arrest_native_tests.md)。

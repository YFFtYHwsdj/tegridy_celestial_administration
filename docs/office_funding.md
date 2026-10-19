# 地方官署经费

## 设计与当前接入

2026-10-18：正式接入提刑与通判的地方国库拨款。只面向新开局，不提供旧三档契约的迁移。帅司及其特殊规则不在本模块范围。

路司五档为紧缩2%、从俭4%、常额6%、增拨8%、优给10%；通判为5%、10%、15%、20%、25%。默认常额。比例直接乘以本辖区实际收到的发展金减去继续下发的发展金，负数按零处理。各官署独立领取，不按权重瓜分，不重新分配空缺份额，不根据付款国库余额同比缩减，不设欠款与追补。

提刑的付款人为 `song_judicial_circuit.holder`；通判为 `tca_tongpan_county.holder`。付款关系取辖区绑定，不取官员直属领主。转运使是路级主管，本职不另领一笔。经费进入人物国库，个人金币俸禄仍由原版 `celestial_salary` / `celestial_salary_rank` 处理。

契约待遇属于头衔。`tca_office_budget_level` 在首次官员身份维护时从原生契约读取，在两侧正式改约获准后更新；换任维护恢复该头衔原档位，不用新任默认档覆盖。未持有官员主头衔的角色不从这个人物入口更新其他官署待遇。读取与结算按官署遍历，保留逐司计算结构；当前正式任命模块仍限制提刑专职，尚未新增其他路司或开放其兼任，不能将此结构宣称为完整兼任玩法。

收付人同一时不执行转账、不列入预计收支，不制造额外收入。官署空缺、辖区／反向绑定失效、制度停用、双方跨政权或付款方不适用时停止拨款，不自动由皇帝兜底。任免不追溯、不按天拆分；结算时使用当前有效持有人、契约和基数。

经费拆成两个原生契约：`tca_circuit_office_budget` 只向提刑等当前登记的路司显示；`tca_tongpan_budget` 只向通判显示。两类由独立资格 trigger 筛选，均默认第三档，协商分值沿用-2至2，对契约领主好感按原版五档俸禄取-25／-15／0／+5／+10。好感对象与辖区付款人可以不同，沿用原生契约关系，不另建重复好感修正。改约成功后读取本署对应契约，把档位保存到头衔；换任维护只恢复对应类型，不改另一类待遇。旧共用经费契约及十个具名修正已撤回，不做旧存档迁移。

改约权限与付款职责分别处理：通判由对应州长官及其直属领主修改，提刑仍由正常直属上级修改。两侧原生互动接受后均保存同一官署头衔档位；没有把官员改挂给州主官来获得窗口权限。具体入口、原生请求限制及验证边界见[官职契约](official_contracts.md)。

比例集中在 `tca_*_funding_*_rate_value`，各档独立配置。结算直接按本署类别与头衔保存档位取数；契约说明读取同一数值，直接写明所属路／州及比例，不再并列两类机构或展示人物状态修正。月度实际转账、下期预计与收付明细仍共用现有入口。当前任命模块的兼任限制不变，不能将该结构宣称为完整兼任玩法。

## 实现入口

- `common/script_values/tca_office_funding_values.txt`：两类契约的比例、基数、逐署金额及人物预计收支。
- `common/scripted_triggers/tca_office_funding_triggers.txt`：现有制度和辖区双向绑定检查。
- `common/scripted_effects/tca_office_funding_effects.txt`：头衔待遇记录／恢复与实际资金转移。
- `common/on_action/tca_office_funding_on_actions.txt`：追加 `dynastic_cycle_monthly_pulse`；复用司法路、通判州的全局登记表，不扫描所有人物。
- `common/subject_contracts/contracts/tca_official_contracts.txt`：两类独立五档原生契约，移除临时借用的中央朝臣预算。官职项仅保留提刑与通判，不再预留武职入口。
- `common/character_interactions/zz_tca_official_contract_interactions.txt`：原版行政改约成功后记录官署档位。
- `gui/tca_office_funding_types.gui` 与 `gui/hud.gui`：原生国库明细追加经费行、修正收入／支出合计和顶栏净额。原生项目保持可见。

每个官署在 `tca_office_funding_paid` 记录结算日期，满30日才能再次结算，阻止重复月脉冲和换任后的重复领取；不依赖同日变量到期与回调顺序。王朝循环的月脉冲是原生约30日节奏，并不代表各人物财政缓存已统一刷新。没有活动王朝循环的政权尚无独立补充月调度。

批量结算先为全部官署锁定 `tca_office_funding_quote`，再执行收付，避免前一笔赤字触发原生财政刷新后改变后一笔基数；临时报价在同一回调消费并清理。每笔支付保存实际付款人、收款人，以同一金额扣款、入账。只对正额调用效果；本机 `remove_treasury = 0` 会产生脚本错误。资金转移不进入原生月收入，避免自身经费反馈进下一期基数。

## 原版依据与边界

本机参考为 CK3 1.20.1.1 Crozier、macOS ARM64。`monthly_character_treasury_variable_income` 的原生定义是全部国库收入减封臣发展金支出，不是扣除全部支出的净余额。前期原型在普通路、州主官上验证了该值与所需净额一致；玩家财政刷新和AI缓存更新时点不同，不能声称统一实时读取。

**尚未解决的取数边界：** 如果地方主官另有原生国库收入，这个字段也会包含它，不能精确排除。本模块没有实现中央兼职，也没有把脚本官署经费加入该字段；但不能据此声称任意额外原生收入都已排除。独立君主的直接税收国库不作为发展金基数，当前返回零。正式验收应保持这一限制显式可见。

顶栏显示下期预计，按当前持有人、头衔档位和原生基数计算，不显示上次实付冒充预测。付款方预计遍历本人持有辖区的绑定官署，收款方遍历本人持有的官署；不进行每帧全世界扫描。该显示扩展不会自动改变原生AI预算、账簿、人物窗口或其他直接读取原生月收入的接口。不能声称注册了原生 monthly modifier 或所有原生财政窗口都已同步。

覆盖登记沿用现有契约组、行政互动和HUD条目；新增王朝循环月回调为同名追加，登记于 `tools/upstream_overrides.json`。没有修改游戏安装、Workshop 或可执行文件。全HUD替换的兼容范围仍是其他替换 `gui/hud.gui` 的模组。

## 验证

原生测试入口：`events/tca_office_funding_test_events.txt`，登记于全组 `events/tca_tests_events.txt`。检查正式州／路绑定、五档不同费率、实际州／路国库支付、收支守恒、防重、基数无反馈、制度停用、余额不足足额支付、同人自付、头衔往返授予后档位恢复、两次自然月结及原生预算无重复收入。运行 `python3 tools/run_game_tests.py --seed 1538798675 --timeout 360`，核对本次 `terminal.json`、`result.txt`、源码清单及 `error.log`。

待补充验收：真正改约互动路径、官员和付款主官死亡／继任、空缺恢复、完整兼任玩法、真实负基数、保存重载、实际悬停布局、各语言、界面缩放、其他财政窗口一致性。直接调用维护或支付效果的通过不能替代这些路径。

## 2026-10-18 正式库验证记录

- 静态检查：126项工具测试通过；24个原版对象、29项同名追加、2份整文件GUI覆盖的登记／基线检查通过；中英文本地化BOM通过。只核对本次修改，保留其他研究工作。
- 单项：`run-_k2md2qf`，入口 `tca_office_funding_test.1`，1 BEGIN／1 PASS／22 CHECK_PASS，零失败或未执行；观察者、汇总、冻结源码、同次日志核对通过，verification_exit和runner_exit均为0。
- 完整组：`/private/tmp/tca-funding-final-runs/run-g23gf9q8`，CK3 1.20.1.1 ARM64，独立1066中国观察者局，种子1538798675，仅本模组与CLI适配；120 BEGIN／120 PASS／709 CHECK_PASS，零失败和未执行。`terminal.json`、`result.txt`、观察者确认、源码快照及同次日志核对通过，两个退出码均为0，未检出模组相关引擎错误。源码SHA-256：`ec2d9f0eeb5fc4014896c0d3a15eba013de23b2446c64c822a4c3c90ae6332ff`。本轮未运行可选严格首位继任模式。

失败记录保留：`run-w9qdjisl`在沙箱中Steam初始化失败，未运行断言；`run-dj1jgv_i`原119项通过，新用例因固定洪州前置不成立未执行。改为自行维护机构并选取符合条件的州、路后，`run-w1azohk0`16条断言通过。

`run-8g3cj97_`完整组118 PASS、4条失败：新增自付第20条及既有通判第28、46、56条。后续自付诊断 `run-1xlodjy4`记录临时授职前600、授职完成900、经费效果后仍900，金额0且无支付标记；原断言误把授职的原生资金变化算作拨款。现改为以授职后余额检查零转账，并清理临时授职资金；仍检查实际同人持有、零金额、无支付标记和待遇保留。`run-cljlph7c`含失效调试作用域错误、`run-1xlodjy4`含诊断变量仅本地化读取的错误，均为NOT VERIFIED，不作为通过证据。正式源码已移除这些诊断。

此前三条通判继任断言本轮完整组已通过，但没有单独隔离其波动原因，不能声称修复了该既有继任问题。所有原断言保留，没有删除或放宽。

此前临时净额原型53断言不是本轮正式库验收。界面探针的表达式核对与真实视觉验收分别记录，不与资金断言合并计数。


### 正式HUD表达式核对

`/private/tmp/tca-formal-funding-hud-runs/run-gfixpmui`：独立1066皇帝开局，在暂停状态准备正式河南路机构后切换为该路主官。冻结正式HUD只加入原生检查模板，不替换正式计算或明细类型；正式收支提示框及脚本分项明细也在真实HUD上下文实例化。HUD装载确认及3项断言通过：正额地方官署支出并入净额；停拨后恢复原生净额；优给档恢复后原生收入合计加调整后的支出合计等于顶栏净额。观察到真实玩家角色切换、全部PASS唯一，无FAIL；terminal为complete、verification_exit为0，源码冻结与同次日志核对通过，未检出模组相关错误。启动与清理由 `/private/tmp/run_tca_formal_funding_hud.py` 编排，原生断言和控件源保存在该运行适配副本。

分项名称使用脚本值中的 `tca_funding_display_office` 临时头衔作用域，不假定GUI的THIS就是当前官署。`run-ol48ymxf`曾因测试控件注册错误及THIS名称上下文报错中止；`run-h9xou37k`没有成功进入指定地方玩家的测试阶段，超时；`run-kwm1nije`在玩家切换重建HUD及准备／断言同帧时产生重复装载及短暂FAIL。最终探针改为单向阶段、每次准备后一秒再检查，PASS去重但保留全部FAIL，未放宽数学条件；生产结算逻辑未因取样问题调整。

上述旧探针只证明其额外上下文下的表达式计算，不能证明实际悬停提示框的数据绑定。用户随后提供的实际截图已暴露该遗漏：新增行金额和合计为空、零额行仍显示，并出现多余“无数值”。旧探针对提示框额外注入 `datacontext = "[GetPlayer]"`，掩盖了生产提示框未绑定 `Character` 的问题；不得把这次旧结果作为实际提示框正常的证据。鼠标悬停、文字颜色、点击命中、缩放或溢出的视觉表现、收款官员玩家、所有语言及保存重载均未覆盖。人工复现：新开局选路／州主官，查看国库提示；依次调整官署五档、令官署空缺／恢复，核对付款与收款预计及下一次到账；保存重载后重复。不要在正常游玩存档运行回归事件。


### 提示框人物上下文修正

实际国库悬停提示框的收入／支出区块只明确传入 `ValueBreakdown`，没有提供可依赖的 `Character`。2026-10-18将专用类型里的金额、显示条件、合计及分项提示统一改用 `GetPlayer.MakeScope`，与顶栏净额绑定同一玩家。经费为零时隐藏对应行；仅当原生分项和经费均为空时显示“无数值”。收入按原版习惯显示带正号的绿色金额，收支金额右对齐。未改变结算或契约机制。

静态回归入口 `python3 -m unittest discover -s tools -p 'test_*.py'`，新增 `tools/test_office_funding_gui_contracts.py` 两项绑定约束；使用修正前GUI副本时按预期失败，修正后128项全部通过。原版覆盖登记／基线检查及本次范围空白检查通过。静态检查不模拟引擎显示。

本次界面验收按用户截图分三种角色，重新载入GUI后分别检查：

1. 无官署经费往来的皇帝：两条官署经费行均隐藏，收入／支出原生分项和合计保留。
2. 向属署拨款的路／州主官：只显示非零的地方官署经费支出，支出合计包含该扣减；没有经费收入时隐藏收入经费行。
3. 收款的提刑／通判：显示官署经费收入及收入合计，没有经费支出时隐藏支出经费行；真正空的支出列表可显示“无数值”。

上述角色均需核对明细收入合计加支出合计等于顶栏月度净额；本轮自动HUD探针尚不能替代这三种角色实际鼠标悬停的外观验收。当前界面工具无法定位CK3应用，未取得修正后的实际悬停截图。

移除探针对提示框的 `GetPlayer` 数据上下文注入后，首次复测 `/private/tmp/tca-formal-funding-hud-runs/run-5fa8ckga` 出现首项短暂 `FAIL_1`，随后三项PASS；整体仍为NOT VERIFIED，不能以随后PASS抵消失败。没有检出模组相关引擎错误。复测保留原数学断言及全部FAIL记录，将切换玩家并强制刷新财政后的首次等待由1秒改为4秒；这只调整测试取样，不改变生产财政计算。

等待调整后的复测 `/private/tmp/tca-formal-funding-hud-runs/run-7789ooa4`：独立1066局、种子1538798675，正式河南路主官HUD装载，3项原数学断言均唯一PASS，无FAIL；terminal为complete，verification_exit为0，冻结源码与同次日志核对通过，未检出模组相关引擎错误。提示框实例不再额外注入人物上下文，正式GUI与冻结运行副本逐字节一致。运行源码SHA-256：`dab849565495d442e030510aaafa96dcd529cfc42f2b08237aa80d49b2f8064c`。该结果覆盖正式类型装载及正额／停拨／提高档位后的净额计算，不证明实际悬停的文字、零额行可见性或布局；后者仍按上述三类角色人工验收。

### 经费提示的交互与人物明细

用户实际截图确认上一轮金额和零额行问题已改善，但外层经费金额缺少下划线，展开后仅显示地区名，数字又继承原版递归脚本值提示的绿色和下级链接。现将两层显示分开：

- 外层国库经费数额保留下划线和悬停入口，仍以当前玩家的正式预计收支为来源。
- 经费收入明细显示所属州／路的拨款主官；支出明细显示收款官员。使用人物原生 `GetName`，保留人物悬停与链接，不再以不带官职的地区名代替。
- 官署经费专用分项控件直接枚举原生 `GetPlayer.GetTitles`；每个头衔以正式金额入口计算，按普通 `|1` 数字显示，不使用递归 `ValueBreakdown.GetValue` 的自动着色或下级数字提示。分项收入为普通正额，支出转为普通负额；不改变实际支付金额。
- 新增 `tca_local_office_funding` 游戏概念，国库两条经费标签都可查看说明。概念说明付款层级、净额基数、契约比例和空缺不拨款，不引入新的经费规则。

新增入口：`common/game_concepts/tca_office_funding_concepts.txt`；专用分项GUI仍在 `gui/tca_office_funding_types.gui`。中英文名称和概念说明在现有官职契约本地化文件同步维护并保留BOM。新增两个辖区头衔显示读取值 `tca_office_funding_judicial_expense_value`、`tca_office_funding_tongpan_expense_value`，缺少绑定时返回零，有绑定时调用原有 `tca_office_funding_amount_value`；不另算费率。收入直接按所持官署取正式金额，按机构标记选择所属州／路的付款人。没有新增界面名单、缓存、月度维护或付款效果。

本轮静态检查130项工具测试通过；新增样式约束对上一轮GUI副本按预期失败。人物名称实际解析、类型加载与视觉悬停分别验证，不把纯文本约束当作人物悬停成功的证据。

本轮失败／诊断记录：`run-dp50omzl`、`run-pj4p_2p3`、`run-l_eaybbw`均仅三项净额断言通过，新增的两项人物分项断言没有完整执行，整体NOT VERIFIED。探针的父容器、初始可见状态和数据上下文陆续核对，不能把没有FAIL标记当作姓名正确。`run-8e1xl0nh`向 `GuiScope.AddScope` 传入数字变量导致测试绑定转换错误；`run-_wz7ozzq`还包含诊断探针热更新、快照变更与提前退出，均排除为通过证据。上述错误位于临时适配探针，未引入正式GUI。所有人物匹配条件保留。

最终显示方式采用原生人物头衔列表，避开脚本值计算树的地区分组。参考本机 Workshop `3807197628`（朝闻道：修仙之路1.2.3，声明支持1.20.1）`gui/zwd_ledger_accounts.gui` 中逐所持头衔的账簿写法：`GetPlayer.GetTitles` 提供 `Title`，并使用 `Title.MakeScope.HasFlag` 检查变量；参考仅作接口依据，本模组不加载或修改该模组。原生回归第7、18条保留原条件并追加两个显示读取值与实际官署金额一致的断言，计划数量仍为22。

补充诊断：`run-mv96uxw9`三项净额通过，但人物断言仍缺失；`run-z2ytpg_6`晚于机构准备创建了分项控件，但 `Localize` 命令无法读取条目中的 ValueBreakdown，出现诊断本地化错误；`run-m7i2_l83`直接展开计算树的诊断局提前退出。这些均为NOT VERIFIED，不用作人物显示正常的证据，诊断控件没有进入正式库。

原生头衔列表方案的有效复测：`/private/tmp/tca-formal-funding-hud-runs/run-qtrrhudi`，CK3 1.20.1.1 ARM64、独立1066中国局、种子1538798675。真实地方主官HUD装载及5项断言均唯一PASS、无FAIL：三项原净额条件，另两项按正额头衔行核对收款官员与拨款主官的原生姓名。姓名表达式直接从正式GUI提取；测试在机构建立后创建角色控件，分项用原生 `Character.GetTitles` 显式提供对应角色的头衔，生产默认 `GetPlayer.GetTitles`。不向生产提示框补注隐式Character上下文。terminal为complete、verification_exit为0，源码冻结及同次日志核对通过，未检出模组相关引擎错误；正式GUI和数值文件与冻结副本逐字节一致。

本结果验证类型装载、正式姓名表达式及数值绑定；不证明实际鼠标悬停的人物肖像、点击跳转、文字下划线、颜色、长名称裁切、缩放及中英两种画面。这些仍需按三种角色的实际悬停步骤验收，不能将5项表达式检查改称完整GUI验收。

资金单项复测：`/private/tmp/tca-funding-presentation-finance-runs/run-gnj0zynj`，同版本、同种子，独立1066观察者局；入口 `python3 tools/run_game_tests.py --case tca_office_funding_test.1 --seed 1538798675 --timeout 360 --run-root /private/tmp/tca-funding-presentation-finance-runs`。1 BEGIN／1 PASS／22 CHECK_PASS，零失败及未执行，包含新增的路／州显示读取值与实际官署经费一致检查；观察者确认、terminal、result、源码快照和同次日志核对通过，verification_exit和runner_exit均为0，未检出模组相关引擎错误。源码SHA-256为 `7262cbc7b15527a43da230d3f0c743c2fdd63f62c73d88e295aa83306d0775f6`。本轮没有重跑120项完整组；此前完整组属于此前源码，不能视为本次完整验收。

### 经费提示框的焦点颜色、对齐与总计修正

用户实际截图确认人物行和负额已显示，但标题居中、数额没有贴到统一右边界，且缺少原版的白／灰焦点颜色与底部总计。本轮仅修改 `gui/tca_office_funding_types.gui` 的显示及相关静态约束：

- 标题明确左对齐，列表和各级行容器横向铺满。人物列保留原版宽度约束，金额列同样设为扩展并右对齐，填补人物列达到最大宽度后留下的空白。
- 标题、人物、分项金额、总计文字使用原版 `TooltipInfo.GetTintColor`，让焦点提示框及失焦提示框沿用白／灰着色；金额仍不附加红绿语义颜色或数字链接。
- 两类明细底部增加原版 `BREAKDOWN_ENTRY_TOTAL_TREASURY` 标签（中文“总国库”），收入为正额，支出为负额，直接复用当前玩家外层经费行的正式读取值，不在GUI重算。

原版参考：`game/gui/shared/value_breakdown.gui` 的 `widget_value_breakdown_list` 对姓名及数值设置焦点 tint，普通数额节点采用扩展宽度和右对齐；`game/localization/*/core_l_*.yml` 提供现有总国库标签。没有新增本地化或修改资金结算。

静态布局约束在修正前副本按预期断言失败，修正后130项工具测试通过，原版覆盖登记／基线检查与本次范围空白检查通过。静态约束只防止再次遗漏颜色接口、总计及扩展容器，不证明实际像素对齐或鼠标移入后的颜色变化。

本轮加载／绑定复测：`/private/tmp/tca-formal-funding-hud-runs/run-7rl7teuh`，CK3 1.20.1.1 ARM64、独立1066中国局、种子1538798675，HUD装载与既有5项收支／人物绑定断言均唯一PASS、无FAIL；terminal为complete，verification_exit为0，源码冻结与同次日志核对通过，未检出模组相关错误。正式GUI与运行副本逐字节一致，源码SHA-256为 `fe32d57d156dd1090f3f87bfd032f528878030653317ab96542fab3f362bf4af`。本轮没有修改或重跑资金结算；仍未取得修正后的实际悬停截图，白／灰切换与左右边界的像素效果不能由这5条绑定断言代替验收。

### 人物页国库月净额

用户截图中的人物页国库提示由 `game/gui/window_character.gui` 的 `Character.GetTreasuryTooltipWithBalance` 生成，其本地化键为原版 `TREASURY_WITH_BALANCE_TOOLTIP`，只带原生余额和月净额。此前只接入顶栏，因此外国官员即使能收到经费，这里仍会显示原生的0.0／月。

新增 `gui/window_character.gui` 整文件覆盖，仅将这一处提示改为 `tca_office_funding_character_treasury_tooltip`：库存仍读取当前窗口的 `Character.GetTreasury`，月净额读取 `Character.MakeScope.ScriptValue('tca_office_funding_balance_value')`。保留原版两行样式及中英文月份文本，不改全局原版本地化键，不使用顶栏玩家或 `InGameTopbar`。因此查看非玩家官员、付款主官或普通人物时，均以实际查看对象计算。

必要性与兼容：该国库行直接内嵌于原版人物窗口，没有独立可替换类型。本轮没有找到局部覆盖该属性的原生入口；采用整文件覆盖，与其他替换同一人物窗口的模组冲突。已登记 `tools/upstream_overrides.json`，完整原版基线位于 `tools/baselines/office_funding_window_character.gui`。静态回归比较所有非注释token，恢复这一提示键后须与基线完全一致；其他窗口可执行内容保留原版。说明性注释译为中文，原版停用代码样例保留。

静态检查132项工具测试通过，覆盖检查通过（24个原版对象、29项追加、3份整文件GUI覆盖），本次范围空白检查通过。新增用例约束整文件仅改一个提示键，并检查中英文本地化都读取 `Character` 而不是 `GetPlayer`。原版参考还包括 `localization/*/core_l_*.yml` 的原提示样式，以及 `gui/hud.gui` 通过 `ToggleGameViewData('character', GetPlayer.GetID)` 打开人物窗口的原生入口。绑定及真实人物页验证另记，不把静态比较当作悬停通过。

人物页首轮 `run-14cqtm9t`：原5项通过，但第6项未执行到结果，整体NOT VERIFIED；测试HUD中的窗口状态查询未可靠触发打开操作，不能宣称已验证人物页。后续探针只在指定阶段直接调用原版 `ToggleGameViewData` 并记录实际调用，保留所有原条件和FAIL记录。

有效复测 `/private/tmp/tca-formal-funding-hud-runs/run-3ebizqxq`：CK3 1.20.1.1 ARM64、独立1066中国局、种子1538798675，仅主模组及临时CLI适配。先以河南路主官为玩家，完成5项原收支／人物绑定检查，再实际调用打开该路提刑的人物窗口。第6项探针注入冻结副本中真实人物窗口的国库行，不注入额外Character；要求窗口人物为绑定提刑、非本地玩家、官署经费收入为正，且窗口人物月净额等于其经费收入（该官员原生净额为零）。新提示本地化还在同一窗口上下文中实例化，用于检查数据绑定错误。

HUD装载、原生打开调用及6项断言均有唯一记录，全部PASS，无FAIL；terminal为complete、verification_exit为0，源码冻结及同次日志核对通过，未检出模组相关引擎错误。去除测试注入后，冻结人物窗口与正式文件的非注释token一致，中英文本地化逐字节一致。验证了实际外国官员窗口的数据来源和经费净额，不等同于已取得鼠标悬停截图；真实鼠标悬停的两行文字外观仍待人工确认。本轮没有改动或重跑资金结算。

其他已知入口：原版 `gui/window_ledger.gui:6233` 和 `gui/window_title.gui:446` 也直接使用 `GetTreasuryTooltipWithBalance`，仍属原生读数。本次人物页补接没有覆盖这两个整文件；将来接入时应分别使用行人物与头衔持有者，不能把人物窗口的Character上下文或当前玩家直接套用过去。

### 路司比例调整复测（2026-10-18）

本节记录先前的步长实现；下述比例保留，当前拆分契约实现以文首及后续验收为准。

路司五档调整为2%／4%／6%／8%／10%，默认6%；通判仍为5%／10%／15%／20%／25%。两类分别配置步长。中英文契约说明同步更新。

原生回归入口 `tca_office_funding_test.1`，独立1066观察者局、种子1538798675，CK3 1.20.1.1 macOS ARM64；结果目录 `/private/tmp/tca-funding-rates-runs/run-8jjjpfe_`。1项用例、22项断言通过，含五档比例、实际转账、收支守恒、任免待遇保留与自然月结；观察者切换确认，runner与verification退出码均为0，同次日志未检出模组相关引擎错误。132项工具测试、原版覆盖检查及范围内格式检查通过。测试冻结后只补充契约说明性注释与本文记录，未改变执行逻辑。未重新进行界面悬停验收。

首次沙箱内启动 `/private/tmp/tca-funding-rates-runs/run-ow8sb73p` 在加载前退出，未执行断言，不计为通过；上述有效结果来自允许Steam图形环境的重试。

### 具名经费修正与单项验收（历史，2026-10-18，已撤回）

本节只保留探索和验收记录。具名状态没有满足通用数值 modifier 的需求，当前已移除；不作为现行设计或兼容接口。

本机 Workshop `2887120253`（Elder Kings 2，版本0.20.0.1，声明支持1.19.0.6）在 `common/script_values/ek_magic_values.txt` 第1130行附近，用 `has_character_modifier` 检查 `wild_magic_weak` 等状态，再加入配对数值和说明。本模块借鉴这种“具名状态＋脚本解释”的结构，不复制其法力规则，也不把其版本声明当作本模组兼容性证明。

原版 `common/modifier_definition_formats/_definitions.info` 说明该目录只控制既有属性的格式，不能注册新的底层属性。当前契约描述通过 `GetModifier(...).GetNameWithTooltip` 链接具名修正，不在 `subject_modifier` 中伪造可执行字段。路司与通判分别使用五个状态，比例各自独立集中在 `*_modifier_value` 中，具名修正的说明也读取同一数值。改变修正状态会影响实际收付，而不是仅改变显示。

新增原生断言23至26，检查最低档挂载、切至最高档时替换旧修正、移除修正后经费归零，以及原生头衔交接同步新旧任。修复前独立局 `/private/tmp/tca-funding-modifier-runs/run-13_3nsut` 为22通过、4失败，整体 NOT VERIFIED；接入后的 `/private/tmp/tca-funding-modifier-runs/run-abea9idj` 为1项用例、26项断言全部通过。均为CK3 1.20.1.1 macOS ARM64、1066独立观察者局、种子1538798675，仅本模组及CLI适配。复测观察者确认、runner与verification退出码均为0，同次日志未检出模组相关引擎错误。复测源码SHA-256：`c82a80a2f02aba3aeec04d8e27a99a25f48dbfbd839d4e0a09b95fbac38dd38c`。

132项工具测试、原版覆盖检查及范围内格式检查通过。新增两个原生头衔回调均登记为追加。契约中具名修正链接的实际悬停、人物修正图标和说明排版尚未做画面验收；不将原生收付断言当作UI验收。

完整回归 `/private/tmp/tca-funding-modifier-full-runs/run-lxgbtk49`：同版本、场景与种子，`python3 tools/run_game_tests.py --seed 1538798675 --timeout 480`。120项用例、713项断言全部通过，零失败或未执行；观察者确认，summary结束，runner与verification退出码均为0，快照核对无问题，同次日志未检出模组相关引擎错误。完整运行冻结后仅调整契约注释、英文标点和文档，执行逻辑未变化。

### 明细空白行修正（2026-10-18）

用户截图显示一项收款人物与总计之间有多余空白。原布局按所持头衔创建外层项目，只隐藏内部零额类别行；外层空项目仍可占用列表间距。收入、支出明细现在都在整个头衔项目上判断正额，并在列表和项目内部显式设置 `ignoreinvisible = yes`。属性参考原版 `gui/shared/succession_election_widgets.gui` 的原生容器写法。

新增静态回归先失败、修复后通过，全部133项工具测试、原版覆盖检查及范围内格式检查通过。独立1066局、种子1538798675、CK3 1.20.1.1 macOS ARM64，运行 `/private/tmp/tca-formal-funding-hud-runs/run-3io1y4a0`：正式付款主官HUD实际加载，5项原生表达式／姓名绑定断言唯一通过，COMPLETE结束，verification_exit为0，快照核对及同次日志检查通过。该探针覆盖类型加载和既有数据绑定，不测量空白像素；实际悬停时空白消失仍待画面复测。本次不改变经费数值和结算逻辑，未重跑资金全组。

### 契约税兵提示的原版来源（2026-10-18）

原版 `gui/interaction_modify_vassal_window.gui` 的树形、单选及其他档位按钮均调用 `ModifySubjectContractInteractionWindow.GetObligationLevelTooltipFor`。本机二进制对应 `NSubjectContractInterfaceUtil::GetObligationLevelTooltipForContract`：当前档位调用 `AppendCurrentContractTooltip`；其他档位调用 `AppendContractChangeTooltip`。前者读取整份契约的 `CalcTaxContribution` 与 `CalcLevyContribution`，非零就追加税兵比例文字；没有先按当前契约类型或无地身份排除。后者比较变更前后的整份契约贡献。这说明经费说明里的税兵数字是通用预览，不是经费档位新增的征收比例。

原版 `celestial_obligations` 仍提供税收0.75、征召兵0.3的基础值，随后受臣属贡献修正影响；不能把截图95%与36%直接解释为经费档位的效果，也不能在未保存该人物修正明细时强行断言这两个最终值的具体来源。比例非零不等于实际缴纳金额或兵数非零。原版主面板还显式排除了向国库领主缴纳金币的进度条，而上述档位提示使用另一条路径，存在显示口径差异。

反汇编证据为 `/private/tmp/tca-contract-tooltip-function.txt` 与 `/private/tmp/tca-contract-contribution-tooltip.txt`；这是本机1.20.1.1静态路径证据，不代替原版画面或实际征收验收。本次没有为隐藏文字修改税兵义务，也没有新增对整个契约窗口的正式覆盖。

原版动态对照：`/private/tmp/tca-vanilla-contract-probe-runs/run-3khyhn7m`，CK3 1.20.1.1 macOS ARM64、1066、种子1538798675。主模组内容为空，只加载独立诊断 on_action、scripted GUI 和原版契约窗口的探针副本；未载入本模组玩法，未发送或接受改约。先通过原生 `is_landless_ruler` 检查刑部尚书，再实际打开其原版行政契约窗口；窗口人物上下文同时验证无地身份及非零税兵比例。日志读取 `Character.GetSubjectContract` 同源接口：税收95.0%、征召兵30.0%。唯一 PASS_WINDOW、COMPLETE、verification_exit=0、快照核对及同次日志检查通过。该结果证明原版无地官职也保留非零名义贡献比例，结合上述通用提示函数可解释其显示；未截图验证实际悬停文字，也未验证实际缴税金额与兵数。截图中36%的个体修正来源仍未重建。

首轮 `/private/tmp/tca-vanilla-contract-probe-runs/run-_bxjr918` 虽读到相同比例，但控制器进入下一阶段后被自身可见性隐藏，缺少 COMPLETE，并出现仅在GUI读取变量的未使用诊断，整体为 NOT VERIFIED。复测让控制器在两个阶段持续可见，并在结束条件中读取阶段变量；保持原版无地／税兵比例的断言条件不变，没有屏蔽日志错误。

### 拆分契约实现与验收（2026-10-18）

已删除旧共用契约、十个具名状态及其两条头衔得失同步回调，契约组登记两类新契约；原生改约成功入口识别任一类型，记录与换任恢复按本署类别读取对应待遇。两个契约的说明各自读取集中比例，仍共用现有国库结算和明细。不做旧存档迁移。本次没有增加新的GUI整文件覆盖。

原生财务第1至22项断言保留；因具名状态功能撤回，原第23至26项改为两类资格互斥、独立头衔待遇记录、各类第三档默认值和离任收入归零。新增第27项用不同档位验证两类契约不会串读。静态绑定新增拆分契约与无状态层回归，修改前失败、修改后全部134项工具测试通过；上游24项覆盖、29项追加回调、1项辅助扩展及3份文件覆盖检查通过，范围内格式检查通过。

单项 `/private/tmp/tca-split-budget-runs/run-l8r2y0sy` 为1用例、26断言通过。完整 `/private/tmp/tca-split-budget-full-runs/run-tiispldi` 为120用例、713断言通过；两次均CK3 1.20.1.1 macOS ARM64、独立1066观察者局、种子1538798675，仅本模组及CLI适配；观察者确认，summary结束，runner与verification退出码均为0，快照核对无问题，同次日志未检出模组相关引擎错误。完整运行冻结后只新增第27项测试及文档，玩法逻辑未变。完整源码SHA-256：`e04736719b843bb4fcb7a5558d78054d2cbc294f038dce363b22382b3d4fb874`。新契约说明的实际悬停、缩放与交互画面仍待验收；不以脚本断言替代这些验收。

新增独立性断言复测 `/private/tmp/tca-split-budget-runs/run-5hid1drc`：1项用例、27项断言全部通过，观察者确认、summary结束、runner与verification退出码均为0，快照核对及同次日志无检出的模组相关错误；版本、场景和种子同上。测试直接降低路司原生契约至最低档并记录，通判仍保持最高档25%，随后恢复路司最高档继续原有财务与任免断言。

官署经费当前通过[独立调整互动](office_budget_interactions.md)修改：横向五档、仅邻档、地方与上级各自冷却；原契约页保留只读经费，俸禄改约保持原版。旧的共用冷却及原生窗口试验不作为当前验收依据。

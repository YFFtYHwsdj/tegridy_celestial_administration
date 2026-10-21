# 儒家思潮统计

## 当前实现（2026-10-18）

为后续人物生成和思潮影响力机制提供本朝成年儒家人物的分布快照，同时保留人数占比、强度占比和并列排行。目前没有改变人物信仰、Rite、生成或皈依概率；随机选择尚未接入。

### 人群与强度

统计人群须同时满足：在世、成年、Faith属于 `confucianism_religion`、实际 `top_liege` 等于被统计君主，并有有效Rite。包含君主、各级封臣、无地官员及所属廷臣，以政治归属而非所在地判定。外国来访者、无归属流浪人物和当地人物池不会只因位于本朝而计入。囚禁地点本身不改变统计归属。

各Rite从实际人物动态建立，不硬编码经学／道学，也包含同宗教下其他Faith的人物。只显示有人信奉的Rite。人数占比＝该Rite人数／成年儒家总人数；强度占比＝该Rite强度／成年儒家总强度。零人时不做除法。百分比保存为0至100，显示一位小数，显示合计可能有舍入误差。

个人强度＝基础1＋儒学教育贡献＋最高普通头衔贡献＋世族贡献，采用加法：

- 儒学经验不足20／20／40／60／80／100，对应0／2／5／10／18／30，只取最高档，无特质为0。
- 普通头衔男爵／伯爵／公爵／王国／帝国／霸权，对应2／5／10／18／30／45，只取最高档，不按兼任数量累加，不区分文武及实地／无地。
- 实际持有世族头衔另加5，只计一次，家族其他成员不自动加分；其名义等级不计入普通头衔贡献。
- 冒险者不获得头衔及世族贡献，保留基础及教育贡献，但仍须满足上述领主链人口口径。

例如无官满经验儒者贡献31，无教育霸权君主46，两者兼具76，另持世族头衔81。这些是游戏设计权重，不是历史测量。各行及总计均保存人数、强度、教育、普通头衔和世族分项；基础贡献等于人数。按未舍入强度降序排列，并列采用1、1、3的竞赛排名。

### 共享缓存与周期

正式缓存保存在实际最高君主人物上，同朝所有调用者共享，与调试窗口无关。各天朝分别统计。君主死亡时统计行随所有者结束；继任者使用自己的缓存，首次读取时补建。缓存不复制旧君主的story引用。

`quarterly_playable_pulse`追加独立天朝君主的维护入口，每季度重建一次，无须打开窗口。原生季度是相对于角色年度脉冲的季度，不保证恰逢1／4／7／10月首日。首次机制读取会立即建立快照；主要头衔变化或距更新满90天时再读也会补算，以覆盖季度回调尚未执行或旧存档缺少缓存的情况。季度内的出生、成年、死亡、改信、教育和官职变化通常在下次更新反映，手动刷新可立即反映。

生产收集只访问最高君主、`every_vassal_or_below`以及每人的 `every_courtier_or_guest`、`every_prisoner`，再按人口口径过滤。临时 `tca_stats_seen` 变量列表对重叠访问去重，构建结束立即清除；不持久标记被统计人物。全世界扫描只作为测试参照。未对大型后期存档作耗时实测；不能据此承诺固定耗时。去重列表查找和逐Rite归组仍随人数增长。

调试决议与窗口只在debug且所属最高君主为天朝时可用。打开确保缓存有效，关闭只隐藏本人窗口；其他查看者和正式机制仍可使用数据。手动刷新强制重建本朝共享快照，暂停时也可使用。GUI直接读取当前最高君主的数据，显示距更新天数、两个占比、排行和贡献分项，不在显示表达式内扫描人口。旧版本已排队的每日事件只消费标记，不再续排。玩家更换最高君主且其尚无缓存时，重新打开窗口即可补建。

### 正式调用约定

`common/scripted_effects/tca_confucian_statistics_effects.txt`：

- `tca_ensure_confucian_statistics_effect`：任意在世本朝人物作用域，不受debug限制。成功返回 `scope:tca_stats_cache` 指向最高君主；不符合天朝资格时清除该输出。读取前应调用该入口，勿保存跨季度的行引用。
- `tca_refresh_confucian_statistics_effect`：当前人物作为缓存所有者，按其最高领主构建；正式机制仅在最高君主上调用，测试可使用独立人物作临时存储。
- `tca_quarterly_confucian_statistics_effect`：独立天朝君主作用域，季度回调的正式维护效果；自身检查资格。
- `tca_force_confucian_statistics_effect`：debug查看者作用域，手动强制刷新本朝共享快照。
- `tca_collect_confucian_statistics_member_effect`：候选人物作用域，调用者提供 `tca_stats_viewer` 缓存所有者及 `tca_stats_realm` 最高君主；内部检查人口口径，单独收集不去重。生产遍历通过visit入口去重。

缓存变量：`tca_stats_updated`记录日期，`tca_stats_realm`记录最高君主，`tca_stats_primary_title`绑定主要头衔，`tca_stats_total`人数，`tca_stats_rite_count`行数，`tca_stats_strength`及education／titles／families分别记录总强度及贡献。`tca_stats_rows`为原始行列表，`tca_stats_display_rows`为强度降序列表。行由 `tca_confucian_statistics_row` story承载，保存rite、count、percent、strength、strength_percent、rank及贡献分项。刷新会结束旧行，不能将行引用作为永久Rite标识。

后续随机可在ensure返回的缓存中使用各行 `tca_stats_strength` 或 `tca_stats_count` 作为权重，避免先四舍五入占比；同批次连续调用ensure共用快照。本轮只完成统计接口，不实际抽取Rite。

依据：本机原版1.20.1.1的 `common/on_action/_on_actions.info`（季度回调）、原版 `common/script_values/10_health_values.txt`（日期差）、`common/story_cycles/_story_cycles.info`（story生命周期）、`gui/window_government_administration.gui`（GetTopLiege）及 `gui/window_pam_christian_church.gui`（Rite数据）。本模组既有司法候选收集使用君主、封臣及各自廷臣的局部遍历。

## 本轮验证

原生测试仍直接维护在 `events/tests/tca_confucian_statistics_test_events.txt` 和 `events/tests/tca_confucian_strength_test_events.txt`。统计聚合由18增至28断言：新增局部与全世界参照的总量／逐Rite对照、首次共享读取、跨人物复用快照、手动刷新、关闭保留、89天继续复用及91天过期补算、主要头衔绑定失效及季度维护效果。保留成年、异教、死亡、两种占比差异、贡献、并列、重复归一化和零分母检查。测试通过原生trigger_event的on_action入口验证季度子回调及非独立人物的拒绝条件；人工派发不替代自然季度脉冲的时机验证。

首轮 `run-in3e4ljh`：种子1538798675，119 BEGIN／119 PASS／685 CHECK_PASS，零断言失败和未执行；同次error.log出现两条旧兼容标记 `tca_stats_refresh_pending` “使用但未设置”错误，verification_exit和runner_exit均为1，整体 **NOT VERIFIED**，不作为通过。已在兼容事件测试中显式准备旧标记；另补主要头衔绑定及季度子回调拒绝条件，当前计划119项／687断言，复测结果如下。最终复测 `run-vhmi3_hj`：CK3 1.20.1.1，种子1538798675，独立1066中国观察者局，仅主模组与CLI适配副本。入口 `python3 tools/run_game_tests.py --timeout 480 --seed 1538798675`。已核对同次terminal.json、result.txt、debug.log、error.log：119 BEGIN／119 PASS／687 CHECK_PASS，零FAIL／CHECK_FAIL／PRECONDITION_FAIL，统计聚合28断言与权重21断言全部通过；观察者确认，SUITE_ALL_PASSED，verification_exit与runner_exit均为0，源码副本无差异，未检出模组相关引擎错误。旧兼容标记错误已消除。

季度子回调共记录7次，测试源只人工派发符合资格的一次，其他6次来自接入的原生季度脉冲，确认自动入口有实际执行；未把人工派发冒作自然触发。尚未独立断言每次回调间隔或GUI跨季度重绘。126项Python工具测试、24项原版覆盖基线／28项追加回调分类检查、双语键名、BOM及本次文件空白检查通过，未刷新原版基线。

本轮目录位于 `/private/var/folders/f0/dh90nqcx6rsgf1558f91wmz40000gn/T/tca-game-tests/` 下，分别为失败的 `run-in3e4ljh` 和通过的 `run-vhmi3_hj`。完整结果只覆盖脚本、引擎加载及已执行回调，不替代界面、保存重载、玩家继承及动态Rite的人工验收。实际画面、按钮、保存重载、玩家继承与动态Rite由用户另行验收，本轮不操作界面。

## 历史验证记录（下列每日窗口行为已由季度共享缓存取代）

测试源：`events/tca_confucian_statistics_test_events.txt`，登记于 `events/tca_tests_events.txt`。18项断言覆盖人数／强度占比差异、分项汇总、少数学统高强度、并列排名及全人口扫描差值、16岁／15岁边界、佛道与死者排除、领主链隔离、两个Rite的2:1构成及百分比、重复生成排序、改信、死亡、零分母、开关与续接停止。另有 `events/tca_confucian_strength_test_events.txt` 的21项断言检查教育19／20、39／40、59／60、79／80、99／100边界，无教育的基础贡献、世族不按县级重复计分、普通头衔最高档、兼任去重、无地头衔、冒险者及清理。直接调用正式统计入口和script value，不在Python中重写业务规则。

静态检查：126项Python工具测试通过；上游覆盖检查通过，无新增原版同名覆盖；空白检查通过。

历史修复记录：`run-sjpspqxj` 新用例第4、5项断言失败，复现原生 `ordered_in_list` 默认只取一行的问题；显式遍历全部行后13项断言通过，`run-e4pvl4_l` 同次日志又发现上限超出列表大小的错误，现已改为维护准确行数。首次打开未设置可见变量及滚动策略的加载问题也已修正。

界面实际画面由用户自行检查，本轮不再操作游戏界面。界面人工验收应在专用天朝测试局打开决议，核对名称、图标、列表、百分比、滚动、刷新、关闭；暂停当天改变人物Rite后手动刷新，再推进一日核对自动刷新。还需分别验证保存重载、玩家继承及动态Rite。

### 2026-10-17 引擎回归结果

最终运行 `run-lwynk8q6`：CK3 1.20.1.1，独立1066中国观察者局，仅主模组和CLI适配副本。入口为 `python3 tools/run_game_tests.py --timeout 300`。本机沙箱内首次启动无法连接Steam，后改为可访问Steam及macOS图形会话的隔离启动。

已核对本次 `terminal.json`、`result.txt`、`debug.log`、`error.log`：观察者切换确认，118 BEGIN／118 PASS／651 CHECK_PASS，零FAIL／CHECK_FAIL／PRECONDITION_FAIL；新增用例1 PASS／13 CHECK_PASS。summary为 `SUITE_ALL_PASSED`，verification_exit和runner_exit均为0，源码快照无差异，未检出模组相关引擎错误。统计模块错误引用为0，证实此前第4、5项失败已经转为通过，排序上限及首次可见性检查的脚本错误也已消除。

该结果覆盖引擎加载和脚本断言，不代表界面实际渲染或点击通过。用户已明确自行检查游戏实际画面；本轮未完成窗口显示、按钮点击、玩家状态下跨日自动更新、保存重载、玩家继承及动态Rite的人工验收。未运行可选的严格首位继任模式，不改变该既有事项的验证状态。

本次日志目录：`/private/var/folders/f0/dh90nqcx6rsgf1558f91wmz40000gn/T/tca-game-tests/run-lwynk8q6/`。此前主动终止的失败运行保留在同级目录，不能作为完整通过证据。

## 机制用途与后续边界

人数占比保留为基础分布，强度占比按本页已确定公式独立计算。后续生成入口可读取分布按权重选择儒家Rite；本轮已实现贡献分项、归一化和并列排行，但尚未接入生成。

### 调试入口限制验证

后续调整：查看资格增加 `debug_only = yes`，决议有效性及窗口显示同样受限；中英名称同步改为调试入口。此前118项／651断言结果属于加门槛前版本，不代表已完成本次非debug隐藏的实机验收。本次执行工具测试、覆盖及空白检查；实际界面继续由用户检查。

### 加法强度实现与验收

2026-10-17：采用本页“当前强度公式”，新增 `tca_confucian_strength_values.txt`。在现有收集器中同步汇总各Rite及全政权的总强度、教育、头衔、世族贡献；基础贡献等于人数。窗口按强度降序，同时显示两种占比和各项来源，人数占比的定义不变。只做统计，不接入生成、不修改人物信仰或任命。

第一次运行 `run-eefc_m6n` 发现本机不能动态创建县级头衔，对应权重夹具第13项失败；现已改用独立静态无地县级测试头衔，保留断言。其余教育、较高头衔及冒险者断言通过不替代完整复测。随后 `run-1s4dnw_0` 新增两组38项断言通过，统计模块无相关引擎错误，但既有通判生命周期失败15项，并伴随拘押观察用例错误，整组NOT VERIFIED。已补充显式销毁新增权重夹具人物，避免高教育及曾持高阶头衔者留在候选池；该干扰解释尚未确证。既有种子1538798675及原失败种子4208744368的完整复测现均通过，见下。实际画面仍由用户验收。

固定种子1538798675回归 `run-ys4k38x_`：119 BEGIN／119 PASS／677 CHECK_PASS，0 FAIL／CHECK_FAIL／PRECONDITION_FAIL；新增聚合18断言、权重21断言均通过。观察者、summary、terminal、result及源码快照均核对通过，verification_exit和runner_exit为0，未检出模组相关引擎错误。原失败种子4208744368的追加复测也已通过，见下。男爵档权重已经静态审阅，本轮未准备独立男爵夹具；县至霸权、无地官职、世族与冒险者有引擎断言。英文排名前缀随后从符号改为文字Rank，属于本地化显示修订，不把该文本改动称为已实机显示通过。

原失败种子4208744368复测 `run-b0irpxaf`：119 BEGIN／119 PASS／677 CHECK_PASS，零失败及未执行。已核对同次 `terminal.json`、`result.txt`、`debug.log`、`error.log`：观察者确认，summary为SUITE_ALL_PASSED，verification_exit和runner_exit均为0，源码快照无差异；统计模块错误引用为0，未检出模组相关引擎错误。清理前该种子通判生命周期失败，清理后同种子通过；这支持夹具隔离修正，但尚未单独证明此前失败的唯一根因，仍保留原失败日志与记录。

两个最终运行目录均在 `/private/var/folders/f0/dh90nqcx6rsgf1558f91wmz40000gn/T/tca-game-tests/` 下，分别为 `run-ys4k38x_` 和 `run-b0irpxaf`。126项工具测试、上游覆盖检查及空白检查通过；新增本地化保留UTF-8 BOM。权重统计与脚本行为已验证，实际画面、交互、玩家每日续接、保存重载及动态Rite仍待用户验收；此次不宣称已接入生成机制或修复严格首位继任问题。

### 2026-10-18 提交前复核

复核人数／强度分母、加法贡献、并列排名、局部遍历去重、共享缓存、季度门槛、debug入口与夹具清理，未发现需调整的玩法逻辑。当前相关代码与 `run-vhmi3_hj` 已通过的快照逐文件一致，仅修正GUI关闭行为的一处旧注释，非注释内容一致。再次运行126项工具测试、上游覆盖检查、BOM／双语键名及暂存区空白检查；此次不重复运行已验证且逻辑未变的引擎全组。其他研究文件的并行改动不属于本次提交。界面、保存重载、玩家继承及动态Rite仍待人工验收。

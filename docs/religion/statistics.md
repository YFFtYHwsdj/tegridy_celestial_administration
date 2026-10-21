# 儒家思潮统计

## 当前实现

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

后续随机可在ensure返回的缓存中使用各行 `tca_stats_strength` 或 `tca_stats_count` 作为权重，避免先四舍五入占比；同批次连续调用ensure共用快照。当前只提供统计接口，不实际抽取Rite。

依据：本机原版1.20.1.1的 `common/on_action/_on_actions.info`（季度回调）、原版 `common/script_values/10_health_values.txt`（日期差）、`common/story_cycles/_story_cycles.info`（story生命周期）、`gui/window_government_administration.gui`（GetTopLiege）及 `gui/window_pam_christian_church.gui`（Rite数据）。本模组既有司法候选收集使用君主、封臣及各自廷臣的局部遍历。

## 验证与待接入

原生源为 `events/tests/tca_confucian_statistics_test_events.txt` 和 `events/tests/tca_confucian_strength_test_events.txt`，覆盖局部／全世界参照、Rite聚合、加法贡献、零分母、并列排序、共享读取、89／91日缓存边界、主要头衔变化和季度入口。季度自然回调曾在日志中实际出现，未独立证明每次间隔及跨季度 GUI 重绘。自然回调的旧观察只能作为线索，周期与重绘仍需在目标版本复核。

当前仅提供统计与缓存，尚未接入人物生成或随机 Rite 选择。debug入口的实际隐藏、不同角色共享窗口、保存重载、继任后缓存重建、动态 Rite 及大型后期存档耗时仍待验收。不要保存跨季度 story 行引用，也不要以直接维护断言替代自然季度、继任及界面路径。

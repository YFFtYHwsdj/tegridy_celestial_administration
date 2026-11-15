# 边疆战争的AI依据与待验证问题

本页记录原版脚本能确认的接口边界，供[玩法设计](design.md)与[开发计划](plan.md)使用。原版依据来自本机文件，原型实现与实测范围另见[验证页](verification.md)；引擎内部算法不可由脚本说明完整还原。

## 宣战评分与军力判断分开

原版 `game/common/casus_belli_types/_casus_belli.info` 定义：

- `ai_score`：在头衔等硬编码评分上相加。
- `ai_score_mult`：乘到头衔评分上。
- 两者使用标准战争作用域，可用于自定义寇边战争的吸引力调整，但不是“替换整套军力估计”的接口。

`game/common/defines/ai/00_ai.txt` 同时存在独立统治者和封臣寻找战争对象的军力门槛，以及目标处于和平、战争时的宣战军力比例限制。因此不能假定提高战争评分就能突破对象筛选或宣战门槛；具体先后顺序和计算仍需引擎确认。

原版已有性格对战争行为的影响：`AI_BASE_WAR_CHANCE` 的说明关联 energy，`AI_BOLDNESS_ADJUSTMENT_FACTOR_ADMIN_REALM_POWER` 明确说明 boldness 会改变对行政国家官员作战效率的估计。相关特质还设置 `ai_war_chance`。这说明人物差异不必从零重做，不代表所有局势后果会自动进入原生判断。

## 会不会考虑全国军力

不能把“国家内全部人物的兵力总和”“皇帝可调用的力量”和“某场地方战争实际会投入的力量”视为同一数值。

原版行政国家军力估计已有官员效率因素，但仅凭可见定义，无法确认每类天朝头衔兵士的计入范围、重复扣除方式，以及地方主官自主宣战时采用哪一层国家力量。不能据此断言只算个人，也不能断言已自动完整计算全国。

`_casus_belli.info` 另有 `ai_overlord_defensive_power_impact`，返回0至1，用于估计攻击未获即时保护的 subject 时其 overlord 后续介入的力量。说明给出的中间值是 subject 与 overlord 的加权估计，并非向现有防守力量简单追加同一比例的宗主兵力。

`game/common/script_values/00_war_values.txt` 定义了同名全局兜底值，因此不能因各宣战理由未单独配置就认为没有原生实现。基础值为0.75，并按当前根作用域的主头衔等级调整；其实际作用域对应须在引擎中核对，多级上级及邻近援军的精确计算仍待验证。

## 原生边境战争与上级加入

原版已有允许直接攻击封臣、上级有条件后续介入的边境战争机制。不能单凭 `_casus_belli.info` 中 `target_top_liege_if_outside_realm` 的通用说明，断言普通跨国战争只能以最高领主为防守者。

`game/common/law_groups/02_admininistrative_law_groups.txt` 的 `border_wars_laws` 不设置专属政体旗标要求；`game/common/laws/02_admininistrative_laws.txt` 的两档法律分别设置 `can_vassals_be_attacked = no/yes`。

允许攻击封臣的一档要求独立、有地、公爵级以上，且满足霸权级、领国规模达到阈值、家族处于对抗团结阶段或正在防御内战等条件之一；开局选择也依据这些条件。规模阈值由 `game/common/script_values/10_tgp_dynastic_cycle_values.txt` 的 `border_war_sized_realm_value` 引用 `monumental_realm_size`，其当前值在 `game/common/script_values/00_basic_values.txt` 中为160。小国受到最高领主直接保护是另一档，但对抗家族或防御内战也会改变资格。因此这不是所有天朝国家无条件启用的政体特性，辽、夏也不能只凭政体名称判断。

1066年原版历史中，西夏 `history/titles/k_xia.txt` 将最高统治者设为 `meritocratic_government`；辽在 `history/titles/00_other_titles.txt` 的最高头衔历史使用 `steppe_admin_government`，部分下属头衔在 `history/titles/k_khitan.txt` 使用 `meritocratic_government`。这些政体差异本身不排除上述法律。两国实际开局法律须在目标版本测试局读取，不能只凭规模印象断言。

`game/common/character_interactions/00_alliance.txt` 的 `join_vassal_war_interaction` 明确提供上级加入封臣防御战争的路径：

- 可显示给实际上级链中的统治者，要求相关上级链具有允许攻击封臣的法律；也另行支持符合保证条款的朝贡关系。
- 只允许相应防御战争，排除己方辖下进攻者；直属封臣还核对目标头衔与本国实际辖属。
- 上级当前不得处于战争中，且战争天数须超过 `border_war_grace_period_days`；原版该值在 `game/common/script_values/tgp_values.txt` 中为1095天。
- 接受时实际使用 `add_defender = scope:actor`，证明已有脚本加入路径；不等于已经验证自定义延迟、多级参与及头衔兵士行为。

原版AI基础意愿为100，单个公国级及以下目标、没有王国级以上目标、赤字、自己正在战争中或封臣兵力足以应敌等情况会降低意愿。该互动注释明确指出，同一意愿值也用于宣战界面判断上级是否会加入；这说明原版已有介入预测接点，但不能直接断言它与硬编码军力筛选完全等价。

这为复用原生参战效果提供依据，但不直接采用其整套法律前置和等待规则。具体响应参数由玩法设计维护，必须防止原生加入与自定义加入重复执行；不全局缩短原生等待期影响无关战争。专属寇边能否绕过原保护，由P0独立验证；原版其他战争的保护规则不因此自动改变。

## 配套影响与说明文本差异

`can_vassals_be_attacked` 也被原版民众、农民及升级农民派系读取：当派系目标满足此条件时，不满增长额外加2。它不是只控制对外宣战的独立开关；给人物附加等效修正也可能触发该影响。`game/common/on_action/war_on_actions.txt` 还据此向未自动参战的最高领主发送封臣遭外敌攻击通知。

原版简中法律说明提到首年不能加入、持续超过5年更可能加入，但当前加入互动实际检查战争超过1095天，所查 `ai_will_do` 也没有5年增益。当前行为分析以脚本为依据，不能照抄该段本地化作为准确规则。

加入互动的AI基础意愿100，相关减项各为100；对单个公国及以下目标，以及没有王国级以上目标的战争均有减项。因此“王国级、多目标更可能介入”是概括，不能写成低级目标仍有固定随机援助概率。其当前可见评分没有专门的性格加项，不能因其他战争系统考虑性格就推定这个互动也如此。

加入互动还包含常规参战副作用：标记已召入和盟友记录、适用的人质风险提示、宗教战争勋号虔诚收益、怯懦压力及同族氏族团结变化。它们属于互动效果，不是法律直接提供的资源修正。法律自身没有税收、军费或兵力加成。

## 不切换法律时实现局势内有条件防御

设计要求见[防御动员](design.md#防御动员与原版战争边界)。原版法律以 `modifier = { can_vassals_be_attacked = yes/no }` 控制，且该键在 `game/common/modifier_definition_formats/00_definitions.txt` 中登记，因而存在通过独立修正提供相同能力的候选路径，无须先假定必须覆盖法律。

但原版实际用例目前仅查到法律，尚不能保证普通人物修正承载时的结果、与“无条件保护”叠加后的取值、引擎读取哪一层人物，以及玩家界面和自然AI是否同步生效。尤其该键没有宣战双方、目标地区或宣战理由参数，不能据此宣称它能只影响局势区域内的战争；若加在最高领主上，可能影响其整个国家的封臣保护。

即使独立修正能开放地方防御战争，原生 `join_vassal_war_interaction` 仍明确检查“有条件加入”法律，因此修正本身不会自动解锁原生后续加入互动。可继续复用原生加入效果设计局势专属入口，但需要处理原生AI介入预测与实际候选者的一致性。

独立修正是备选调查方向，当前主线已选择专属互动脚本开战，不优先给全国添加该状态。若主线失败，须区分仅局势相关战争和整个国家的效果，再讨论是否接受备选方案及派系等附带影响；不能静默扩大范围。

## 当前入口选择与验证顺序

当前debug原型已通过原生互动投递验证了受保护地方领主的脚本战争、单上级延迟加入及保存重载续接，见[验证页](verification.md)。这支持专属互动方向，不证明普通宣战界面或自然AI能够绕过原保护，也不证明完整军力估计已经可用。已有头衔兵士在地方和单上级军队中的实际集结，另由原生现场存档引用链核验，未见需要自建军队调用机制的问题。

正式方向改为“发动边境战争”互动、原生选择界面与自定义CB，首版由局势限制范围；旧自有窗口不再是交付依赖。互动仍须自行处理资格与战略评分，不自动调用完整自然宣战评估。

`game/common/character_interactions/_character_interactions.info` 提供 `ai_targets`、`ai_frequency`、`ai_frequency_by_tier` 和 `ai_will_do`。其说明将`ai_will_do`定义为选出候选后检查的0—100发送概率；头衔互动另会逐个评估目标头衔，存在选项时选取最高评分组合。不能由此推断普通人物收件人必定取全局最高分。这为互动自身驱动AI提供依据，但正式头衔与战争类型选择能否进入同一评估路径，仍须验证。

`ai_will_do`在接口说明中是选定目标后执行的0至100意愿／概率，并会被限制在此范围；不能把它理解为任意大的CB分数，也不能只改一个值就假定有完整战略规划。候选目标和选项的优选说明不代表可以无代价穷举全国角色与头衔，需要限制候选范围和检查频率。

原版 `game/gui/interaction_declare_war.gui` 使用专用宣战数据上下文，`game/common/character_interactions/00_war.txt` 使用 `special_interaction = declare_war_interaction`。因此可以参考其外观与信息组织，但不能仅复制GUI就断言可用于新的脚本互动，也不能默认能复用原版军力、费用及目标预览。

具体探针、阶段范围和验收统一维护在[开发计划](plan.md)，本页不再复制另一份执行顺序。人物、目标、费用和援军预期须使用同一正式规则来源；基本评分可单独验证，合理长期战争行为还需自然AI观察。

## 最小验证范围

以下问题仍需超出当前最小战争原型的验证，不能因互动投递或单上级支援成立就全部视为通过：

- 玩家与互动AI能否按同一资格对预期地方主官宣战，实际主防守者是谁。
- 增减中央或其他官员兵力时，地方宣战与被选为目标的行为如何变化。
- 互动评分能否正确选择战争类型与目标，能复用哪些原生军力接口，是否另受引擎开战限制。
- 上级、邻近主官延迟参战及头衔兵士动员是否有效，是否与已有军力重复计算。
- 潜在援军及等待时间变化后，AI是否仍能作出可接受的局部进攻选择。

原版依据为上述相对游戏目录文件；不将本机绝对路径或本次检索记录作为长期公共证据。后续游戏版本变化须重查接口，实际行为以专用测试局的原生路径验证为准。

## 局势参与组与阶段修正

原版依据为`game/common/situation/situations/_situations.info`：同一人物在同一子区域只进入第一个满足条件的参与组，分组顺序有业务意义。正式三组职责以[玩法设计](design.md#参与资格与边疆身份)为准。境内组对普通领主复用`any_sub_realm_county`检查本人领地，包含封臣土地，不向上扩大为全国；提刑、通判保留绑定治所分支。相关组只检查参与独立最高领主的直属无地官署，不再重复纳入最高领主本人。

阶段`modifier_sets`可按组配置`character_modifier`与`county_modifier`，前者作用于参与人物，后者的文档定义为统治者参与者的全部直辖伯爵领（domain counties），不是含封臣的整个领地（realm）。最高领主的土地修正不会由该入口自动覆盖封臣土地；封臣须通过自己的参与组承接相应效果。原版`the_great_steppe.txt`专设`settled_rulers`组，为定居统治者的伯爵领施加肥力修正，可作为两类效果并用的实际用例。

参与条件中的`require_domain_in_sub_region`与`require_realm_in_sub_region`只分别要求区内存在直辖或领地，不能单凭资格条件推断效果范围。格式说明没有承诺地理裁剪；本机1.20.1.2独立探针已分别验证指定组和`all`的`county_modifier`：区内直辖样本生效，同一参与者的区外直辖、区内封臣及外国样本不变，结束后恢复。当前证据支持原生按区域裁剪直辖效果，具体测量、失败边界及复现命令见[作用范围探针](verification.md#county_modifier作用范围探针)。原生迁都及测试组往返切换已补验：首府在江南时，北疆直辖仍生效、江南直辖不受影响；旧组效果最终撤除。名单与县读数存在异步更新，不能承诺立即同步，探针有界等待后才判断。仅变更私有资格flag未触发退出；显式`remove_manual_participant`后最终清理通过。这项范围探针不覆盖正式三组的全部身份变化、改隶、无地官署或全部经济军事modifier键；正式阶段的另行验收见[验证页](verification.md#正式三阶段修正)，不代表完整P2验收。

正式三阶段在Situation自身的`modifier_sets`中按三个参与组分别写入，境内与相关组的县修正相同，边疆县值已经包含区域基准，不再叠加`all`；只有边疆组有人物修正，相关组不承担地域裁剪职责。土地使用原生`tax_mult`、`garrison_size`与`levy_size`，人物使用`men_at_arms_recruitment_cost`与`defender_advantage`。数值只在[阶段修正设计](design.md#阶段负担与动员收益)维护。原版兵士窗口的`GetCostString`与`GetTitleRegimentCostString`可分别记录人物、头衔军报价，不能以报价替代实际扣款验收。`GetCommanderAdvantageDesc`只展示通用指挥优势，不能证明条件性`defender_advantage`已经传入战斗；防守方实际战斗、统治者与指挥官传递关系仍待验证。

原版手动候选退出依据：`game/common/scripted_effects/10_dlc_tgp_scripted_effects.txt`的`destroy_held_ministry_titles_effect`在撤官后明确调用`remove_manual_participant`，`game/common/on_action/title_on_actions.txt`亦有按身份失效撤销手动候选的实际用例。探针沿用配对入口，未手工指定改组结果、切换阶段催生退出或直接删除县效果。

正式方案不另设双边阶段或点数，所有催化作用于同一整体阶段。有地领主交给原生`auto_add_rulers`自动搜集，不再遍历相关国家的全层级封臣或为其登记手动候选。原生无地自动候选以domicile为入口，遗漏的无地官署参照原版`10_dlc_tgp_scripted_effects.txt`做手动补入：中央部职读取相关最高领主的内阁，提刑、通判分别读取既有`tca_judicial_circuits`与`tca_tongpan_counties`注册表；最终仍经过同一正式资格入口。转国快照只预存相关最高领主，战争双方另在宣战时记录，不为全体参与者反复写入身份变量。

`add_manual_participant`登记的是持续考虑的候选，不强制人物进入任何组；没有匹配组时不属于实际参与者。实际分组与修正更新交给原生机制，`remove_manual_participant`用于撤销候选资格，不能把未显式撤销候选直接当作实际参与或修正残留。


战争回调的root可能是短命Casus Belli。二级回调先转到`scope:attacker`／`scope:defender`的持久人物作用域承接，不把CB作为延迟事件载体。同一脚本里立即开战并结束可能在二级回调执行前销毁CB，此时人物作用域转移本身也会报错，普通root存在检查不能修复；测试夹具须真实跨日结束战争。此为已知原生时序限制，尚未证明所有瞬时脚本战争兼容。胜利原生回调互斥；白和平不注册计分子回调。土地变化延后一日合并，避免征服后分封把同一事实重复记分；快照同时记录代表头衔与最高领主人物，容忍普通继位和同一君主更换主头衔。

### 交易成功接入

原版`00_gift.txt`的`gift_interaction.on_accept`直接执行`pay_short_term_gold`，付款者是`scope:puppet_or_actor`，并非始终是操纵者`scope:actor`。本模块在实际付款后调用`tca_frontier_gift_succeeded_effect`，双方本人须为参与的独立君主；仅有缓和去向时计分。主头衔上的`tca_frontier_gift_partners`列表保存对方国家主头衔，原生期限三年、双向检查，普通继位沿用；局势结束按自身登记清理。当前不提供随任意主头衔更换或国家分裂迁移冷却的完整国家续接系统。

原版`00_prison_interactions.txt`的`ransom_interaction`、`pay_ransom_interaction`和`ransom_me_interaction`均在接受后调用`00_prison_effects.txt`的`ransom_interaction_effect`。共用效果读取`prisoner`、`payer`、`imprisoner`，按选项支付金币、牵制、影响力或牧群，然后调用`release_from_prison`。北疆在效果开头重置并保存本次资格，实际释放后计分；资格要求付款者和关押者本人参与、仍由该关押者羁押，以及囚犯当前或本次羁押快照证明重要异国身份。通用释放可以清理快照，但不会抹掉本次交易已经核验的临时值；批量赎回每个囚犯重新初始化，避免串用。

原版`release_from_prison_interaction.on_accept`先处理实际释放，再在“无要求”分支检查13个选项均为`no`：`demand_conversion`、`renounce_claims`、`banish`、`gain_hook`、`take_vows`、`become_executioner`、`recruit`、`disfigure`、`blind`、`castrate`、`demand_admin`、`change_prison`、`make_puppet`。北疆在仍被羁押时保存双方资格和主权身份，仅在此分支且受影响者实际获释时触发`tca_frontier_release_succeeded_effect`。不把越狱、普通脚本释放或其他附条件释放当作无条件释放。

上述三个对象均无可追加的专用成功回调，互动及scripted effect也不能像on_action一样跨文件追加执行块。因此仅覆盖这三个必要对象，原版全部可执行内容保留，加入准备／成功钩子；不覆盖整份原版文件，不借宗教等无关辅助效果承接。基线、理由和冲突范围登记于`tools/upstream_overrides.json`；修改同名对象的其他模组须合并。原版`on_release_from_prison`仍仅负责清理，不能提供交易原因。

### 当前催化判定入口

- `tca_frontier_title_in_scope_trigger`在头衔作用域判断：先核验地图省份存在，排除无地官署和销毁中的动态县级头衔；伯爵领的`title_province`位于`tca_frontier_region`，或其`any_de_jure_county`中至少一个县位于该范围。`tca_frontier_war_in_scope_trigger`只检查战争`target_titles`列表，不因任一参战国有北疆土地就把其南方战争纳入。
- 宣战由`on_war_started`承接：局势存在、战争存在、主攻守双方`top_liege`不同、目标合格且该战争尚无`tca_frontier_declaration_counted`，才计一次。胜利使用互斥的`on_war_won_attacker`／`on_war_won_defender`，以目标及战前国家快照防止完全吞并后误当内战；白和平没有计分回调。
- `tca_frontier_person_action_valid_trigger = { ACTOR = ... }`在受影响人物作用域检查：本人先通过`tca_frontier_important_person_trigger`，发出者本人通过`tca_frontier_is_participant_trigger`，双方`top_liege`不同。重要性入口要求本人先是参与者，再满足独立君主、边疆组资格、或`this = top_liege.primary_heir`之一；普通境内官员及相关部职不自动重要。
- 囚禁使用`on_imprison`的囚犯root与`scope:imprisoner`，通过上述条件后记录本次羁押的国家、关押国与重要身份。死亡使用`on_death`的受害者与`scope:killer`；责任人必须仍有参与资格，受害者符合当前条件或有效羁押记录中的异国重要身份。处决与杀害由次日实际死因互斥分类，不从人物关系猜幕后凶手。
- 释放与赎回共用`tca_frontier_captive_action_valid_trigger = { ACTOR = ... }`：受影响者符合当前异国重要人物条件，或羁押快照仍标记重要、被俘前国家不同且记录的关押国等于当前关押者国家。实际羁押关系由各交易prepare入口另行核验；原始接入时序见上节。

### 自动生命周期入口

[生命周期条件](../../common/scripted_triggers/tca_frontier_lifecycle_triggers.txt)和[维护效果](../../common/scripted_effects/tca_frontier_lifecycle_effects.txt)只为1066新局初始化，不承担旧存档迁移。`tca_frontier_initialized`、`tca_frontier_resting`与`tca_frontier_unified_title`为全局变量，分别表示已经初始化、统一后休止、原国家代表头衔，不依附已结束的Situation。启动共用`tca_frontier_situation_start_effect`，只在真正创建新对象时清除休止记录；决议改用`tca_frontier_enter_rest_effect`先记录统一国家再清理对象。

`on_game_start_after_lobby`追加独立二级回调，延后两日首次检查；相关`on_title_gain`、`on_vassal_change`与`on_title_destroyed`合并次日检查，`yearly_global_pulse`为已初始化但无局势的状态补漏。原版明确`on_vassal_change`也用于独立，头衔销毁上下文为`scope:landed_title`。排队使用原生延后on_action，以固定`h_china`头衔对象承载，不依赖在位皇帝存活，也不改变该头衔；三日全局锁合并重复请求，worker先清锁再重查当前世界。

自动授权入口`tca_frontier_automatic_lifecycle_allowed_trigger`在主模组为`yes`；CLI适配以`zz_`文件名确保其定义晚于主文件加载，只覆盖本模组自有trigger，默认`no`，不新增原版覆盖。`configure_selection`根据单个WORLD在封存前重写适配入口，仅`tca_frontier_lifecycle_test`、`tca_frontier_lifecycle_unified_test`、`tca_frontier_lifecycle_annual_test`和`tca_frontier_lifecycle_succession_test`为`yes`。混合总计划、普通共享局和其余独立探针均为`no`，克隆时重新计算，不继承父任务授权；读档沿用同一冻结适配，不靠运行中flag或开局回调顺序切换。


年度补漏WORLD在加载前另将`tca_frontier_change_notifications_allowed_trigger`设为`no`，仅屏蔽头衔、改隶和销毁三类变动通知，保留正式开局与`yearly_global_pulse`。该入口在正式游戏为`yes`，不改变重启资格或年度时间；其余自动WORLD重新开启通知，克隆为普通局或手动探针时两项授权均关闭。测试事件不临时改生产锁、不直接调用年度on_action或维护worker，以年底仍休止、真实跨年后才重启证明年度补漏路径。


适配文件须保持`zz_tca_cli_frontier_lifecycle_triggers.txt`名称：引擎的实际数据库冲突日志曾显示不带`zz_`时主文件反而覆盖适配，单看启用模组顺序和冻结文件内容不能证明关闭已生效。独立关闭用例同时读取实际解析的两个入口，并等待开局窗口结束，确认没有Situation、初始化、休止或排队标记；旧手动探针先创建对象，不能单独证明默认关闭。

## 有限战争与追讨的技术核查

以下是本机原版源码核查结果，不是新方案的引擎验收。玩法共识以[设计](design.md#持续控制目标与胜利)和[追讨](design.md#战后追讨)为准。

### 原生互动选择

`game/common/character_interactions/pam_interactions.txt`的`ecclesiastic_incite_claim_war_interaction`使用`target_type = title`、`target_filter = realm_titles`、`target_source = recipient`，以`populate_recipient_list`生成第二人物候选，并以`can_be_picked_title`过滤目标。`send_option`承载参战、资助等选择；`game/common/scripted_effects/pam_effects.txt`的`pam_incite_claim_war_effect`最终调用`start_war`和`claim_cb`。这是原生互动选择后脚本开战的依据，不是普通宣战窗口绕过封臣保护的依据；该原版互动明确要求收件人独立，资格也不能照搬到天朝。

### 战争分数

`game/common/casus_belli_types/_casus_belli.info`定义`full_occupation_by_attacker_gives_victory`、`max_attacker_score_from_occupation`、`max_attacker_score_from_battles`、`imprisonment_by_attacker_give_war_score`、`defender_capital_gives_war_score`及目标持续分数、延迟和控制比例字段。可配置取消完全占领自动满分、俘虏分数并限制战斗与占领来源；分数合计、全部目标失守、俘虏首领及持续控制后的真实读数须在独立局核验。字段存在不证明组合效果，也不证明实际议和路径。

### 议和AI与低于满分的结算

`game/common/character_interactions/00_war.txt`的`end_war_attacker_victory_interaction`分别定义`is_available`、`ai_will_do`、`ai_accept`与`auto_accept`。提议门槛有100、90、80、70分等分支，涉及和平缔造者、游牧宗族传承、首级威慑及征服者；不能把所有低于满分的分支都称作强制接受。接受基础为-99，再计分数和加成；自动接受另有满分、向进攻者投降及征服者军力分支。仅降低战争分数上限不能证明必须控制目标后才能结算，也不能靠调整`ai_accept`覆盖`auto_accept`。

白和平的`end_war_attacker_white_peace_interaction`也分别维护提议与接受逻辑；接受值考虑战争分数、持续时间、债务、其他战争及性格等。后续须分别核对地方AI主动投降、接受胜利要求、提议和接受白和平，保留玩家自愿投降，不以全面禁议和代替援军判断。

目前已查CB说明未提供独立的议和AI修正字段；上述互动内也未发现预留给本模组援军承诺的追加入口。精确接入可能需要覆盖必要的顶层互动对象，但尚未确认不存在免覆盖替代，故当前不新增覆盖、不改评分。若最终必须覆盖，保留原版逻辑，仅对指定CB及正确一方添加条件，并登记上游清单与基线；不得同路径覆盖整份`00_war.txt`。

### 追讨结算与停战

`game/common/casus_belli_types/00_claim.txt`在胜利、白和平及失败事务分别调用`add_truce_attacker_victory_effect`、`add_truce_white_peace_effect`、`add_truce_attacker_defeat_effect`。因此不能仅看CB的`truce_days`推断整场战争全部停战关系，更不能预先假定脚本开战不会产生违约成本。新CB、实际主战双方及已加入上级的停战结果须直接测量。

原生`on_war_won_attacker`已有成功事务入口，但战争／CB作用域短命；本模块已知二级回调和瞬时结束的时序限制仍适用。承诺名单须以持久载体保存，不能将待追讨任务挂在销毁中的战争上。此轮未找到主动替换主防守者的通用脚本用例，继承字段不能作为移交接口证据；新方案无需依赖该接口。

追讨必须另查原进攻者已交地、失去全部土地、已有战争、盟友、死亡及改隶。原进攻者与现持有人不一致时，既定的反向攻守身份与目标有效性可能冲突，属于设计待决，不可由测试偷偷替换防守者。

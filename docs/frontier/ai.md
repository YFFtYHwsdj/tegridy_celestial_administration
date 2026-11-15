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

自定义寇边现采用专属人物互动加自有宣战界面的设计方向，旨在独立判断地方目标并灵活配置AI评分。早先优先普通宣战窗口的设想由此替代；原生军力与参战接口仍可作为可复用依据，不能假定互动会自动调用完整的自然宣战评估。

`game/common/character_interactions/_character_interactions.info` 提供 `ai_targets`、`ai_frequency`、`ai_frequency_by_tier` 和 `ai_will_do`。其说明将`ai_will_do`定义为选出候选后检查的0—100发送概率；头衔互动另会逐个评估目标头衔，存在选项时选取最高评分组合。不能由此推断普通人物收件人必定取全局最高分。这为互动自身驱动AI提供依据，但自有界面中的全部选择能否进入同一评估路径，仍须验证。

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

原版依据为`game/common/situation/situations/_situations.info`：同一人物在同一子区域只进入第一个满足条件的参与组，分组顺序有业务意义。正式三组职责以[玩法设计](design.md#参与资格与边疆身份)为准。

阶段`modifier_sets`可按组配置`character_modifier`与`county_modifier`，前者作用于参与人物，后者的文档定义为统治者参与者的全部直辖伯爵领（domain counties），不是含封臣的整个领地（realm）。最高领主的土地修正不会由该入口自动覆盖封臣土地；封臣须通过自己的参与组承接相应效果。原版`the_great_steppe.txt`专设`settled_rulers`组，为定居统治者的伯爵领施加肥力修正，可作为两类效果并用的实际用例。

参与条件中的`require_domain_in_sub_region`与`require_realm_in_sub_region`只分别要求区内存在直辖或领地，不能据此认定county_modifier会裁剪至区内。格式说明没有承诺地理裁剪；兼有区内外直辖时的实际范围仍待引擎验证。最小探针须区分参与者的区内直辖、区外直辖及其封臣土地，并核对阶段变化、改隶和退出后的清理。未验证前不能保证给普通区域或边疆组配置土地效果不会影响区外直辖。

正式方案不另设双边阶段或点数，所有催化作用于同一整体阶段。原生无地自动候选以domicile为入口，无domicile中央部职参照原版`10_dlc_tgp_scripted_effects.txt`的`add_manual_participant`做手动补入。首次名单从北疆实际国家向下收集并去重，后续原生刷新仍重查身份。


战争回调的root可能是短命Casus Belli。二级回调先转到`scope:attacker`／`scope:defender`的持久人物作用域承接，不把CB作为延迟事件载体。同一脚本里立即开战并结束可能在二级回调执行前销毁CB，此时人物作用域转移本身也会报错，普通root存在检查不能修复；测试夹具须真实跨日结束战争。此为已知原生时序限制，尚未证明所有瞬时脚本战争兼容。胜利原生回调互斥；白和平不注册计分子回调。土地变化延后一日合并，避免征服后分封把同一事实重复记分；快照同时记录代表头衔与最高领主人物，容忍普通继位和同一君主更换主头衔。

### 交易成功接入

原版`00_gift.txt`的`gift_interaction.on_accept`直接执行`pay_short_term_gold`，付款者是`scope:puppet_or_actor`，并非始终是操纵者`scope:actor`。本模块在实际付款后调用`tca_frontier_gift_succeeded_effect`，双方本人须为参与的独立君主；仅有缓和去向时计分。主头衔上的`tca_frontier_gift_partners`列表保存对方国家主头衔，原生期限三年、双向检查，普通继位沿用；局势结束按自身登记清理。当前不提供随任意主头衔更换或国家分裂迁移冷却的完整国家续接系统。

原版`00_prison_interactions.txt`的`ransom_interaction`、`pay_ransom_interaction`和`ransom_me_interaction`均在接受后调用`00_prison_effects.txt`的`ransom_interaction_effect`。共用效果读取`prisoner`、`payer`、`imprisoner`，按选项支付金币、牵制、影响力或牧群，然后调用`release_from_prison`。北疆在效果开头重置并保存本次资格，实际释放后计分；资格要求付款者和关押者本人参与、仍由该关押者羁押，以及囚犯当前或本次羁押快照证明重要异国身份。通用释放可以清理快照，但不会抹掉本次交易已经核验的临时值；批量赎回每个囚犯重新初始化，避免串用。

原版`release_from_prison_interaction.on_accept`先处理实际释放，再在“无要求”分支检查13个选项均为`no`：`demand_conversion`、`renounce_claims`、`banish`、`gain_hook`、`take_vows`、`become_executioner`、`recruit`、`disfigure`、`blind`、`castrate`、`demand_admin`、`change_prison`、`make_puppet`。北疆在仍被羁押时保存双方资格和主权身份，仅在此分支且受影响者实际获释时触发`tca_frontier_release_succeeded_effect`。不把越狱、普通脚本释放或其他附条件释放当作无条件释放。

上述三个对象均无可追加的专用成功回调，互动及scripted effect也不能像on_action一样跨文件追加执行块。因此仅覆盖这三个必要对象，原版全部可执行内容保留，加入准备／成功钩子；不覆盖整份原版文件，不借宗教等无关辅助效果承接。基线、理由和冲突范围登记于`tools/upstream_overrides.json`；修改同名对象的其他模组须合并。原版`on_release_from_prison`仍仅负责清理，不能提供交易原因。

### 当前催化判定入口

- `tca_frontier_title_in_scope_trigger`在头衔作用域判断：伯爵领的`title_province`位于`tca_frontier_region`，或其`any_de_jure_county`中至少一个县位于该范围。`tca_frontier_war_in_scope_trigger`只检查战争`target_titles`列表，不因任一参战国有北疆土地就把其南方战争纳入。
- 宣战由`on_war_started`承接：局势存在、战争存在、主攻守双方`top_liege`不同、目标合格且该战争尚无`tca_frontier_declaration_counted`，才计一次。胜利使用互斥的`on_war_won_attacker`／`on_war_won_defender`，以目标及战前国家快照防止完全吞并后误当内战；白和平没有计分回调。
- `tca_frontier_person_action_valid_trigger = { ACTOR = ... }`在受影响人物作用域检查：本人先通过`tca_frontier_important_person_trigger`，发出者本人通过`tca_frontier_is_participant_trigger`，双方`top_liege`不同。重要性入口要求本人先是参与者，再满足独立君主、边疆组资格、或`this = top_liege.primary_heir`之一；普通境内官员及相关部职不自动重要。
- 囚禁使用`on_imprison`的囚犯root与`scope:imprisoner`，通过上述条件后记录本次羁押的国家、关押国与重要身份。死亡使用`on_death`的受害者与`scope:killer`；责任人必须仍有参与资格，受害者符合当前条件或有效羁押记录中的异国重要身份。处决与杀害由次日实际死因互斥分类，不从人物关系猜幕后凶手。
- 释放与赎回共用`tca_frontier_captive_action_valid_trigger = { ACTOR = ... }`：受影响者符合当前异国重要人物条件，或羁押快照仍标记重要、被俘前国家不同且记录的关押国等于当前关押者国家。实际羁押关系由各交易prepare入口另行核验；原始接入时序见上节。

# 原版天朝文官任命继承

> 依据 CK3 1.20.0.4（All Under Heaven，内部前缀 `tgp`）原版脚本整理；路径相对游戏根目录。本文只记录原版机制，模组复用关系见文末；专职选官实现另见[官职任命](README.md)。未在引擎中复现的判断标“待验证”。

## 速览

| 项目 | 地方民政辖区 | 中央文官省部 |
| --- | --- | --- |
| 继承法 | `celestial_appointment_succession_law`（天朝任命继承制） | `celestial_ministry_appointment_succession_law`（省部任命制） |
| 法律位置 | `common/laws/00_succession_laws.txt:1333`，继承顺序组 index 26 | `common/laws/01_title_succession_laws.txt:321`，头衔继承组 index 10 |
| 法律层级 | 领地法（realm law），统一约束该封臣名下任命制头衔 | 头衔法，逐个省部头衔固定 |
| 任命类型 | `celestial_civic_governor` | `celestial_minister` |
| 默认给谁 | 天朝、非独立、非军政契约的封臣 | 八个文官省部头衔（历史中直接写入） |
| 排序依据 | 先功绩等级，再候选分数 | 同左 |
| 任命冷却 | 5 年（`RECENT_APPOINTMENT_COOLDOWN`） | 同左 |

“文官”在本文指民政辖区与文官省部，不含军政辖区、枢密使和大将军；后者使用 `celestial_military_appointment_succession_law`（index 27）或 `celestial_grand_marshal_appointment_succession_law`。

## 地方民政辖区

### 适用条件

`celestial_appointment_succession_law` 的各段触发器（`common/laws/00_succession_laws.txt:1333`）：

| 段 | 条件 |
| --- | --- |
| `can_keep` | 行政机制；非独立统治者；**不带** `celestial_military_appointment` 契约标记；未被契约锁定为分割继承 |
| `can_have` | 行政机制；非独立统治者 |
| `can_pass` | 行政机制；非独立统治者 |
| `should_start_with` | 天朝政体；非独立统治者；**不带**军政契约标记 |
| `potential` | 天朝政体；非独立统治者 |

要点：

- 该法不要求“民政标记”，只排除军政标记。`celestial_civil_appointment` 只出现在三类民政契约上，见下节。
- `potential` 排除独立统治者，因此中国皇帝本人不挂此法；帝位继承不在本文范围。
- 法律失效后会在约一个月内被默认法替换（原版 `common/laws/_laws.info` 的 `can_keep` 说明）。契约从民政改为军政时，民政法的 `can_keep` 因军政标记失败，默认法解析会落到军政法；原版契约切换效果也会显式补挂军政法（`common/scripted_effects/10_dlc_tgp_scripted_effects.txt:720` 起）。
- 分割类继承法的 `potential` 都排除 `government_is_celestial`（如 `common/laws/00_succession_laws.txt:77`、`:171`、`:242`），所以天朝封臣实际只能在民政法与军政法之间选择。`_laws.info` 说明 `appointment` 顺序可同时用于领地与头衔，因此民政法是领地法，不是逐头衔法。

### 契约分类

`common/subject_contracts/contracts/celestial.txt`：

| 契约级别 | 标记 | 对应法律 |
| --- | --- | --- |
| `celestial_province_standard`（州） | `celestial_civil_appointment`、`province_civilian` | 民政 |
| `celestial_province_industrial`（监） | `celestial_civil_appointment`、`province_civilian` | 民政 |
| `celestial_province_metropolitan`（府） | `celestial_civil_appointment`、`province_civilian` | 民政 |
| `celestial_province_military`（军） | `celestial_military_appointment`、`province_military` | 军政 |
| `celestial_province_protectorate`（都护） | `celestial_military_appointment`、`province_military` | 军政 |

因此模组把“军”显示为知军时，该头衔仍走军政继承法，不属于本文的民政任命。

### 法律自带修正

`modifier`：`glory_hound_opinion = -10`、`courtly_opinion = 5`、`player_heir_opinion = 20`、`eligible_child_except_player_heir_opinion = -5`。`pass_cost`/`revoke_cost` 只花威望（`change_succession_law_prestige_cost`）。

## 中央文官省部

`celestial_ministry_appointment_succession_law`（`common/laws/01_title_succession_laws.txt:321`）：

- `can_have`：天朝政体；`can_title_have`：`tgp_is_civilian_minister_title`；`can_realm_have` 恒否，所以只管单个头衔。
- `can_remove_from_title` 恒否，省部不能移除该法。
- 任命类型 `celestial_minister`（`common/succession_appointment/celestial_minister.txt:1`）。
- 法律自带 `celestial_government_opinion = 5`。

八个文官头衔在 `history/titles/e_china.txt` 中逐个写入 `succession_laws = { celestial_ministry_appointment_succession_law }`：

`e_minister_chancellor`、`e_minister_censor`、`e_minister_of_personnel`、`e_minister_of_revenue`、`e_minister_of_rites`、`e_minister_of_war`、`e_minister_of_justice`、`e_minister_of_works`。

`e_minister_grand_marshal` 使用 `celestial_grand_marshal_appointment_succession_law`，任命类型 `celestial_military_governor`，不属文官。

省部头衔是 `landless = yes` 的无地帝国级头衔（`common/landed_titles/02_china.txt:8623` 起）。

## 候选池、排序与继承

### 池的生成

任命类型 `celestial_civic_governor` 设置 `level = merit`（`common/succession_appointment/celestial_governor.txt:1`）。按原版 `common/succession_appointment/_succession_appointment.info`：

- 设置 `level` 后忽略 `default_candidates`。中央 `celestial_minister` 同样设置 `level = merit`，因此其显式声明的默认类别也不能当作最终候选池范围。
- 候选人是“达到该头衔所需货币等级的所有合格角色”。民政文官的 `default_candidates` 未写，因此不能理解为“领主亲属＋封臣”那一套。
- `allowed_candidate_tier = lower_or_equal`：允许低于或等于目标头衔等级的候选人。接口另说明，有地统治者若被任命到低于自身等级的有地头衔，须为目标的法理领主；这是另一个带条件的限制，不能合并解释为普遍允许降阶。无地专职官署的实际资格待引擎验证。
- `cooldown = yes`：受任者进入任命冷却。

法律说明写“境内所有成年人可竞争”，游戏内概念 `game_concept_merit_pool` 写池包含“所有潜在角色”。实际池由引擎按“可被该领主授予头衔者”生成，本次只核对到脚本与界面文本，具体成员构成待引擎复现。

### 资格限制

`common/scripted_triggers/07_ep3_triggers.txt:915` 的 `is_appointment_valid_trigger` 与人际交互的 `can_appoint_for_title` 共同限制：

- 成年；若目标头衔等级等于领主的最高头衔等级，不作此检查。
- 非神职。
- 不能是最高领主首都所在伯爵领。
- 在任者不能作为自己的继任候选。
- 天朝特有：已持更高阶头衔者不能竞争较低阶头衔。
- 已经持有头衔的候选人，若目标头衔的“重要性”不高于其现有头衔，会在继承时被跳过（见下）。

### 功绩等级门槛

`common/defines/00_defines.txt:1861` 的 `APPOINTMENT_MERIT_TIER = { 0 1 1 3 5 7 9 }` 定义各头衔等级所需功绩等级；脚本侧 `common/script_values/10_dlc_tgp_china_values.txt:99` 起给出同组期望值，并注明必须与 define 一致：

| 头衔等级 | 所需功绩等级 |
| --- | --- |
| 伯爵 | 1 |
| 公爵 | 3 |
| 王国 | 5 |
| 帝国 | 7 |
| 霸权 | 9 |

男爵不在脚本期望值表中，实际授职很少涉及。省部是无地帝国级头衔，按此表应为 7；但原版 `merit_level_too_low_ministry_desc` 文案写“2”，该键未在脚本中使用，属引擎界面文本，待核对。

### 排序与继承

游戏内概念 `game_concept_merit_pool` 写明：使用功绩的任命继承法，候选人**先按功绩等级、再按候选分数**排序；持有者死亡时头衔传给列表最前者。若最前者已持头衔，新头衔的 `appointment_prominence` 必须高于其现有头衔，否则顺延。

这与法律副标题“拥有最高分数的候选人继承”并不完全一致：副标题只概括分数，实际首选键是功绩等级。排序由引擎完成，本次未在游戏中复现，标待验证。

“重要性”（`appointment_prominence`）由 `appointment_title_value` 计算（原版 `common/script_values/tgp_values.txt:272`）：民政头衔按 24 个月收入加“距首都距离”加成；军政头衔按兵员规模和行省规模。模组覆盖了该脚本值，见文末。

### 冷却与退出

- 受任后 5 年内不再被考虑为其他任命候选人（`RECENT_APPOINTMENT_COOLDOWN = 1825`，`common/defines/00_defines.txt:1867`）。`level` 模式下原版说明为“有时执行”，触发条件待验证。
- 角色可用辞谢任命决议（`tgp_refuse_appointments_decision`）把自己从候选池移除（设定 150 年任命超时），再用恢复任命决议（`tgp_resume_appointments_decision`）重新加入。

## 评分构成（地方文官）

任命类型 `celestial_civic_governor` 的 `candidate_score` 依次累加（`common/succession_appointment/celestial_governor.txt:1`）：

| 组成 | 主要内容 | 脚本位置 |
| --- | --- | --- |
| `appointment_score_base` | 威望与家族威望（仅“家族”法时）、中华传承 4、诗人志向、影响力等级、特质、罪行、宣称、关系、内阁/宫廷职位、阴谋、决策、请愿、性别法、独立者 −1000 | `07_appointment_values.txt:394` |
| `appointment_score_civic` | 心智不健全 −100；儒家教育经验 ÷4（最低 5）；文官职业分变量；东亚洲宅邸官署 +10/20/40/80；公爵征服 perk +20 | `:1153` |
| `appointment_score_celestial` | 家族宅邸在头衔法理内 −20；与现任持有者或本人领主同王朝 −50 | `:1671` |
| `appointment_score_governor` | 与领主开战 −9999；总督特质 +5 至 +20；礼仪敌对 −10/−25/−50 | `:1406` |
| `appointment_score_non_military` | 首都伯爵领持有者好感 ×0.25（头衔持有者为最高领主时 ×2）；内阁 +20；宫廷职位 +10 | `:1253` |
| 年龄 | 超过致仕年龄按（致仕年龄 − 年龄）÷2 扣分；40 岁以上 +15；30 岁以下 −10 | 任命类型内 |
| 技能 | 学识 ×0.5、外交 ×0.25、管理 ×0.25，四舍五入 | 同上 |
| 教育 | 外交/管理/学识五星教育 +10 | 同上 |
| 虔诚 | +10 ×（虔诚等级 − 1） | 同上 |
| `appointment_score_final_factors` | 扩张权力基础 +10%/20%/30%（最低 25/50/75）；摄政请愿 ×1.1、×1.15 | `:1498` |

补充：

- 影响力等级本身给 `+10 ×（等级 − 1）`；持有“推举”法时翻倍，天朝不用该法。
- 性别法：偏好法下非偏好性别 −100，专属法下 −9999。
- 与领主开战、独立统治者、礼仪性领主等是硬性排除或极大负分，不是普通加减。
- 地方文官评分**不含**天命循环/党争加成；相关加成只出现在省部任命类型里。

## 评分的共用部分

地方与中央任命类型明确共同调用 `appointment_score_base`、`appointment_score_governor`、`appointment_score_final_factors`，并共同使用功绩等级、同级候选许可和任命冷却。文官职业分与年龄项两边都有，但中央另外编写，不能据此把整套 `appointment_score_civic` 当作共用部分。

这为“共享原版底座、各职保留专业侧重”提供静态参考，不代表自定义法律的优先级、候选池和实际授职已经验证。

## 省部评分（差异）

`celestial_minister`（`common/succession_appointment/celestial_minister.txt:1`）同样 `level = merit`、`allowed_candidate_tier = lower_or_equal`、`cooldown = yes`，但评分组成不同：

- 年龄：超龄 ÷4；40 岁以上 +10；30 岁以下 −5。
- 文官职业分变量、东亚洲宅邸三省官署 +10/20/40/80。
- 得势文化 +100；党争领袖 +100，得势党派 +25，拥戴霸主 +10/+25。
- 按头衔取对应属性：宰相/吏部看外交，御史看谋略，兵部看军事，户部/工部看管理，礼部/刑部看学识。
- 最后加 `appointment_score_base`、`appointment_score_governor`、`appointment_score_final_factors`。
- 不含 `appointment_score_civic`、`appointment_score_celestial`、`appointment_score_non_military`，所以没有宅邸在辖区、同王朝、首都好感的修正。

## 提高胜算的原版手段

1. **功绩等级**：排序第一键，来自科举与任职积累。低于头衔门槛不入池。
2. **影响力与职业分**：`influence_meritorious_career_interaction`（`common/character_interactions/10_tgp_interactions.txt:4133`）花影响力给目标加文官/武官职业分。宰相 −50% 花费、吏部尚书 −30%、权门 −20%；宰辅另有直接加候选分、赐功绩、免科举等选项。
3. **宅邸官署建筑**：东亚洲宅邸的文官官署按级别加分。
4. **儒家教育**：`confucian_education` 经验折算为分数。
5. **年龄**：40 岁至致仕年龄之间最有利。
6. **关系与职位**：与现任头衔持有者同王朝会扣分；在其内阁或宫廷任职会加分。
7. **避开敏感任职地**：家族宅邸在目标辖区会扣分。
8. **继承法环境**：`candidate_score_laws` 为“家族”时威望和家族威望才计入基础分。

注意：通用 `influence_candidacy_interaction`（`common/character_interactions/06_ep3_interactions.txt:2`）的 `is_available` 要求 `NOT = { government_has_flag = government_has_merit }`，天朝不能使用；天朝走职业分互动，不要照搬拜占庭式“投资候选人”。

## 相关法律与全局修正

| 法律/机制 | 作用 |
| --- | --- |
| `candidate_score_laws`（`common/law_groups/02_admininistrative_law_groups.txt:60`） | “贤能”（默认）不计威望与家族威望；“家族”计入 10×威望等级＋10×家族威望等级。仅中国皇帝可改，花费 1000 影响力＋领地规模×10 国库，带冷却。 |
| `celestial_retirement_law` 0–5 | 致仕年龄 50/60/70/80/90/无固定，直接改变年龄扣分起点。 |
| `celestial_bureaucracy` 0–3 | 主要管剥夺、战争、权威与头衔不出境，不直接改候选分；0 级带 `titles_cannot_leave_realm_on_succession`。 |
| `tgp_chinese_legacy_4` | 家族传承给 +15 候选分。 |
| 党争/天命循环 | 只进省部评分；地方文官不吃这些加成。 |
| AI | 不资助 50 岁以上候选人；影响力不足不主动使用职业分互动。 |

## 与模组的关系

- [通判](../tongpan/README.md)与[司法](../judicial/README.md)的持有人保留原版 `celestial_appointment_succession_law`，官署另装各自的头衔法与任命类型，完整复用本文地方评分底座并调整本职能力／性格，入口见[官职任命](README.md)；`common/laws/tca_judicial_succession_laws.txt` 只为旧存档保留可解析的 `tca_judicial_appointment_succession_law`，不再挂到新官职。
- 模组不覆盖上述两条原版继承法，也不改 `celestial_governor.txt`、`celestial_minister.txt`。
- 模组覆盖 `appointment_title_value`（`common/script_values/appointment/zz_tca_appointment_values.txt`，原版基线 `common/script_values/tgp_values.txt:272`），为司法、通判头衔提供价值，并保留原版民政/军政估算。该值决定“已持头衔者是否让位”，改动会影响调任结果，须与通判、司法文档一起复核。
- 原版若调整法律、评分权重、功绩门槛或契约标记，先核对本页再改模组；本页不是覆盖登记，覆盖清单仍以 `tools/upstream_overrides.json` 为准。

## 待验证

1. 候选池的实际成员构成与“所有成年人”文案的差距；`level` 门槛在引擎侧的精确判定。
2. “先功绩等级、再候选分数”的排序是否与所有头衔等级一致；法律副标题只写“最高分数”。
3. `level` 模式下 5 年任命冷却的“有时执行”具体条件。
4. 契约在民政/军政间切换后，法律是即时由脚本补挂，还是等约一个月的 `can_keep` 失效替换；两者结果相同，时点不同。
5. 省部头衔按帝国级应要求功绩 7，但界面文案写 2；以引擎实测为准。
6. AI 的候选支持、职业分互动频率与年龄限制在实战中的表现；本次只读脚本，未开测试局。

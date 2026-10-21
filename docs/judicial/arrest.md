# 拘捕执行与公职囚犯

## 当前实现

- 分层权限、身份评分、州／路管辖与中央替补审批见[辖区、位望与审批](authority.md)，该文档是当前权限规则入口。
- 伯爵／公爵级文官州主管、路主官与提刑分别在本人辖区发起。地方低分对象直接拘捕，中层请求提刑，高层请求中央；提刑中层可直接，高层也需中央批准。
- 中央按刑部→御史→宰相→皇帝解析；提刑缺位的中层请求上送中央。审批与关押分离，成功后由发起人收押，只有提刑本人发起的囚犯登记为提刑公职囚犯。
- 合法理由、牵制、暴政仍归实际发起人；AI必须拥有拘捕理由。请求批准不保证拘捕成功。
- 州／路主官承担本人发起的拒捕战争；提刑的军事支持者按[统一辖区规则](authority.md#法理司法辖区2026-10-14当前实现)解析。实际捕获后延迟交给提刑；普通地方官发起的拘捕不登记引渡。
- 公职囚犯释放、死亡、换任、空缺与撤销时沿用登记清理及交接；不交接提刑私人囚犯。
- 原版普通及摄政囚禁对纳入新机制的官员均受限制；皇帝及中央大臣的原版入口保留。权限变化后的旧请求重新检查，而不是自动转发。

## 公职囚犯交接

已在狱中的角色不能直接再次收押；共享交接效果先释放，再按原监禁类型由新看管者收押。转移标记及当前在押检查保护双向登记，无法交接而仍在押时保留登记。只转移公职囚犯，不处理私人囚犯。

该实现不调用完整拘捕暴政／亲属好感包装；但仍会触发原版释放／收押回调，关押时长、记忆、消息与其他原版结果须完整玩法验收，不能称为无附带效果的原子转移。详细记录见[司法法律测试](verification.md)。

## 原生审批队列

请求互动禁用整个互动的 `auto_accept`，因为它会同时跳过审批人与目标两个阶段。审批后原本不能拒捕的无地 AI 目标使用专用接受分支；玩家目标仍需本人回应。真实发送、等待、审批及收押分别验证，不能以直接调用接受效果代替。

## 实现入口与兼容影响

- `common/character_interactions/tca_judicial_arrest_interactions.txt`：直接／请求两种互动、审批、资格、回复与 AI。
- 请求拘捕的 `ai_intermediary_accept` 直接保留原生评分结构：基础值20、合法理由+80、审批人对发起人好感×0.25、对目标好感×−0.25；仅无合法理由时 `ai_honor` ×−0.25。审批与拘捕均开启随机开关，不再使用端点转换、独立审批脚本值或显示修正。
- `localization/{simp_chinese,english}/tca_judicial_arrest_l_*.yml`：审批使用将批准／否决／可能批准三种提示，可能批准时显示百分比；自定义评分理由保留 `$VALUE|=+0$`，逐项明细自动生成。不新增或覆盖 GUI。
- `common/opinion_modifiers/tca_judicial_arrest_opinions.txt`：否决后的三项3年、不叠加好感修正。
- `common/scripted_triggers/tca_judicial_arrest_triggers.txt`：官员身份、辖区与发送/回复时资格复查。
- `common/scripted_effects/tca_judicial_arrest_native_effects.txt`、`common/scripted_modifiers/tca_judicial_prison_modifiers.txt`：从本机原版拘捕流程改写的结果、拒捕与 AI 分数。
- `common/scripted_effects/tca_judicial_prison_effects.txt`、`common/on_action/tca_judicial_prison_on_actions.txt`、`events/tca_judicial_prison_events.txt`：登记、交接、延迟引渡。
- 仅覆盖原版 `imprison_neutral_is_valid_showing_failures_only_triggers_trigger`，保留原版检查并限制地方／司法官员使用普通与摄政拘捕入口。其他 mod 覆盖同名 trigger 时存在加载顺序冲突。通用原版漂移检查步骤见 [原版覆盖检查](../development/upstream.md)。

原版参考（本机 1.20.0.4）：`game/common/character_interactions/00_prison_interactions.txt` 的 `imprison_interaction`，`game/common/scripted_triggers/00_scripted_triggers.txt` 的 basic/advanced 囚禁资格，`game/common/scripted_effects/00_prison_effects.txt` 的暴政、合法收押与拒捕战争，以及 `game/common/on_action/prison_on_actions.txt` / `war_on_actions.txt` 的角色作用域。

## 概率审批

请求拘捕同时设置 `ai_intermediary_maybe = yes` 与 `ai_maybe = yes`，与本机1.20.0.4原版 `game/common/character_interactions/00_diarch_interactions.txt` 的 `diarch_imprison_interaction` 相同。审批按现有分数进行随机判定，批准后才继续拘捕判定；审批否决本身不算目标拒捕，不引发拒捕战争。审批总分在0～100之间时表示概率；不能沿用旧权重场景的+13/+52推算新概率。两项概率是不同阶段，底部拘捕百分比不等于请求整体成功率。

### 数值、代价与冷却

- 批准分 = 20 + 合法理由80 + 提刑对请求者好感×0.25 − 提刑对目标好感×0.25；仅无合法理由时增加提刑 `ai_honor` ×−0.25。中立关系有合法理由时为100，无理由且性格项为0时为20。法律项不再使用旧的+75。
- `on_intermediary_decline` 先恢复互动角色并复查有效性；有效否决执行请求者 `add_prestige = -100`、`change_influence = -50`。审批官员不扣威望、影响力或功绩。失效请求走取消分支，不执行否决惩罚。
- 请求者对提刑−15；目标对请求者−10、对提刑+20。三项修正固定持续3年且不叠加，也应用于玩家角色，不赋予任何额外犯罪或拘捕理由。
- 请求互动使用原生 `cooldown = { months = 3 }` 与 `cooldown_against_recipient = { years = 1 }`。发送后，请求者3个月内不能再使用此互动，1年内不能对同一目标再次使用，批准、否决均不退还冷却。提刑及中央审批者仍可审核其他官员的请求。
- 冷却属于角色与互动，不属于官职或审批人；换请求者不继承旧请求者的冷却。提刑主动“辖区拘捕”保持原来的同目标10天冷却，没有新增3个月全局冷却。
- 取消或否决时清除的是既有10天敌对行动锁，不清除原生请求冷却。否决惩罚不进入目标拒捕分支，也不触发拒捕战争。原有摄政附加发送成本保持不变，没有另加此前讨论过的25威望发送费。

显示文本只保留请求、批准、否决等简短说明及角色标签，不写死资源数值、冷却时长、关押归属或拒捕战争细节。否决代价与关系变化由实际效果预览生成，冷却由原生不可用提示显示截止日期；中英文同步简化。数值及行为仍在本文作为当前实现与验收依据记录。

原版依据：`00_diarch_interactions.txt` 的摄政囚禁同时使用全局及同目标冷却；`_character_interactions.info` 明确说明两个字段。中文 `interactions_l_simp_chinese.yml` 的 `character_interaction_on_cooldown` 和 `character_interaction_against_on_cooldown` 显示不可用截止日期。原版 `10_tgp_interactions.txt` 使用 `change_influence` 扣除影响力；`common/opinion_modifiers/_opinions.info` 与现有对象支持 `years`、`stacking`。当前复用原生字段和效果，不覆盖原版对象或GUI。

### 当前显示与扩展

审批使用本互动的三种标题；0～100之间显示“审批人可能批准拘捕：X%”，端点使用将批准／否决标题。因素在 `ai_intermediary_accept` 中直接使用原生 modifier、opinion_modifier和ai_value_modifier，原生系统生成基础值与逐项理由。新增因素只需扩展该评分块；新理由增加中英文desc本地化，无需同步另一份评分总和或GUI列表。自定义理由文本必须包含 `$VALUE|=+0$` 才会显示分值。

拘捕结果使用原来的 `ANSWER_MIGHT_SUCCEED`、`ANSWER_CANT_SUCCEED`、`ANSWER_WILL_SUCCEED` 与 `ANSWER_SUM_CHANCE`；保留原生行为及显示边界，包括原生悬浮明细可能显示未截断负分，而底部实际概率为0%。此次没有额外覆盖原生百分比格式。

### 验证范围与步骤

自动原生回归及其边界见[司法验证](verification.md)。以下步骤用于真实玩家路径、随机分布和显示，不能由工具检查或直接回复效果替代。

1. 重启游戏并加载尚未发送该请求的存档，检查新生成的 `error.log`；旧待回复请求可能保存旧的判定结果。
2. 准备中立关系场景：有合法理由时基础审批总分100；无理由且性格为0时总分20。改变提刑对双方好感，检查每点好感的权重为±0.25。明细没有100／0修正项、审批决定或动态脚本值空白。
3. 在多个新请求中验证审批可能批准或否决；同一存档反复重载可能重复随机序列，不作为概率分布验证。抽样结果不要求精确匹配显示概率。
4. 测试审批分数≤0和≥100两个端点；否决无拘捕、无拒捕战争；批准后拘捕仍可能失败，无合法理由仍有暴政。
5. 测试玩家提刑人工否决及AI否决：请求者威望减100、影响力减50；提刑资源不因否决减少。检查三项关系方向、数值、3年期限及重复否决不叠加。批准后拘捕失败不触发这组惩罚。检查低资源请求者的实际扣除与引擎下限行为。
6. 发送请求后马上换目标，检查原生3个月冷却及截止日期；3个月后换目标可请求、同目标仍被阻止，1年后同目标可请求。检查另一个观察使能正常向同一提刑提交请求，以及提刑主动拘捕不受新增全局冷却。保存重载后复查。
7. 发送后换任提刑/请求者或改变目标辖区、囚禁状态，测试否决回复走取消且不扣否决代价；原生冷却仍保留。中英文核对简短说明、否决页真实效果及通知；确认具体代价由真实效果生成、冷却由原生日期提示生成，文本不再重复写死数值。
8. 测试玩家提刑人工批准，以及提刑主动拘捕，确认原有结果、囚犯登记和交接行为。

## 本地化调用约定

- `[character.GetTitleAsName]`：读取角色当前官衔。纯文字标题使用 `GetTitleAsNameNoTooltip`。
- `[character.GetTitledFirstName]`：读取带官衔的人名，适合说明谁批准、关押或承担战争。通知标题使用 `GetTitledFirstNameNoTooltip`。
- `[character.GetShortUIName]`：按阅读者显示人名或“你”，用于上下文已经明确的后续指代。
- `[title.GetName]`：读取头衔当前名称，用于实际绑定的辖区或机构；`GetNameNoTierNoTooltip` 用于定义名称时避免附加等级和提示。

原版证据：`game/localization/simp_chinese/interactions/diarch_interactions_l_simp_chinese.yml:4` 使用 `GetTitledFirstName`，`:161` 使用 `GetTitleAsNameNoTooltip`，`:234` 使用 `GetTitleAsName`。`game/common/flavorization/11_tgp_china_flavorization.txt:223` 起按身份、政府等选择王国级官衔；`game/localization/simp_chinese/culture/culture_titles_l_simp_chinese.yml:1314` 是“观察使”的称号定义，而不是互动文案应重复写入的常量。

本 mod 的 `tca_celestial_duke_holder_*` 已接入原版 flavorization，`TCAJudicialHolderTitle` 根据当前主要头衔的标记返回 `tca_judicial_holder`。因此互动直接使用原版角色取名函数，不额外增加一套官衔选择器。`GetTitleAsName` 读取的是角色当前主要称号；不应用于人物兼任多个职位时指定次要官衔。当前提刑任职资格要求官职为主要头衔，符合这个使用条件。

## 验证边界

正式真实发送用例、自然释放／死亡证据、人工审批与保存重载的分工见[司法验证](verification.md)。历史完整组通过不保证当前快照或所有无地宗教头衔均已验证。

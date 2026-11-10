# 行政整饬系统（归正辖属 & 裁撤兼领）

行政整饬是皇帝与宰相依据既有法理，纠正天朝制下不规范行政管辖关系的制度性权力。系统只调整实际行政结构（封属关系与兼领头衔），不修改法理疆界，不产生暴政或宣称权，也不设置玩家豁免或拒绝选项。

## 一、核心角色互动与架构

| 互动 ID | 互动名称 | 处理对象 | 核心效果 |
|---|---|---|---|
| `tca_rectify_subordination_interaction` | 归正辖属 | 实际封属关系与主头衔法理上级持有人不一致的地方官员 | 派发书信，确认后将直属上级改隶为法理上级头衔持有人 |
| `tca_retract_concurrent_title_interaction` | 裁撤兼领 | 兼领不当官署或越辖直辖领地的官员（皇帝，或宰相在无需批准范围内） | 指定一个头衔派发书信，确认后移交合格继任官员并理顺封臣关系 |
| `tca_request_retract_concurrent_title_interaction` | 奏请裁撤兼领 | 宰相在权力天平 `< 60` 时裁撤王国级兼领官署 | 经原版 `intermediary` 奏请皇帝批准后，派发裁撤兼领书信 |

相关实现文件：

- 角色互动：[`tca_admin_rectification_interactions.txt`](../../common/character_interactions/tca_admin_rectification_interactions.txt)
- 判定触发器：[`tca_admin_rectification_triggers.txt`](../../common/scripted_triggers/tca_admin_rectification_triggers.txt)
- 执行效果：[`tca_admin_rectification_effects.txt`](../../common/scripted_effects/tca_admin_rectification_effects.txt)
- 共享数值：[`tca_admin_rectification_values.txt`](../../common/script_values/tca_admin_rectification_values.txt)
- 书信事件：[`tca_admin_rectification_events.txt`](../../events/tca_admin_rectification_events.txt)
- 权力天平共治可见性桥接：[`tca_tongpan_hud.txt`](../../common/scripted_guis/tca_tongpan_hud.txt)（`tca_grand_secretariat_diarchy_details`）
- 原生回归测试：[`tca_admin_rectification_test_events.txt`](../../events/tests/tca_admin_rectification_test_events.txt)（包含资格例外、天平权限、归正执行、升迁腾退与全自然继任善后流水线共 5 项用例）

## 二、归正辖属规则

1. **适用条件**（`tca_rectify_subordination_target_valid_trigger`）：
   - 目标为同一最高领主天朝制下的伯爵级或公国级地方实职官员（排除家门、提刑、通判、奉祠致仕与中央大臣）；
   - **在途防重入互斥**（Pending Mutex）：目标身上不能已有在途的书信（排斥 `tca_rectify_pending_actor` 与 `tca_retract_pending_actor`）；
   - 目标主头衔具有明确的 `de_jure_liege`，且该法理上级头衔已有存活的天朝官员持有（若法理上级空缺则不可归正，须先由任官机制补齐）；
   - 目标当前直属上级（`liege`）与法理上级持有人不同；
   - 拟转入的法理上级持有人主头衔级别严格高于目标官员，且不形成封属循环。
2. **跨辖区兼领限制**（`tca_rectify_subordination_no_cross_jurisdiction_trigger`）：
   - 若目标官员持有任何可被【裁撤兼领】收回的不当兼领官署或越辖伯爵领，或持有法理上级与主头衔法理上级不同的其他公国头衔，直接转移整个角色会产生新的辖属错位，故禁止直接归正，提示先使用【裁撤兼领】理清头衔。
3. **执行效果**（`tca_execute_rectify_subordination_effect`）：
   - 书信事件 `tca_admin_rectification.10` 在次日送达，确认时二次复验（`tca_rectify_subordination_still_valid_trigger`），通过 `swear_fealty`（`add_claim_on_loss = no`）将目标直属上级变更为法理上级头衔持有人，不改变头衔与法理。

## 三、裁撤兼领规则

### 3.1 王国、公国级兼领判定與越辖伯爵领判定（`tca_is_retractable_concurrent_title_trigger`）

每次互动通过 `target_type = title`（`target_filter = recipient_domain_titles`）指定一个头衔，目标官员同样须满足在途互斥（未有在途整饬书信），并遵循以下法定豁免：

1. **主头衔豁免**：官员本人的 `primary_title` 始终允许持有，不可裁撤。
2. **首府所在公国豁免**：对于王国、公国级地方主官，其领地首府所在的法理公国头衔（`capital_county.duchy`）允许兼领；其他额外持有的王国级、公国级地方官署头衔可作为裁撤对象。
3. **伯爵级主官首府豁免**：对于伯爵级主官，其本人的领地首府伯爵领（`capital_county`）允许持有；其他额外伯爵领可裁撤。
4. **王国、公国级主官的直辖伯爵领与首府伯爵领特别例外**：
   - 位于主头衔法理管辖范围内（`target_is_de_jure_liege_or_above = primary_title`）的直辖伯爵领正常合法；
   - 位于主头衔法理管辖范围外的直辖伯爵领可被裁撤，**但当官员在主头衔法理范围内没有任何本人亲自直辖的伯爵领时（`NOT = { tca_official_holds_county_in_primary_de_jure_trigger = yes }`），允许保留位于主头衔法理范围外的领地首府伯爵领（`capital_county`）**；一旦官员在主头衔法理内拥有至少一个直辖伯爵领，该外部首府伯爵领即不再享有豁免。

### 3.2 继任选拔、3 次重抽与生成新官员（`tca_admin_rectification_select_or_generate_successor_effect`）

裁撤兼领直接将指定头衔移交合格继任者，不经过皇帝或上级临时接管，且必须满足目标官署正常的官品要求（王国级 `>= 5` 品、公国级 `>= 3` 品、伯爵级 `>= 1` 品），不特批放宽：

1. **现有候选池级别限制**：排除已持有同级或更高级实职的官员（王国级允许无实职／伯爵级／公国级；公国级允许无实职／伯爵级；伯爵级仅允许无实职），并要求已有地或已持有家门头衔以保证引擎有地头衔交接安全。
2. **抽取顺序**：
   - 首先检查待移交头衔的 `current_heir`，若符合全部任职资格，直接选为继任者；
   - 若不存在或不合格，从全国候选池按任官候选分加权（`tca_admin_rectification_candidate_weight_value`）最多重新抽取 3 次；
   - 三次仍未获得合格人选，则调用 `tca_admin_rectification_generate_official_effect` 生成新官员（火星人）。
3. **生成新官员（火星人）属性**：
   - 文官路／州郡使用 `tgp_minister_scholar_template`，军区／都护路（`tca_circuit_kind >= 2`）使用 `tgp_minister_commander_template`，文化与信仰匹配天朝最高领主；
   - 100% 具备童子试、乡试、会试通过记录，10% 概率具备殿试通过记录；
   - 初始官品与功绩：伯爵级 80% 九品／20% 八品；公国级 80% 七品／20% 六品；王国级 75% 五品／20% 四品／5% 三品；
   - 在互动接受当日（Day 0）完成王朝、家门头衔、领主与天朝政体准备，次日（Day 1）书信确认时安全接收有地头衔。

### 3.3 跨辖区升迁旧头衔腾退与封臣善后

- **跨辖区升迁腾退**（`tca_admin_rectification_vacate_promoted_old_title_effect`）：若现有低级有地官员升任公国或王国级官署，其位于新官署法理范围内的原头衔按兼领规则保留，位于新官署法理范围外的旧头衔**不适用首府公国或首府伯爵领例外**，同步移交合格替补继任官员。
- **封臣关系善后**：头衔移交后，原归于被裁撤官署法理下的直属下级官员改隶新任主官，原官员保留头衔法理下的下级官员仍留归原官员统属。

## 四、皇帝与宰相权限及权力天平

宰相（`grand_secretariat` 共治下的在任摄政）发起行政整饬受权力天平（`diarchy_swing`）三档约束，并在共治窗口权力天平等级 1、3、4 提示中展示：

| 权力天平阶段 | `diarchy_swing` 区间 | 对应天平等级 | 宰相整理皇帝直属官员 | 宰相裁撤王国级兼领 |
|---|---|---|---|---|
| 倾向皇帝 | `< 40` | 等级 1–2 | 不可使用 | 须奏请皇帝批准 |
| 权力均衡 | `40 <= swing < 60` | 等级 3 | 可以使用 | 须奏请皇帝批准 |
| 倾向宰相 | `>= 60` | 等级 4–6 | 可以使用 | 无须批准，直接执行 |

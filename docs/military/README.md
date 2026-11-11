# 地方驻军、军费与军事差遣

本页维护天朝地方军制头衔的基础驻军规模、中央军事预算份额，以及军事宫廷差遣（兵马监押、兵马都监、都虞候）与待阙官员铨选流转系统的核心规则与边界。

---

## 一、地方驻军与中央军费

维护天朝伯爵级军制头衔（知军）的基础驻军规模与中央军事预算份额。州制知州、府制知府、监制知监三类民政县采用民政省类型、关闭头衔兵士，不适用本节规则。

### 1. 实现入口

规则集中在原版隐藏契约 `celestial_salary_rank` 的县级义务 `celestial_salary_rank_county`（由[模组覆盖文件](../../common/subject_contracts/contracts/zz_tca_retirement_salary_rank.txt)承载）与原版省份类型契约 `celestial_provinces`（由[模组覆盖文件](../../common/subject_contracts/contracts/zz_tca_celestial_provinces.txt)承载）。

- 原版对象：`game/common/subject_contracts/contracts/celestial.txt` 的 `celestial_salary_rank` 与 `celestial_provinces`
- 契约组覆盖：`common/subject_contracts/groups/zz_tca_celestial_contract_group.txt`
- 原版政体：`game/common/governments/00_government_types.txt` 的 `celestial_government`
- 覆盖登记与基线：`tools/upstream_overrides.json`、`tools/baselines/tca_retirement_salary_rank.txt` 与 `tools/baselines/tca_celestial_provinces.txt`

### 2. 当前规则

只计该契约自身修正、不叠加法律／科技／文化加成时，伯爵级军制头衔的基准如下。表中基数按原版 defines 与契约修正推算，头衔兵士是否完全沿用同一基数仍需游戏内确认，见[验证边界](#4-验证边界)。

| 项目 | 县级修正 | 基准 |
| --- | --- | --- |
| 头衔兵士军团数 | `men_at_arms_title_cap = -1`（原版已有） | 伯爵级基数 2 − 1 = 1 队 |
| 头衔兵士单军团规模 | `men_at_arms_title_limit = -2`（模组新增） | 规模基数 3 − 2 = 1 级（每级 100 人） |
| 中央军事预算份额 | `monthly_treasury_from_military_budget_base = -1.0`（原版 -0.6） | 军制省 +1.0 − 1.0 = 0 |
| 在任考绩保底 | `monthly_merit = 1`（模组新增） | 伯爵级在任基础考绩保底 1.0/月 |

军制省（知军、帅臣）与边防军区在契约 `celestial_provinces` 覆盖中追加了 `monthly_merit_per_liege_tax = 0.3` 纳税功绩，使武臣兼理地方赋税民政时同样获得合理考课资望，消除小军州或暂无常备军时的零功绩死锁。公爵级及以上保持原版军事预算与常备军基准：公爵级军制净 +0.7，王国／帝国级净 +1.0。

### 3. 取舍与后果

- 选择隐藏契约而非事件、特质或政体修正：契约按最高头衔层级自动选档，只需改一处，无需新增事件与存档状态。
- 只压规模、不额外压军团数：军团数沿用原版 −1，避免在基准层就锁死后续法律与科技提供的军团数增长。
- 军费抵消只写在伯爵级：公爵以上保留原版比例。
- 旧存档：契约修正随存档加载重新结算，已在任知军的头衔兵士可能按新上限缩编；不写迁移，作为规则性改动的已知影响。
- 民政县不受影响：三类民政契约均设 `enable_title_maa = no`，没有头衔兵士可供压低。

### 4. 验证边界

静态与文档检查可验证覆盖登记与链接；下列行为仍需在独立、可丢弃测试局人工验收。本规则不新增自动化用例：头衔兵士上限与规模没有脚本读取接口，军事预算到账又依赖预算法与领主收入，脚本断言只能复述常量或变成脆弱的总收入比较。

县级知军的军事预算到账已人工确认为 0；以下项目仍待实测：
- 保存重载后军事预算仍为 0；县级民政无该条目且无负值；公爵级军制仍为 +0.7。
- 伯爵级头衔兵士军团数基数确为 2、规模基数确为 3；改后县级知军面板为 1 队、1 级。
- 扩大或缩小上限时，既有头衔兵士是缩编、保持还是销毁。
- 军制节度使下属县级知军（子封臣）不会出现只有 −1.0、没有军制省 +1.0 的负到账。

---

## 二、军事宫廷差遣与待阙官员流转

为解决待阙武官员多阙少、无差遣难以迁转且不适宜滥设无地头衔的问题，系统基于 CK3 宫廷职位复用为**兵马监押、兵马都监与都虞候**三级军事差遣，建立固定 Merit 培养与重要度单向流转晋升机制。

### 1. 差遣定位与架构

| 职位 | 适用宫廷层级 | 职掌定位 | 常驻基础效果（优秀称职度） | 月度功绩 |
|---|---|---|---|---|
| **兵马监押** | 伯爵级及以上地方官署 | 地方兵员与驻军管理、寨堡防务 | 控制力增长 +0.2、征召兵补员 +10%、防御优势 +2 | +1.5/月 |
| **兵马都监** | 公爵、王国及帝国级地方督抚 | 军队操练、兵甲整备、高级营防 | 军队维护费 −5%、军队坚韧 +3%、军队伤害 +2% | +2.5/月 |
| **都虞候** | 枢密使与王国级以上高级军路 | 将校管理、军令行纪、精锐行伍 | 骑士战斗力 +8%、骑士数量 +3 | +3.5/月 |

- **官署准入底线（实地基础 + 地方专属 + 军职白名单）**：
  - 彻底依托原生 `is_landed = yes` 守门：排除提刑司、六部尚书、宰相省部等纯无地中央文职设立军事差遣；
  - **天朝独立最高皇帝全面排除**：中央独立皇帝不设立地方军事差遣，保留中央殿中省乘舆掌管（尚乘奉御）；
  - **兵马监押**：必须为非独立实土地方领主（`is_landed = yes` 且 `is_independent_ruler = no`，最高头衔 $\ge$ 伯爵级）；
  - **兵马都监**：必须为非独立实土地方长官（`is_landed = yes` 且 `is_independent_ruler = no`，涵盖公国级、王国级及帝国级地方督抚）；
  - **都虞候**：极度尊崇，仅开放给**枢密使**（持有官方枢密院头衔 `title:e_minister_grand_marshal`）及**高级军路**（有地王国级及以上长官 + 军制省或都护府契约，`is_independent_ruler = no`）。
- **专属任务体系**：每职设 3 项专属任务（共 9 项），支持主官自由指派与 AI 稳健切换。
- **专职排他底线**：复用原版全职排他（`court_position_does_not_already_have_a_job_trigger`），排除内阁大臣、税吏及原版杂职；三军事差遣内部两两互斥。
- **严格限定待阙廷臣**：必须满足入品在籍（`merit_level >= 1`）、无地实官（`is_ruler = no`）且为本署待阙廷臣（`is_courtier_of = scope:liege`）；世族族长与有地封臣领主彻底排他。
- **纯官库财政支出（免除领主威望损耗）**：三大差遣定位为国家公职差遣，雇主维护费（`salary`）仅支出 `treasury`（有内库）或 `gold`（无内库），完全免除原版普通宫廷职位模板中的每月领主威望扣减；任职官员的考绩与声望成长由其自身 `modifier` 赋予。
- **封锁日常自主任免**：采用系统专属授权 Flag 锁（`tca_military_appointment_allowed`）限制自主任命，撤职消耗朝廷影响力（`revoke_cost` 依职级消耗微量至大量影响力，AI 与系统调拔自动免单），统一由朝廷系统按季铨选除授。

### 2. 动态重要度与单向晋升通道

官署战略动态重要度量纲由 7 维构成，总区间 $0 \sim 82$ 分：
- 体制军区（+15）、外国接壤（+15）、要塞城防（最高 +15）、辖区体量（最高 +10）、总军力人头（最高 +4）、头衔常备深度（最高 +11）、任职宫廷位阶（伯爵 0 / 公爵 3 / 王国 6 / 帝国 9 / 霸权 12，最高 +12）。

**单向阀门量纲铁律**：
- 兵马监押（100 ~ 182） < 兵马都监（200 ~ 282） < 都虞候（300 ~ 382）。
- 绝不发生同级平调或逆流贬黜；任期磨勘满 2 年（730 天冷却期）方可参与上一级差遣铨选。
- 季度除授时滞防雪崩：本季预先锁定出缺名单，拔擢后腾退的原职位留待下季自然补齐。

### 3. 实现入口清单

- 职位定义：`common/court_positions/types/tca_military_court_positions.txt`
- 职位任务：`common/court_positions/tasks/tca_military_court_position_tasks.txt`
- 原版覆盖（屏蔽地方御马官）：`common/court_positions/types/zz_tca_court_position_overrides.txt`
- 资格与判定触发器：`common/scripted_triggers/tca_military_court_position_triggers.txt`
- 战略权重与重要度宏：`common/script_values/tca_military_court_position_values.txt`
- 铨选调任与清理效果：`common/scripted_effects/tca_military_court_position_effects.txt`
- 季度心跳与离任挂载：`common/on_action/tca_military_court_positions_on_actions.txt`
- 中英本地化：`localization/simp_chinese/tca_military_court_positions_l_simp_chinese.yml` 与 `localization/english/tca_military_court_positions_l_english.yml`

### 4. 自动化测试与验证

自动化回归用例维护于 [events/tests/tca_military_court_positions_test_events.txt](../../events/tests/tca_military_court_positions_test_events.txt)，由模块效果 [common/scripted_effects/tests/modules/tca_test_modules_military_court_positions_effects.txt](../../common/scripted_effects/tests/modules/tca_test_modules_military_court_positions_effects.txt) 登记至全局测试目录。

- 回归套件代号：`--suite military_court_positions`
- 涵盖用例：
  1. `tca_test_military_court_positions_validity`：待阙资格过滤、权限 Flag 锁及封臣排他性校验；
  2. `tca_test_military_court_positions_importance_tier`：动态重要度量纲阶梯、宫廷位阶加分与单向阀门校验；
  3. `tca_test_military_court_positions_cooldown_and_cleanup`：两年任期磨勘锁定、离任清理与状态防残留校验；
  4. `tca_test_military_court_positions_exclusivity_and_rank`：全职职位排他（内阁/税吏）、知兵底线与在籍品级守门校验；
  5. `tca_test_military_court_positions_vanilla_override`：原版御马官（牧监）覆盖验证，地方封臣屏蔽与中央皇帝保留；
  6. `tca_test_military_court_positions_cooldown_and_empty_pool`：任期磨勘冷却拦截与待阙池耗尽（宁缺毋滥）安全熔断校验。
- 验收口径：在真实 CK3 引擎中保持 6/6 PASS、17/17 断言全绿、0 引擎错误。

---

## 三、相关设计与模块文档

- [差遣与流转系统设计](court_positions_design.md)：详细数值公式、称职度特质权重、AI 倾向与调度性能保障机制。
- [官制与名称](../court/README.md)：伯爵级省类型分类与官名。
- [官职任命](../appointment/README.md)：地方任命、品级铨叙与退休待遇。
- [测试框架说明](../testing/README.md)：原生自动化测试套件运行规范。

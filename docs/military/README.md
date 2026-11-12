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

以原生宫廷职位承载兵马监押、兵马都监与都虞候，为已入品、尚未持有正式官职头衔的合格待阙官员提供差遣与考绩。职位不新增独立领地或军队，朝廷按季度集中补缺，满任期者可参与更高重要度差遣的铨选。

### 1. 规则与维护位置

- [文武宫廷差遣统一设计](../court_positions/README.md)维护共用框架、文官职位、途径准入、重要度与最高分录取；实际验证范围由对应验证页说明。
- [差遣与流转设计](court_positions_design.md)维护军事官署准入、职位效果、专项任务与战略附加值；共用任职、待遇、评分与迁转规则见统一设计。待阙池沿用原版全职排他；任职期间只豁免本署军事差遣兼任本主君的军事内阁，其他内阁、税吏及全职杂职仍排他。
- [地方军事内阁联动](military_council_integration.md)维护同署选席、防撤职保护、离任与主君更替、玩家补位和内阁任务交接。同署可设置多种差遣，但同一人物不能兼领；唯一军事内阁按都虞候、都监、监押的顺序选择兼任者。
- 功绩入品、资格档位和正式头衔任官由[官职任命模块](../appointment/README.md)维护，本模块不另建升品或官职继承体系。

### 2. 实现入口

- 职位及专项任务：[职位定义](../../common/court_positions/types/tca_military_court_positions.txt)、[差遣任务](../../common/court_positions/tasks/tca_military_court_position_tasks.txt)。
- 资格及评分：[官署与人物资格](../../common/scripted_triggers/tca_military_court_position_triggers.txt)、[全职排他名单](../../common/scripted_triggers/tca_military_full_time_job_triggers.txt)、[铨选与重要度数值](../../common/script_values/tca_military_court_position_values.txt)。
- 调任及内阁生命周期：[正式效果](../../common/scripted_effects/tca_military_court_position_effects.txt)、[任务交接](../../common/scripted_effects/tca_military_council_task_effects.txt)、[原生回调追加](../../common/on_action/tca_military_court_positions_on_actions.txt)、[主君死亡后定向重绑事件](../../events/tca_military_council_events.txt)。
- 表现与兼容：[动态称谓](../../common/customizable_localization/tca_military_council_custom_loc.txt)、[地方御马官覆盖](../../common/court_positions/types/zz_tca_court_position_overrides.txt)；双语文本位于 `localization/`，覆盖及原版依赖统一登记于 `tools/upstream_overrides.json`。

### 3. 实现与验收

职位、铨选、内阁联动及任务交接均已实现；综合验收仍有未执行项目，不能将实现完成等同于全部验收完成。

原生用例统一维护于 [军事测试事件](../../events/tests/tca_military_court_positions_test_events.txt)，由 `military_court_positions` 和 `military_council` 两个模块登记。前者覆盖资格、评分、任免与补位，后者覆盖任务、同署优先级及独占延迟生命周期。冷却／空池用例自备地方官署和真实监押，直接调用季度流程共用的人物收集入口，分别检查磨勘期拒绝、解除冷却后接纳、重新冷却后拒绝，以及有效官署在候选池为空时保持出缺；任务显示资格另测雇主正例和普通廷臣反例。用 `--list` 读取实际范围，不在文档维护断言总数或逐轮成绩。

定向回归入口、验证边界及尚未执行的玩家界面、自然 AI、完整跨署升迁、旧存档与保存重载验收，统一见[联动验收](military_council_integration.md#回归与验收)。全模组回归按[测试运行说明](../testing/README.md)执行，军事定向结果不能替代全量结论。

## 三、相关模块

- [官制与名称](../court/README.md)：伯爵级省类型分类与官名。
- [官职任命](../appointment/README.md)：天朝文武品级晋升模型与任官资格。
- [测试框架](../testing/framework.md)：原生用例登记、并发 lane 与清理契约。

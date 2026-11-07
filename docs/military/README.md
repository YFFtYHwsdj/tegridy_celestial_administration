# 地方驻军与军费

本页维护天朝伯爵级军制头衔（知军）的基础驻军规模与中央军事预算份额。州制知州、府制知府、监制知监三类民政县采用民政省类型、关闭头衔兵士，不适用本页规则。

## 实现入口

规则集中在原版隐藏契约 `celestial_salary_rank` 的县级义务 `celestial_salary_rank_county`，由[模组覆盖文件](../../common/subject_contracts/contracts/zz_tca_retirement_salary_rank.txt)承载；该覆盖同时负责排除退休身份取得普通等级基础额。

- 原版对象：`game/common/subject_contracts/contracts/celestial.txt` 的 `celestial_salary_rank` 与 `celestial_provinces`
- 契约组覆盖：`common/subject_contracts/groups/zz_tca_celestial_contract_group.txt`
- 原版政体：`game/common/governments/00_government_types.txt` 的 `celestial_government`
- 覆盖登记与基线：`tools/upstream_overrides.json`

## 当前规则

只计该契约自身修正、不叠加法律／科技／文化加成时，伯爵级军制头衔的基准如下。表中基数按原版 defines 与契约修正推算，头衔兵士是否完全沿用同一基数仍需游戏内确认，见[验证边界](#验证边界)。

| 项目 | 县级修正 | 基准 |
| --- | --- | --- |
| 头衔兵士军团数 | `men_at_arms_title_cap = -1`（原版已有） | 伯爵级基数 2 − 1 = 1 队 |
| 头衔兵士单军团规模 | `men_at_arms_title_limit = -2`（模组新增） | 规模基数 3 − 2 = 1 级（每级 100 人） |
| 中央军事预算份额 | `monthly_treasury_from_military_budget_base = -1.0`（原版 -0.6） | 军制省 +1.0 − 1.0 = 0 |

公爵级及以上保持原版：公爵级军制净 +0.7，王国／帝国级净 +1.0。本规则只压伯爵级，维持官职层级差异。

## 基数与叠加

- 头衔兵士军团数基数按最高头衔层级：伯爵领 2、公爵领 3、王国 4、帝国 5，取自原版 `REGIMENT_MAA_CAP_BY_TIER`。
- 单军团规模基数 3，每级 100 人，依据原版 `REGIMENT_DEFAULT_MAX_SIZE`、`MAA_REGIMENT_SIZES`，以及头衔兵士调度成本脚本把单军团前 3 个规模单位视为基线的写法。
- 等级类修正是加算，法律、科技、文化、家族抱负与王朝周期照常叠加，不因契约压低基准而失效。例如 1066 开局天朝封臣已挂 `celestial_army_vassal_law_2`（`men_at_arms_title_cap = +2`），汉文化在 1060 已发现 `innovation_men_at_arms`（`men_at_arms_title_limit = +1`）；按上述基数推算，开局实际约为 3 队、2 级，高于本页基准，属预期加成而非规则未生效。
- 军事预算是费率而非兵员数：家族抱负等提供的 `monthly_treasury_from_military_budget_mult` 是乘区，基数为 0 时仍为 0，因此扩军不会重新产生中央军费。

## 取舍与后果

- 选择隐藏契约而非事件、特质或政体修正：契约按最高头衔层级自动选档，只需改一处，无需新增事件与存档状态。
- 只压规模、不额外压军团数：军团数沿用原版 −1，避免在基准层就锁死后续法律与科技提供的军团数增长。
- 军费抵消只写在伯爵级：公爵以上保留原版比例。
- 旧存档：契约修正随存档加载重新结算，已在任知军的头衔兵士可能按新上限缩编；不写迁移，作为规则性改动的已知影响。
- 民政县不受影响：三类民政契约均设 `enable_title_maa = no`，没有头衔兵士可供压低。

## 验证边界

静态与文档检查可验证覆盖登记与链接；下列行为仍需在独立、可丢弃测试局人工验收。本规则不新增自动化用例：头衔兵士上限与规模没有脚本读取接口，军事预算到账又依赖预算法与领主收入，脚本断言只能复述常量或变成脆弱的总收入比较。

县级知军的军事预算到账已人工确认为 0；以下项目仍待实测：

- 保存重载后军事预算仍为 0；县级民政无该条目且无负值；公爵级军制仍为 +0.7。
- 伯爵级头衔兵士军团数基数确为 2、规模基数确为 3；改后县级知军面板为 1 队、1 级。
- 扩大或缩小上限时，既有头衔兵士是缩编、保持还是销毁。
- 军制节度使下属县级知军（子封臣）不会出现只有 −1.0、没有军制省 +1.0 的负到账。

本次只改模组侧数值，不涉及基线刷新；收口运行 `python3 tools/check_upstream_overrides.py` 与 `python3 tools/scan_upstream_overrides.py`。

## 相关模块

- [官制与名称](../court/README.md)：伯爵级省类型分类与官名。
- [官职任命](../appointment/README.md)：地方任命与退休待遇。

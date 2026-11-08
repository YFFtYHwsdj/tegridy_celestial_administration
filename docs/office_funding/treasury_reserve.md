# 官库留储法

本页维护全国统一的官库留储与年度上缴规则：读取天朝官员的人物国库，按头衔等级保底与固定 24 个月留存收入上限计算应缴额，超出部分在每年 1 月 1 日转入皇帝国库。免缴档停收羡余，不进入年度结算。地方官署的拨款基数、费率与付款关系仍由[地方官署经费](README.md)维护，本页不重复其规则。

## 定稿参数

```
R = max( 24 × max(I_t, I_{t-1}, I_{t-2}),  B_tier × L )
T = max( 0, G − R )，T < 25 不转移、不通知
```

| 变量 | 含义 |
| --- | --- |
| `G` | 官员当前国库余额 `treasury` |
| `I` | `monthly_character_treasury_variable_income`，即留存国库收入；不扣军费与其他支出 |
| `B_tier` | 伯爵 250 / 公爵 500 / 王国 1000 / 帝国 2000；霸权同帝国 |
| `L` | 从严 0.75 / 常额 1.00 / 从宽 1.50；免缴档不结算 |
| `N` | 24，固定，不随档位变化 |

- 从严、常额、从宽三档只缩放保底；免缴档停收羡余，由结算范围 trigger 直接排除，不通过倍率表达。24 个月项固定，只对高收入官署（主要是路）形成二级上限，不承担区分档位的职责。
- 保底是绝对储备，不产生实际收入；余额低于保底时中央不补足。
- 历史只存原始月收入采样，不存滚动最大值；取当年及前两年的最大值，避免一次性尖峰永久抬高上限。

## 适用范围

角色作用域，适用于全部天朝官员，不区分文武、有地无地及官品：

- `has_treasury = yes`、`is_independent_ruler = no`、`top_liege` 为天朝独立君主、`exists = primary_title`。
- 排除皇帝本人、奉祠（`tca_fengci`）与致仕（`tca_retired`）。
- 按国库实际归属角色结算，每位官员每期最多一次；多头衔持有者按主头衔等级取保底。

## 年度结算

- 入口为 `yearly_global_pulse`（每年 1 月 1 日、无根）；全局年锁 `tca_treasury_reserve_processed_year` 防重复入口。免缴档的领域不进入结算范围。
- 顺序：清零各国年度累计 → 逐角色计算上限与应缴额 → 达到门槛才转账 → 更新历史（前年 ← 去年；去年 ← 当前月收入）→ 逐国发送皇帝汇总并清理。
- 历史变量挂 `primary_title`：`tca_treasury_reserve_income_last_year`、`tca_treasury_reserve_income_two_years_ago`。原生国库随头衔更换持有人而保留，换任继承历史。
- 上缴直接 `remove_treasury` 并从皇帝 `add_treasury` 同额，不经过转运使；不写任何 `monthly_income`，避免反馈进下一期收入。
- 通知：皇帝一条汇总（总额、笔数），实际缴款人各一条；仅 `is_ai = no`；使用原生右侧 feed 消息。

## 实现入口

- 法律组：`common/law_groups/tca_treasury_reserve_law_groups.txt`
- 三级法律：`common/laws/tca_treasury_reserve_laws.txt`
- 数值：`common/script_values/tca_treasury_reserve_values.txt`
- 触发条件：`common/scripted_triggers/tca_treasury_reserve_triggers.txt`
- 结算与通知：`common/scripted_effects/tca_treasury_reserve_effects.txt`
- 年度与开局钩子：`common/on_action/tca_treasury_reserve_on_actions.txt`
- 消息类型：`common/messages/tca_treasury_reserve_messages.txt`
- 本地化：`localization/simp_chinese/tca_treasury_reserve_l_simp_chinese.yml`、`localization/english/tca_treasury_reserve_l_english.yml`

## 原版依据与边界

- 本机参考为 CK3 1.20.1.2 Crozier。
- `treasury` 是人物作用域字段；原生国库概念说明国库随头衔更换持有人而保留，因此历史变量挂 `primary_title` 而不是人物。
- `monthly_character_treasury_variable_income` 为全部国库收入减封臣发展金支出，不是净余额；本制度不扣军费与其他支出，故不采用 `monthly_character_treasury_balance`。
- `yearly_global_pulse` 与 `on_game_start_after_lobby` 的同名追加登记于 `tools/upstream_overrides.json`。
- 新增原生用例 `tca_treasury_reserve_test.1` 覆盖法律四档、保底分档、三年取最大、门槛、排除项与年锁；自然年度脉冲由跨年用例间接执行但未做结果断言，消息显示另行验收。运行结果由本次运行记录维护，本页不写历史通过流水。

## 验证边界

- 直接调用结算效果只证明脚本取值、转账和历史更新；自然年度脉冲、AI 皇帝、实际消息显示、布局、多语言和保存重载需另行验收。
- 皇帝汇总与缴款人消息中的动态金额、千分位和消息过滤需实机检查。
- 本页不将单次运行写成长期通过结论；未执行或环境失效的项按[测试运行](../testing/README.md)的验收口径处理。

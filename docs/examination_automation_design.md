# 知贡举与自动会试／殿试设计

状态：脚本已实现；2026-10-21 最终审查修订科举间隔、防重入、近亲额外名额、乡试功绩与实际扣款，验证结果及边界见[实现文档](examination_automation.md#12-2026-10-21-最终审查修复)。

本设计把原版会试／殿试从“活动”改为“玩家皇帝专用的自动事件链”，保留原版的两级考试、录取标准、分数、及第标记和奖励逻辑；知贡举是触发自动链的宫廷职位。AI 皇帝不使用这条链，继续走原版活动。

历史术语说明：宋代省试即礼部／贡院试，游戏内对应“会试”；殿试仍由皇帝亲临。本文统一使用游戏术语“会试”“殿试”，不新增“省试”机制。

## 1. 范围

- 仅玩家皇帝、且持有 `title:h_china` 时启用。
- AI 皇帝不弹事件，不使用自动链；原版 `activity_imperial_examination` 照旧。
- 不做科场舞弊、贿赂、考官事件；第一版只做考试结算。
- 知贡举适配度不额外影响考试，只走宫廷职位自身的数值效果。
- 薪资使用原版同级宫廷职位公式：皇帝支付国库与威望，知贡举领取金币与威望，并显示原版薪资明细。
- 代为主持不降低皇帝收益。

## 2. 原版依据与约束

- 会试 host 必须是霸权级、天朝政府、有地、`government_allows = merit`；活动冷却 5 年。见原版 `imperial_examination.txt` 的 `is_shown`、`can_start_showing_failures_only`、`is_valid`。
- 考生入场只要求 `is_landed = no`、成年、非 host／examiner、未过殿试、非虔诚信徒／宦官、非雇佣兵／骑士团、符合性别法；没有“必须过乡试”的硬门槛。
- 没有乡试时，`imperial_examination_entry_value` 把分数除以 3，并在 UI 红字提示；这是惩罚，不是禁入。
- 原版考生池来自 `situation:dynastic_cycle` 的 participant groups（排除 `other_rulers`），随机抽取“规模上限 × 0.6”的人进入邀请名单；到场后再由 `imperial_examination_gather_entrants_effect` 筛成 `entrants`。
- 原版 `activity_invite_rule_player_family_opt_in_imperial_exam` 只在玩家有 `command_to_attend_flag` 时把近亲／远亲加入邀请名单，并给近亲 `guest_join_chance +5000`；没有 flag 时按普通规则处理。
- 原版 AI 主办：`ai_will_do = 100`，霸权档每 12 个月评估一次；受 5 年冷却、开局 5 年 AI 门槛和王朝周期催办影响。
- 原版会试：玩家分数 < 50 必落；AI 按末位配额淘汰，配额由录取标准决定；剩余前 10 名进殿试；进殿试者无条件获得 `passed_palace_exam`。
- 原版非前十 AI 补录条件：`is_ai = yes`、非低出身、近亲／远亲中没有玩家角色，才有 20% 概率补 `passed_palace_exam`。
- 原版会试侧重受王朝周期阶段限制：学识永远可选；军事仅 `stability_expansion`；管理仅 `stability_advancement`。非学识侧重对玩家额外收费。

## 3. 总体流程

```text
知贡举在任 + 自动任务开启
→ 启用任务时立即检查一次，此后每年复查：原版活动不在冷却、无自定义五年冷却
→ tca_exam.1「知贡举请开科」
    ├─ 亲自主持：跳转原版活动主办窗口，玩家自己开始
    ├─ 代为主持：小比／常科／大开三档规模 + 知贡举自动录取尺度 → 自动结算会试／殿试
    └─ 暂缓：不开科，无代价，下一年再弹
→ tca_exam.4「隐藏结算」
    ├─ 有考生：tca_exam.2「会试放榜」→ 有首名时 tca_exam.3「殿试传胪」
    └─ 无考生：tca_exam.5「本科无人应试」，结束
```

AI 皇帝不走此流程。

## 4. 知贡举宫廷职位

### 4.1 定义

- key：`tca_exam_commissioner_court_position`
- 名称：知贡举
- 上限：1
- 最低等级：empire
- 主技能：learning
- 背景：`gfx/interface/illustrations/event_scenes/tgp_examination_room.dds`
- 动画：`holding_scrolls`

### 4.2 显示

```text
is_shown = {
    is_independent_ruler = yes
    government_has_flag = government_is_celestial
    has_title = title:h_china
}

valid_position = {
    is_independent_ruler = yes
    government_has_flag = government_is_celestial
    has_title = title:h_china
}
```

只对中国霸权皇帝显示。

### 4.3 资格

```text
valid_character = {
    scope:employee = {
        is_adult = yes
        is_landed = no
        age >= 35
        NOT = { has_trait = eunuch }
        NOT = { has_trait = devoted }
        OR = {
            AND = {
                tgp_passed_metropolitan_examination = yes
                merit_level >= 4              # 六品及以上
            }
            AND = {
                has_trait = confucian_education
                has_trait_xp = {
                    trait = confucian_education
                    value >= trait_third_of_five_level_value   # 60
                }
            }
            learning >= 16
            merit_level >= 7              # 三品及以上
        }
    }
}
```

- 四条任职资格路径满足其一即可：
  1. 已过会试且六品及以上；
  2. 儒学教育特质经验达到 60；
  3. 学识 16 及以上；
  4. 未过会试但功绩三品及以上。
- 不限制 `is_courtier`，允许三省六部等无地官担任。
- 不限制 `has_any_court_position`，允许兼其他宫廷职位。
- 仍要求无地、成年、35 岁以上，避免有地官兼任。
- 现任知贡举作为 examiner 从考生池排除。

### 4.4 适配度

```text
aptitude = {
    value = 1
    add = { value = merit_level multiply = 3 max = 30 desc = court_position_merit_level }
    add = { value = learning multiply = 1.5 max = 45 desc = court_position_skill_learning }
    add = { value = stewardship multiply = 0.75 max = 20 desc = court_position_skill_stewardship }
    add = { value = martial multiply = 0.5 max = 15 desc = court_position_skill_martial }

    if = { limit = { has_trait = confucian_education } add = { value = "has_trait_xp(confucian_education)" floor = yes desc = court_position_confucian_education_trait } }
    if = { limit = { has_trait = erudite } add = 5 desc = court_position_erudite_trait }
    if = { limit = { has_trait = diligent } add = 5 desc = court_position_diligent_trait }
    if = { limit = { has_trait = patient } add = 5 desc = court_position_patient_trait }
    if = { limit = { has_trait = calm } add = 5 desc = court_position_calm_trait }

    add = court_position_aptitude_low_penalty_value
    add = general_aptitude_bonus
}
aptitude_level_breakpoints = { 20 40 60 80 }
```

学识为主，管理次之，军事再次；适配度只影响宫廷职位效果，不影响考试。

### 4.5 薪资与效果

使用原版同级宫廷职位（major）的薪资公式：

```text
salary = {
    treasury = { value = major_court_position_salary }
    prestige = { value = major_court_position_prestige_salary }
    round = no
}

received_salary = {
    gold = { value = major_court_position_salary }
    prestige = { value = major_court_position_prestige_salary }
    round = no
}
```

因此薪资会随领地规模、时代和皇帝身份缩放，并显示原版“基础俸禄／领地规模／时代／皇帝”悬浮明细；不再使用固定 4.00。

称职度加影响力：

```text
scaling_employer_modifiers = {
    terrible  = { monthly_influence = 0.1 }
    poor      = { monthly_influence = 0.15 }
    average   = { monthly_influence = 0.2 }
    good      = { monthly_influence = 0.25 }
    excellent = { monthly_influence = 0.3 }
}

base_employer_modifier = {
    monthly_influence = 0.2
}
```

合计约 +0.3–0.5 影响力/月；薪资之外没有额外的威望修正。

### 4.6 生命周期

- `on_court_position_received`：设 `tca_exam_commissioner = yes`。
- `on_court_position_revoked` / `invalidated` / `vacated`：清除该变量。
- 没有额外考试奖励；知贡举的收益只来自宫廷职位本身。

## 5. 两个任务

| 任务 | 效果 | AI |
|---|---|---|
| 知贡举·自动开科 | `on_start` 在 `title:h_china.holder` 上设 `tca_exam_automation = yes`，满足条件时两日后触发 `.1`；年度脉冲复查；`on_end` 清除 | `ai_will_do = 0` |
| 知贡举·常规 | `on_start` 清除 `tca_exam_automation`；不触发事件 | `ai_will_do = 100` |

- 两个任务的薪资、`scaling_employer_modifiers` 完全相同；只有 `on_start`／`on_end` 变量和 AI 权重不同。
- AI 只用常规任务，不会触发自动链。
- 玩家切换任务时，自动任务 `on_end` 清除自动任务变量；已打开的事件由 `tca_exam_prompt_open` 控制。代办至三日后结算期间另以 `tca_exam_pending` 防重，任务切换不清除该标记；结算结束才清理，迟到的重复结算不执行。

自动任务的首次检查由任务 `on_start` 执行，之后由 `yearly_playable_pulse` 追加的 `tca_exam_yearly_pulse` 复查，避免无地大臣持有者的宫廷任务不 tick。两者复用同一条件，任务启动直接作用于中国皇帝：

```text
# 任务启动；根作用域是知贡举本人，不依赖其 liege 作用域
title:h_china.holder ?= {
    set_variable = tca_exam_automation
    if = {
        limit = { tca_exam_can_prompt_trigger = yes }
        trigger_event = { id = tca_exam.1 days = 2 }
    }
}

# 年度复查
tca_exam_yearly_pulse = {
    trigger = { tca_exam_can_prompt_trigger = yes }
    effect = { trigger_event = tca_exam.1 }
}
```

## 6. 考生池

### 6.1 来源

- 只从中国王朝周期 `situation:dynastic_cycle` 的 participant groups 取，排除 `other_rulers`；参照原版。
- 按规模随机抽取 150／300／600 人（对应原版 250／500／1000 × 0.6）。
- 有 `command_to_attend_flag` 时，符合优先条件的近亲先从普通抽样池排除，再追加至结果；不占 150／300／600 个普通名额。

### 6.2 资格

```text
is_landed = no
is_adult = yes
tgp_gender_can_be_exam_entrant_trigger = yes
NOT = { this = scope:host }
NOT = { has_court_position = tca_exam_commissioner_court_position }
NOT = { has_character_flag = passed_palace_exam }
NOT = { has_trait = devoted }
NOT = { has_trait = eunuch }
NOT = { tca_exam_is_official_trigger = yes }
```

- 不要求 `passed_provincial_exam`；没有乡试者仍可入池，分数 ÷3。
- 三省六部、mod 提刑／通判、councillor 等官员不能当考生；但可以担任知贡举。
- 无地冒险者可以考。
- 只有家族头衔、没有官职的可以考。
- 普通廷臣、其他宫廷职位持有者可以考；只排除现任知贡举。
- 玩家近亲优先入池只针对已过乡试者；未过乡试的近亲仍可能被正常随机抽到，分数 ÷3。
- 官员、有地者、已过殿试者、信徒／宦官等硬条件仍然排除。

### 6.3 官员排除

```text
tca_exam_is_official_trigger = {
    OR = {
        is_councillor = yes
        tca_is_landless_official_trigger = yes
        AND = {
            is_landless_ruler = yes
            NOT = { government_has_flag = government_is_landless_adventurer }
            NOT = { primary_title = { is_noble_family_title = yes } }
        }
    }
}
```

- 三省六部、mod 提刑／通判、councillor：排除。
- 无地冒险者：放行。
- 家族头衔、没有官职：放行。
- 普通宫廷职位：放行；只额外排除现任知贡举。

### 6.4 近亲额外名额

玩家有 `command_to_attend_flag` 时：

- `every_close_family_member` 中满足考生资格且 `tgp_passed_provincial_examination = yes` 的人，直接加入考生池，不占规模名额；
- 没有乡试的近亲不优先，但仍可能被正常随机抽到；
- 官员、有地者、已过殿试者仍排除。

## 7. 分数与通过

### 7.1 分数

复刻原版 `imperial_examination_entry_value`：

| 分项 | 数值 |
|---|---|
| 功绩 | ≥7 +20；≥5 +15；≥3 +9；≥1 +6 |
| 儒学经验 | 100 +20；80 +15；60 +12；40 +9；20 +6；有特质 +3 |
| 侧重技能 | 学识／军事／管理，加对应技能值 |
| 教育特质 | 1–5 级 +3／6／9／12／15 |
| 相关 lifestyle 特质 | 每项 +3 |
| 家族抱负 | `examination_success_bonus` +10 |
| 住宅建筑 | 照原版 archive 倍率 |
| 未过乡试 | ÷3 |
| 不会 host 语言 | ÷5 |
| 临场发挥 | +0–10 随机 |

- 会试侧重由知贡举自动选择，不增加玩家选择。
- 任意时刻最多两个：学识永远可选；军事仅 `stability_expansion`；管理仅 `stability_advancement`。
- 自动选择：当前阶段可选的军事／管理 75%，学识 25%；不可选时学识 100%。
- 选中军事／管理时，按原版扣对应额外费用；学识不额外收费。

### 7.2 通过

- 玩家不参加考试，不设 50 分线；所有考生均为 AI。
- AI 按末位配额淘汰：

| 录取标准 | AI 落榜比例 |
|---|---|
| 宽取（低） | 10% |
| 依例（中） | 15% |
| 严取（高） | 30% |
| 极严 | 50% |

- 剩余考生按分数取前 10 名进殿试；进殿试者无条件获得 `passed_palace_exam`。
- 其余会试及第者获得 `passed_metropolitan_exam`。
- 非前十 AI，非低出身、近亲／远亲中没有玩家角色，20% 概率补 `passed_palace_exam`；与玩家亲属有关者排除，照原版。
- 已过殿试不能重考；已过会试可以重考冲殿试。
- 落第者加 `failed_imperial_examination` 和记忆；无及第奖励。

## 8. 玩家选择与事件

### 8.1 玩家选择

只有三个方向：

1. **亲自主持会试**：事件普通选项，使用 `open_view_data` 跳转原版活动主办窗口，选中后事件关闭；自动链不执行。
2. **命知贡举代为主持**：玩家选择小比／常科／大开三档规模。
3. **暂缓**：无代价，下一年再弹。

侧重、录取标准、殿试主持不再让玩家选；录取标准由知贡举按原版权重自动决定。

### 8.2 `tca_exam.1` 请开科举

- 触发：自动任务开启、到期、无原版冷却、无自定义冷却、不在活动、无已打开提示。
- 正文采用 2026-10-21 用户定稿的开科奏请叙事；代办 Tooltip 显示本届侧重和合格候选池人数，规模费用保留原生扣款悬浮。
- 普通选项：亲自主持会试。
  - 使用普通选项的 `open_view_data`，以 `view = activity_list_detail_host_window`、`data = activity_type:activity_imperial_examination`、`player = root` 打开原版主办窗口。
  - 玩家开始活动后，自动链跳过；事件关闭。
- 选项：
  - 命知贡举代为主持·小比（150 人，exclusive 费用）
  - 命知贡举代为主持·常科（300 人，restricted 费用）
  - 命知贡举代为主持·大开（600 人，open 费用）
  - 暂缓
- 效果：
  - 代为主持：设规模、知贡举按原版权重决定录取标准、扣对应规模费用、触发隐藏 `.4` 结算；等级随机与扣费包在 `hidden_effect` 内，避免选项悬浮展开“X%概率”。
  - 暂缓：清提示标记，无费用，下一年再弹。
  - 0 考生时仍可开科，照扣费用、发放皇帝主持收益并设置五年冷却；结算后转入 `.5`，不进入放榜与传胪。

### 8.3 `tca_exam.2` 会试放榜

- 无选择。
- 显示取中人数、前十名、落榜人数。
- 使用当前放榜叙事，说明等待皇帝批准张榜并筹备殿试传胪。
- 有首名时触发 `.3`；无人取中时结束，避免无状元的传胪奖励。

### 8.4 `tca_exam.3` 殿试传胪

- 一个“传胪”选项，无分支。
- 状元、榜眼、探花各占一条带项目符号的独立行；前十名已在会试放榜展示，不在传胪中重复。
- 选项执行原版 `imperial_examination.9000` “祝贺第一名”的 B 档效果：皇帝获得 `medium_legitimacy_gain`，状元 AI 获得 2000 功绩。
- 榜眼、探花没有额外数值奖励，和原版一致。
- 其余考试奖励已在隐藏事件 `.4` 中结算。

### 8.5 `tca_exam.5` 本科无人应试

- 实际考生数为 0 时通知皇帝，没有后续事件或额外奖励。
- 事件右侧人物依次为：`.1` 知贡举、`.2` 会试第一名、`.3` 殿试第一名；`.5` 由知贡举奏报。人物不存在时隐藏。当前自动链会试与殿试第一名为同一人。
- 保留已结算的开科费用、主持收益和五年冷却；不显示旧名次，不发状元及传胪奖励。
- 原版 `imperial_examination.txt` 在正式阶段检查的是 `has_attending_activity_guests`，无人到场走 `invalidation_nobody_present_effect`；没有单独按合格考生数取消的分支，主持奖励也不检查考生人数。自动链没有旅行和到场过程，因此只增加零考生结果通知，不模拟无人赴会取消。这是脚本对照结论，原版零考生完整流程未经实机复现。

亲自主持时没有自定义 `.2` / `.3` / `.5`，走原版活动。

## 9. 费用与奖励

- 花皇帝的钱，费用按原版玩家亲自主持、所选规模、当前侧重组合计算；不检查国库，可为负。
- 开封皇城和考试院折扣对三档规模都生效；`tca_exam.1` 立即效果把三档费用存成变量，选项用 `show_as_tooltip`＋`remove_treasury` 生成原生扣款悬浮，实际扣费使用同一变量。
- 皇帝主持影响力按规模 ×1／×2／×4；代为主持不降低皇帝收益，其余 host 奖励照原版。
- 考生奖励照原版：及第标记、修正、功绩、影响力、记忆；绕过乡试的非低出身及第者另补原版乡试功绩，低出身不补。
- 家族结果逐人通知考生近亲，包含家主；头像和双语正文均引用实际考生。自动链不复刻原版家主汇总，改由同一逐人通知覆盖，避免家主漏收结果。
- 知贡举没有额外考试奖励；适配度不影响考试。
- 由于原版奖励效果是 activity-scoped，不能直接调用，需要在新效果中按原版数值复刻。

## 10. 五年冷却与活动覆盖

### 10.1 自定义冷却

- 在 `title:h_china` 上设置 `tca_exam_cooldown`，持续 5 年。
- 代为主持结算完成后设置；不主动清除，5 年自然过期。同时将原版 `years_since_imperial_examination` 重置为 0，使王朝周期正确记录本次开科。
- 玩家退位成 AI 后变量保留，但 AI 不受影响。
- 非中国霸权不处理；会试只属于 `h_china`。

事件触发同时检查：

```text
NOT = { is_activity_type_on_cooldown = activity_imperial_examination }
NOT = { title:h_china = { has_variable = tca_exam_cooldown } }
```

### 10.2 覆盖 `can_start_showing_failures_only`

整份重定义 `activity_imperial_examination`，在 `can_start_showing_failures_only` 中正常加入：

```text
custom_tooltip = {
    text = tca_exam_cooldown_tt
    OR = {
        is_ai = yes
        NOT = { has_title = title:h_china }
        NOT = { title:h_china = { has_variable = tca_exam_cooldown } }
    }
}
```

- 玩家冷却中被挡并显示 tooltip；
- AI 不受影响；
- 其余部分逐字保留原版；
- 登记 `tools/upstream_overrides.json`，维护基线，运行 `python3 tools/check_upstream_overrides.py`；
- 与半自动科举等同样覆写该活动文件的模组冲突。

## 11. AI 行为

- AI 皇帝不弹事件，不使用自动链；继续走原版活动。
- AI 知贡举只用常规任务（`ai_will_do = 100`）；自动任务 `ai_will_do = 0`。
- AI 宫廷职位可以正常雇佣知贡举；若引擎不允许无地 vassal 担任，需要实机调整。
- AI 考生的末位配额、前 10、20% 殿试补录照原版；玩家亲属排除 20% 照原版。

## 12. 与原版的差异

| 项目 | 原版 | 本设计 |
|---|---|---|
| 会试／殿试 | 活动，有场景、旅行、邀请、考官、舞弊 | 无活动，事件链结算 |
| 玩家选择 | 活动面板多项设置 | 亲自主持／代为主持小比·常科·大开／暂缓；录取尺度由知贡举决定 |
| 考生池 | 王朝周期参与者随机抽 60% | 同来源，按规模 150／300／600 人；近亲额外 |
| 官员 | 无地官可考 | 三省六部、提刑／通判、councillor 排除；可当知贡举 |
| 乡试 | 无硬门槛，÷3 | 同 |
| 侧重 | host 选，受局势限制 | 知贡举自动选，受局势限制，75/25 |
| 知贡举 | 无此职位 | 宫廷职位，触发自动链 |
| 冷却 | 活动 5 年 | 原版冷却 + 自定义 5 年 title 变量 |
| 舞弊 | 有 | 第一版不做 |

## 13. 实现文件

实现文件（已接入）：

- `common/court_positions/types/tca_exam_court_positions.txt`
- `common/court_positions/tasks/tca_exam_tasks.txt`
- `common/scripted_triggers/tca_exam_triggers.txt`
- `common/scripted_effects/tca_exam_effects.txt`
- `common/script_values/tca_exam_values.txt`
- `common/on_action/tca_exam_on_actions.txt`（如需要）
- `events/tca_exam_events.txt`
- `common/activities/activity_types/zz_tca_imperial_examination.txt`（整份覆盖）
- `localization/simp_chinese/tca_exam_l_simp_chinese.yml`
- `localization/english/tca_exam_l_english.yml`
- `events/tca_exam_test_events.txt`
- `tools/upstream_overrides.json` 与对应 baseline

## 14. 测试与验收

至少覆盖：

- 知贡举显示、雇佣、解雇、资格、适配度、薪资、两个任务切换；
- 自动任务只对玩家触发；AI 皇帝不触发；
- 原版冷却中不弹；自定义 5 年冷却不弹；两者都过期后弹；
- 亲自主持选项跳转活动窗口；开始活动后自动链跳过；
- 代为主持按知贡举决定的录取尺度计算配额；前 10；20% AI 补录；玩家亲属排除；
- 官员排除、冒险者/家族头衔放行、廷臣/宫廷职位放行、现任知贡举排除；
- 近亲优先只含已过乡试；无乡试正常随机 ÷3；
- 三档规模 + 近亲额外；始终开放；0 考生；国库负数；
- 费用/奖励与原版一致；知贡举无额外奖励；
- 五年变量存 title、5 年过期、AI 不受影响；
- `can_start_showing_failures_only` 覆盖后原版逻辑不变；
- 保存重载、玩家继承、AI 继承、事件提示不重复；
- `python3 tools/check_upstream_overrides.py`；
- `python3 -m unittest discover -s tools -p 'test_*.py'`；
- CLI 全组回归、`tools/check_test_run.py`、同次 `error.log`。

区分静态检查、引擎加载、游戏内断言与界面验收；未运行项明确写“待引擎验证”。

## 15. 风险与待验证

- 三省六部是无地 vassal，宫廷职位是否允许其担任，需实机验证；不允许则改无地官职方案。
- 亲自主持选项跳转活动主办窗口需验证可用性、事件关闭与自动链跳过。
- 整份活动覆写与其他会试模组冲突；游戏更新后需同步基线。
- 原版 activity-scoped 奖励需复刻，存在数值/标记遗漏风险。
- 0 考生、国库负数、流拍费用处理需平衡复核。
- 自定义 5 年变量在玩家继承、AI 接管、保存重载下的行为需测试。
- 20% 殿试补录与玩家亲属判定需逐条对照原版。

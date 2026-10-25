# 公爵级文官称号按资序分等（评估稿）

状态：**未采用，若干选项待决定**。本页记录方案、依据、风险与实现草案，不代表已实现或已批准。史实判断见[转运司副贰：转运副使与转运判官](../../research/song/transport_commission/README.md)。

## 待决问题

公爵级文官现统一显示"转运副使"。是否改为按功绩等级分等：资浅者称"转运判官"，资深者称"转运副使"；并在玩家官称变化时给出提示。

实现分两层，可以分开决定：

1. **名称**：无状态，所有角色按当前资序显示。AI 也生效，不需要存档状态。
2. **事件**：只有对玩家才有意义。AI 看不到事件，也不该为它维护状态；因此事件层全部以 `is_ai = no` 收口。

同一待办里的"玩家改的时候有事件"有两种读法：

- **官称随资序变化时的事件**——若采用分等，这是配套项，见"事件载体"。
- **玩家切换名称法律时的事件**——不建议做，见"不采用的部分"。

## 现状与实现路径

- 宋制地方称号由 `common/flavorization/tca_song_official_names.txt` 的 `tca_song_duchy_holder_male/female` 匹配，文本为 `$tca_name_duchy_civil$`（"转运副使"）。该条目要求 `flag = tca_song_local_names`，而标记只在 `government_is_celestial`、`is_independent_ruler = no`、`is_landed = yes` 等条件成立时添加（`common/scripted_effects/tca_court_system_effects.txt`）。
- 提刑持有者按设计为无地（`is_landed = no`），不满足该标记的添加条件；其称号走 `common/flavorization/tca_judicial_holder_flavorization.txt` 的优先级 28 桥接，由 `TCAJudicialHolderTitle` 显示"提点刑狱公事"，其余回退原版。
- 因便名称下同样走桥接回退原版，不显示"转运副使"。
- 原版公爵级任命的功绩门槛为 3（七品），见[原版任命](../appointment/vanilla.md)。

因此本项只影响宋制、有地、文官契约的公爵级持有人；不影响提刑、军制公爵（兵马钤辖）、因便名称或伯爵以下。

## 史实依据

《宋史·职官志》把转运司长官序列写作"都转运使、转运使、副使、判官"，并称副使、判官"皆随资之浅深称焉"；《文献通考》记判官始置、副使置罢与运判命词礼遇低于使副。治平前后又有夔路运判张诜改陕西运副、夔州运判张林宗移梓州提刑、江东运判谢景温迁提点江西刑狱等迁转链。

结论：以"资"区分"判官—副使"有直接文本依据，但它是**以资序择差遣**，不是同一职位的两个等级。游戏用同一头衔显示两种官称，属于对这一原则的近似，不是复原原制。

三点限制必须保留：

- "随资浅深"一段在南渡后叙述内，治平三年没有同款成文令可引；
- 判官与提刑分属不同监司，运判迁提刑是迁转次序，不是同一司内上下级；
- 南宋运判可单独掌一路漕司，"判官低于副使"不能泛化。

## 沉浸性分析

### 收益

1. **让"品"可读。** 功绩等级目前主要是授职门槛与排序键，玩家很难从世界里读出它的意义。让官称随资序变化，等于把抽象等级翻译成宋制官称，和"宋式职名"本来的目的同向。
2. **频次天然合适。** [官职任命](../appointment/README.md)模块的功绩升品设计把品级做成核定后锁定的离散身份，一年最多升一次；官称变化因此是低频、可记住的里程碑，适合配事件。现状（原版自动升降）则可能频繁抖动，反而不适合。
3. **补全监司阶梯。** 公爵级内可形成"运判（资浅）—提刑（另司）—运副（资深）"的读法，与治平前后的实际迁转方向一致；也能解释"上面没有正使的副贰"：副使本身就是可掌印的资深差遣，不必以正使在位为前提。
4. **事件有现成史实外壳。** 宋人迁官有告身、制词；原地升迁可用"就迁""就改"一类现成说法，不必假装改授新职。

### 代价与风险

1. **静默改名比不精确更伤沉浸。** 头衔对象没变、任命界面没变，只有称呼变了；没有提示时，玩家更可能读成显示错误或掉级。提示不是装饰，是这个方案能否成立的前提。
2. **抖动与"无名贬官"。** 原生 `merit_level` 会因负修正下降（见[官职任命](../appointment/README.md)模块的接口验证记录）。若直接按实时值判名，一次负修正就会让"转运副使"无声变成"转运判官"。必须绑核定品或"已达最高等级"，并且只在提交/初始化时改，不随显示时求值反复横跳。
3. **同级内的序位错觉。** 提刑也是公爵级，且资浅运判名义上低于提刑。玩家若把三级放在一起比较，会发现同为公爵却官称高下不一；这可以用"不同监司"解释，但界面上不会自动解释。
4. **地理近似没有解决。** 公爵级本身是路以下的区划，而运判、运副都是路级转运司官。分等只是把"一个近似"变成"两个近似"，不修正层级错位。
5. **与既有原则的张力。** 官职任命模块的功绩升品设计明确"不把头衔划成各品专用职位"。本条不改任命资格，只在称号上按品分等，但玩家容易读成"某品=某职"，需要在文案和文档里说清。
6. **实现边界。** 动态称号涉及显示刷新与缓存、存档重载、外部官名模组接管后的清理，以及简中／英文双语。现有 county 称号已用同类动态本地化，可复用做法，但不能据此认定公爵条目也一定按预期刷新。
7. **施行瞬间的批量改名。** 启用当天，所有资浅的公爵级文官会同时从"转运副使"变成"转运判官"。这既不能逐人发事件，也不能当作降官处理；需要像现有法律迁移那样，先静默写入基线档位，只对之后的变化提示。

## 方案比较

| 方案 | 内容 | 判断 |
| --- | --- | --- |
| A 维持现状 | 公爵级文官一律"转运副使" | 最稳；放弃把资序可视化 |
| B 按核定品分等 | 3＝转运判官，≥4＝转运副使 | 史实依据最直接、条件单一 |
| C 按有无正使 | 上有王国级转运使称副使，无则称判官 | 能解决"无正使的副贰"，但史实上副使、判官都可掌印，依据弱于资序 |
| D 组合 | 有正使且资深称副使，其余判官 | 条件叠加，玩家难理解，不建议首版 |

B 与 C 的取舍、以及 B 的阈值（3／≥4 还是 3–4／≥5）均待决定，见"待决定"。

## 阈值与文案

- 候选阈值一：核定品 3（七品）为"转运判官"，≥4（六品及以上）为"转运副使"。原版公爵门槛正好是 3，因此新到任者多为判官，资深者才是副使，符合"判官为入监司之阶"的读法。
- 候选阈值二：3–4 为"转运判官"，≥5 为"转运副使"。副使更稀有，更接近北宋"副使不常置"的印象，但多数公爵级人物一生都不会换称。
- 简中：转运判官／转运副使。英文：Transport Judge／Deputy Transport Commissioner。宋代的判官在这里是监司副贰官称，与司法审判无关，英文用 "Judge" 是惯例译法；若担心误解，可用 "Assistant Transport Commissioner"。

## 实现草案

### 名称：无状态，所有角色生效

在 `common/customizable_localization/tca_song_official_names.txt` 增加动态条目，由 flavorization 的本地化键调用：

```txt
TCASongDuchyHolder = {
    type = character
    text = {
        trigger = { tca_song_duchy_senior_trigger = yes }
        localization_key = tca_name_duchy_civil       # 转运副使
    }
    text = {
        fallback = yes
        localization_key = tca_name_duchy_civil_low   # 转运判官
    }
}
```

`tca_song_duchy_holder_male/female` 的文本由 `$tca_name_duchy_civil$` 改为 `[CHARACTER.Custom('TCASongDuchyHolder')]`，与县级 `TCASongCountyHolder` 同一写法。提刑走 28 优先级桥接、军制走 301，不受影响。

阈值与数据源集中在一个 trigger，功绩正式接入后只改这里：

```txt
# 角色作用域；公爵级文官称号是否取资深一档（资序 4／六品以上）。
# 功绩正式接入后以核定品为准；未接入时退回原生 merit_level。
tca_song_duchy_senior_trigger = {
    if = {
        limit = { has_variable = tca_merit_approved_level }
        var:tca_merit_approved_level >= 4
    }
    else = { merit_level >= 4 }
}
```

`merit_level` 在 custom loc 里可读有原版先例：`10_tgp_custom_loc.txt` 的 `GetMeritRank` 就是 `type = character` + `merit_level = 9/8/...`。该条只证明接口存在，不证明本模组的显示刷新时机。

### 显示条件

事件必须只在"玩家确实显示这个称号"时触发，因此镜像 flavorization 条件：

```txt
# 角色作用域；镜像 tca_song_duchy_holder_* 的显示条件。
tca_song_duchy_civil_holder_trigger = {
    government_has_flag = government_is_celestial
    is_independent_ruler = no
    is_landed = yes
    NOT = { vassal_contract_has_flag = celestial_province_protectorate }
    NOT = { vassal_contract_has_flag = celestial_province_military }
    primary_title = { tier = duchy }
    tca_uses_song_local_names_trigger = yes
}
```

`primary_title` 与 flavorization 的"命名头衔"在配偶头衔更高时可能不一致，见"待验证"。

### 事件载体

原版已经在功绩升级时给玩家发过通知，这是本设计必须避让的既有节拍：

- `common/on_action/character_levels.txt:291` 的 `on_merit_level_gain` 先发 `msg_character_level_increase` toast，再对 `is_ai = no` 的玩家延迟 2–10 天排 `tgp_china_career.0010`（`events/dlc/tgp/tgp_china_career_events.txt:92`），带 30 天冷却。
- `tgp_china_career.0010` 按等级给不同描述（2 级提示可任公爵、5 级王国、7 级帝国、最高级另说），选项是拿 10 年的 `tgp_higher_ambitions_modifier` 或减压；1 级时另有转文／武官路线选项。

因此本模组不覆盖、不取消它，也不在同一时刻再弹一个同类弹窗；把"就迁"做成**第二个节拍**：升级当下只改名称，30–60 天后再以"告身至"的形式提示。这既避开叠弹，也符合告身递送需要时间的史实。

替代形态（均待决定，见"待决定"）：

- 即时事件：升级当下就弹，会和原版升级事件相邻，短期两个弹窗。
- toast：不弹窗，只进通知栏，最轻但仪式感弱。
- 覆盖 `tgp_china_career.0010`：一个弹窗解决，但要新增原版覆盖并维护基线，不推荐。

### 玩家专属状态

`on_merit_level_gain` 触发时 `merit_level` 已是新值，无法直接得知旧档；多级跳升也只回调一次，所以用 0/1 变量记录基线。AI 不写变量、不排事件。

```txt
on_merit_level_gain = { on_actions = { tca_song_duchy_grade_gain } }
on_title_gain = { on_actions = { tca_song_duchy_grade_resync } }
quarterly_playable_pulse = { on_actions = { tca_song_duchy_grade_resync } }

# 玩家专属：换任／就任时静默写基线，不补发历史事件。
tca_song_duchy_grade_resync = {
    trigger = { is_ai = no tca_song_duchy_civil_holder_trigger = yes }
    effect = { tca_song_duchy_grade_sync_effect = yes }
}

# 玩家专属：功绩升级时比较档位，跨门槛才排事件。
tca_song_duchy_grade_gain = {
    trigger = { is_ai = no tca_song_duchy_civil_holder_trigger = yes }
    effect = {
        if = {
            limit = { NOT = { has_variable = tca_song_duchy_grade } }
            tca_song_duchy_grade_sync_effect = yes
        }
        else_if = {
            limit = {
                tca_song_duchy_senior_trigger = yes
                var:tca_song_duchy_grade < 1
            }
            set_variable = { name = tca_song_duchy_grade value = 1 }
            trigger_event = { id = tca_court_system.2 days = { 30 60 } }
        }
    }
}
```

`tca_song_duchy_grade_sync_effect` 只做一件事：按当前档位写入 0 或 1。

### 事件体

```txt
tca_court_system.2 = {
    type = character_event
    title = tca_court_system.2.t
    desc = tca_court_system.2.desc
    theme = merit
    left_portrait = { character = root animation = reading }
    trigger = {
        is_ai = no
        tca_song_duchy_civil_holder_trigger = yes
        tca_song_duchy_senior_trigger = yes
    }
    option = { name = tca_court_system.2.a }
}
```

`_events.info` 说明 queued/instant 事件会检查 trigger，失败时走 `on_trigger_fail`。因此延迟事件在丢官、换因便、掉回 3 时自然不弹，不需要额外清理。

文案草案（待定）：

- 标题：就迁
- 正文：朝廷以资序进尔为$tca_name_duchy_civil$，仍领旧任，不别除人。
- 选项：领命

### 时序

```txt
merit 3→4
  ├─ 名称立即变（custom loc，无状态）
  ├─ on_merit_level_gain：var 0→1，排 tca_court_system.2（30–60 天后）
  ├─ 2–10 天：原版 tgp_china_career.0010
  └─ 30–60 天：本模组"就迁"告身事件（条件复查）
```

### 与当前未提交功绩改动的关系

- 文件不重叠：本方案改的 `tca_song_official_names.txt`、`tca_court_system_triggers.txt`、`tca_court_system_effects.txt`、`tca_court_system_events.txt`、court 本地化与模块测试登记，都不在当前改动清单内。
- `common/on_action/` 下现有三个未跟踪的 merit probe 文件已分别追加 `on_merit_level_gain`、`on_title_gain`。本方案新建 `tca_court_system_on_actions.txt`，文件名不撞；同名 on_action 的追加合并需要与探针的根 `trigger` 一起验证。
- `tca_merit_approved_level` 是功绩设计中的计划变量，现在不存在；trigger 用 `has_variable` 保护，读不到时退回 `merit_level`。
- 本分支从 HEAD 切出，不含主工作区未提交改动；因文件不重叠，功绩改动提交后 rebase 应无冲突，只需人工确认 on_action 合并结果。

### 文件清单

| 文件 | 改动 |
| --- | --- |
| `common/customizable_localization/tca_song_official_names.txt` | 新增 `TCASongDuchyHolder` |
| `common/scripted_triggers/tca_court_system_triggers.txt` | 新增 `tca_song_duchy_senior_trigger`、`tca_song_duchy_civil_holder_trigger` |
| `common/scripted_effects/tca_court_system_effects.txt` | 新增 `tca_song_duchy_grade_sync_effect` |
| `common/on_action/tca_court_system_on_actions.txt` | 新建：三个钩子与两个 action |
| `events/tca_court_system_events.txt` | 新增 `tca_court_system.2` |
| `localization/{simp_chinese,english}/tca_court_system_l_*.yml` | `tca_name_duchy_civil_low`、holder 改动态、事件三条 |
| `docs/court/README.md`、本页 | 状态由评估改为实现说明 |
| court 模块测试登记与 `events/tests/` | 断言 trigger 与变量迁移；玩家分支另作人工验收 |

## 待决定

1. **实现时机**：现在落（名称先读 `merit_level`，trigger 预留核定品分支）／等功绩正式接入（在授品提交事务里比较 source/target，事件最精确）／先只做名称。
2. **事件形态**：延迟 30–60 天的告身事件／即时事件／toast。
3. **阈值**：3／≥4，还是 3–4／≥5。
4. **方案取舍**：B 与 C 是否并存，或只做 B。

## 不采用的部分

玩家切换名称法律（宋制↔因便）时**不建议**加事件：法律切换本身在界面上立即可见，逐人发事件会刷屏，也不符合"玩家文本只写理解选项和作出决定需要的信息"。若确实需要反馈，一次性提示即可，不做逐角色事件。

## 实施顺序

若采用分等，建议与[官职任命](../appointment/README.md)模块的功绩升品正式接入同步，或至少让 trigger 同时兼容核定品与原生 `merit_level`：

- 现在 `merit_level` 仍由原版自动升降，分等会抖动，事件也会误报；
- 正式接入后有核定品作为稳定真值，称号与事件才有可靠触发点；
- 若先行，只能用"已达最高等级"作代理，并明确标注为临时口径。

## 待验证

- 同名 on_action 在多个文件中追加时，`trigger` 与 `on_actions` 的合并行为；特别是与 merit probe 文件的根 `trigger` 共存时，本模组 hook 是否被一并抑制。
- `customizable_localization` 的角色条目读取 `merit_level`（或核定品变量）后，在人物面板、头衔界面、封臣列表中的求值时机与缓存行为。
- 公爵称号从静态键改为动态本地化后，与提刑桥接、军制条目、因便回退的优先级是否仍正确。
- 延迟事件的 trigger 复查与 `on_trigger_fail` 实际行为。
- 保存重载、外部官名模组接管与移除后的称号残留。
- 实际功绩分布：分等后判官／副使各占多少，是否需要在测试局统计后再定阈值。
- 配偶头衔高于本人时，"命名头衔"可能不是自己的公爵领；当前方案只按 `primary_title` 判断。
- 玩家分支在观察者测试框架中跑不到 `is_ai = no`，需专用 debug 局人工验收。

## 维护入口

- 称号与法律：[中央、地方官名](README.md)、`common/flavorization/tca_song_official_names.txt`、`common/customizable_localization/`。
- 官名标记维护：`common/scripted_effects/tca_court_system_effects.txt`。
- 史实依据：[转运司副贰](../../research/song/transport_commission/README.md)。

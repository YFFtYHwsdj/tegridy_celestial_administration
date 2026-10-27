# 功绩来源与收入模型

本组修正旧生涯模型“每人终身固定、跨品级不变、均值720/年”的增长假设。当前功绩机制与参数仍由[数学模型](../../../docs/appointment/merit_model.md)维护，本页维护收入来源、量纲、离散奖励与离线输入边界，不修改正式游戏。

以下原版路径均相对本机安装的`game/`目录，核查版本为CK3 1.20.1.2。脚本可证明条目、条件和系数存在；它不自动证明全国实际拥有比例、事件频率或引擎结算公式已运行验证。模组来源链接指向库内正式对象。

## 替换什么假设

旧模型让18岁待阙新人、低级地方官及中央高官抽取同一均值60/月的个人增长率，并在此后终身沿用。它既可能高估待阙者，也可能低估大税基或大兵池官员，不能预设修正收入后一定补足最高带。

新模型使用显式收入账本，至少区分实际职位/契约、最高头衔层级、向领主实缴税额、头衔兵士基础招募价值、官署实际拨款、个人固定月收入、月倍率和离散奖惩。每次任免及相关状态改变后重新计算；功绩品级本身不直接创造收入。失职取消职务贡献，已拥有的庄园、师门、特长等个人来源按其各自条件保留。

`base_modifier`为空（原版`common/modifiers/00_basic_modifiers.txt`），天朝政府的`character_modifier`也没有普遍`monthly_merit`（`common/governments/00_government_types.txt`，`celestial_government`）。没有脚本依据支持“所有官员天然60/月”；也不能凭此断言引擎隐藏基础值已经验证为零。未提供的个人固定来源在离线输入中显式记零，并保留这项边界。

## 持续收入来源

### 地方契约与中央大臣

原版`common/subject_contracts/contracts/celestial.txt`：

- `celestial_province_standard`：向领主实缴税额系数0.8（65行）。
- `celestial_province_industrial`：税额系数1.2（152行）。
- `celestial_province_metropolitan`：税额系数2.4（290行）；实际条件含有地、王级及以上、直属霸主及都会数量上限等，不能只按品级授予。
- `celestial_province_military`：头衔兵士价值系数0.024（447行）。
- `celestial_province_protectorate`：头衔兵士价值系数0.032（590行）；同样受真实契约与资格条件限制。
- `celestial_minister_civil`及`celestial_minister_military`：固定20/月（671、701行）。按真实大臣身份和相应义务生效，不能给所有帝级地方官套用。

省类型在同一个义务树内择一，不能把五类系数相加。中央义务属于另一树；显示与有效条件不等于所有契约残留组合均已验证。收入账本必须明确当前角色、有效契约和贡献基数，不能默认每人同时拿地方、中央及模组官署全部收益。文件中没有单独的`celestial_county`固定收入项；县级适用何种省契约仍应按真实`main_administrative_tier`与`min_title_maa_tier`上下文处理。

### 量纲与乘区

原版`localization/english/modifiers/modifiers_l_english.yml`的`MOD_MONTHLY_MERIT_PER_LIEGE_TAX`说明基数为向领主实缴的总税收；`MOD_MONTHLY_MERIT_PER_TITLE_MAA_VALUE`说明兵池基数为头衔兵士基础招募价值。后者不是兵员数或月维护费。

个人国库收入不等于实缴税额。`celestial_government.top_liege_character_modifier`中的`monthly_treasury_from_vassals = 0.95`描述国库路径，不能直接再乘进Merit税额项；离线模型接收已经定义清楚的实缴税额，避免重复换算。

[经费契约说明](../../../docs/office_funding/contracts.md)维护既有`CalcMonthlyMeritBalance`静态核查结论：基础月功绩乘区与税收贡献项分开。模组探针注释记录月倍率下限为−1。本页不将此扩展为税收倍率、兵池倍率及全部组合的专项运行验收；离线模型应逐项列账、明确所采用的乘区，不把所有来源统一乘一个个人增益。

### 头衔、宫廷与师门

- 原版`common/modifiers/00_basic_modifiers.txt`的`king_modifier`有月功绩倍率+0.5（93行），`emperor_modifier`为+1（107行）。这是最高头衔层级，非功绩品级；不能把四品自动当王级、三品自动当帝级。
- `common/scripted_relations/00_scripted_relations.txt`的`disciple`为+0.25/月（337行），`elder`为+1/月（353行）。应按正确关系方向和当前关系数量计算。
- `common/court_positions/types/00_celestial_court_positions.txt`：`grand_preceptor_court_position`、`grand_mentor_court_position`、`grand_guardian_court_position`各+10/月（268、577、881行），`favored_minister_court_position`为+3/月（1644行），`minister_bureaucrat_court_position`为+1/月（2094行）。只给实际任职者。
- `common/council_positions/01_ministry_positions.txt`中的`minister_works`、`minister_grand_marshal`及`00_council_positions.txt`中的对应军务职位有`monthly_merit = 1`乘`council_scaled_celestial_ministry_value`。缩放位于`common/script_values/10_dlc_tgp_china_values.txt:206–223`：要求领主属于天朝霸主层级，并按弟子关系数、上限1缩放，不能给全部大臣普遍额外+1。

### 个人、庄园与家族

- `common/lifestyle_perks/00_learning_2_scholarship_tree_perks.txt`的`sanctioned_loopholes_perk`在贤能制度条件下有+2/月；`00_learning_3_theology_tree_perks.txt`的`faithful_perk`有条件+0.5/月，`prophet_perk`有月倍率+0.2。
- `00_stewardship_3_duty_tree_perks.txt`的`meritocracy_perk`有条件月倍率+0.05；`00_diplomacy_1_foreign_affairs_tree_perks.txt`的`forced_vassalage_perk`有条件月倍率+0.2。
- `common/traits/00_traits.txt`的`eunuch_1`与`beardless_eunuch`在对应文化条件下各有月倍率+0.5、固定+0.1/月；`loyal`、`confucian_education`在相应文化参数下有月倍率+0.1；`burdened`为−0.3。不是人人普遍具备。
- `common/domiciles/buildings/00_chinese_estate_buildings.txt:54–65`定义庄园档位：固定月功绩0.15/0.25/0.4，税额系数0.002/0.004/0.006，兵池价值系数0.0005/0.001/0.002，月倍率0.005/0.01/0.02。必须按实际建筑及等级计算，不能把所有档位普遍叠满。
- `common/house_aspirations/10_tgp_celestial_house_powers.txt`、`common/dynasty_perks/08_tgp_dynasty_perks.txt`、宝物、文化宗教及限时事件还可提供固定或倍率收入。模型将其作为明确个人输入或敏感性范围，不猜测普遍拥有率。
- `common/modifiers/10_tgp_modifiers.txt`的`tgp_e_minister_*_modifier`属于大臣家族荣誉来源，实际由`events/dlc/tgp/tgp_china_ministry_events.txt`等通过`add_house_modifier`施加。名字含大臣不表示在任大臣本人固有额外收益；须区分家族范围、获得条件及保留期限。

### 模组官署

[官员身份契约](../../../common/subject_contracts/contracts/tca_official_contracts.txt)的提刑基础4/月、通判2/月，属于原生月功绩乘区。[官署经费系数](../../../common/script_values/tca_office_funding_values.txt)为实拨金额×0.2；[正式结算](../../../common/scripted_effects/tca_office_funding_effects.txt)以冻结实付、实际收款人即时`change_merit`发放，并有官署30日防重。该动态奖励不再套个人月倍率，个人俸禄也不是此奖励基数。离职不保留旧任期的终身拨款收益。

## 离散奖励、资格与初始化

一次性来源必须列为事件，不将单次金额转换成人人固定月收入；未测得发生频率就只做明示敏感性输入。

- 会试基奖：原版`common/script_values/tgp_imperial_examination_values.txt`的`imperial_examination_merit_base_reward = 400`（742行），实际奖励受成绩和上下文修改。[模组会试数值](../../../common/script_values/tca_exam_values.txt)的`tca_exam_merit_base_reward_value`、`tca_exam_entrant_merit_reward_value`继续使用该基奖，另有成绩、殿试与主考档位修正；不是所有考生都得同额。
- [模组会试处置](../../../common/scripted_effects/tca_exam_effects.txt)的`tca_exam_award_candidate_effect`及第分支中，满足AI、非低出身、无玩家近亲/远亲等条件后，20%概率补殿试身份并给`empire_starting_merit_value = 12000`。这是进入该分支后的条件概率，不能设为全国每人每年20%中奖。
- 建造：原版`common/on_action/province_on_actions.txt`的建筑完成回调，要求实际完成建筑、对应行政官员身份及政府允许Merit；奖励`building_construction_merit_gain_value`。该值在`common/script_values/10_dlc_tgp_china_values.txt:932`起为60+县发展度，并可受庄园参数修改。不能给所有头衔持有人每年固定发一次。
- 战争：原版`common/scripted_effects/00_casus_belli_effects.txt`的胜者功名处理按`FAME_BASE × WINNER_FAME_SCALE`计算并受`maximum_merit_winner`限制（93–122行）；存在1000上限的奖励路径。它不等于所有战争、所有参战者普遍得到1000。事件发生次数不能从金额反推。
- 行政/军事任务：`common/task_contracts/tgp_admin_contracts.txt`、`tgp_admin_military_contracts.txt`中的相应结果分支使用`medium_merit_value × governance_task_contract_tier_value`，即60×任务等级；失败损失有30×等级档。它要求实际接取并完成/失败对应任务，不是所有官员每年无条件获得一次。
- 通判、提刑初次授职路径可在条件下补`county_starting_merit_value`或`duchy_starting_merit_value`并调用`assign_completed_exams_based_on_merit_effect`。它属于初始化/授职输入，不应每次年度增长重复发放。

考试奖励、考试身份和理论资格必须同步迁移。原版`common/scripted_effects/10_dlc_tgp_scripted_effects.txt`的`assign_completed_exams_based_on_merit_effect`按已有Merit分层补考试；低余额AI分支的10/50/25/15权重是在初始化时决定考试身份，并可能补县级基奖+年龄+学识，不是终身潜能分布，也不是每年重复考试概率。旧代理把最终资格封顶抽取为终身固定cap，既没有后续考试，也未完整反映高额奖励与补资格同一事件发生；因此不能只补一笔12000而继续把人物锁在原cap，也不能把已经计入初始Merit的考试奖再发一次。自然发生频率与后续考试的AI条件未测得时，使用明确时间表或敏感性情景，不称原版真实转移率。

## 升品回调不是本人功绩补贴

原版`common/on_action/character_levels.txt`的`on_merit_level_gain`没有向晋升者本人固定发Merit。庄园升品奖励发放prestige、piety、influence；师门关系可能因双方等级变化解除，从而改变后续月收入。

当到达原生level5、文化拥有`family_shares_merit`等条件成立时，回调给符合条件亲属`stratified_society_merit_gain_value = 500`并可能补乡试/荫补身份；数值位于`common/script_values/10_dlc_tgp_china_values.txt:49`。这是亲属的事件及资格反馈，不是本人下一关自动获得500，更不能无限自触发复制。

## 离线验证边界

模型采用已核查系数及显式税额、兵池价值、个人来源、实拨与事件外部输入。合成规模、分布、任职率、建筑次数、考试时间表和奖励发生率均须随配置冻结，不称游戏实测。先保持四带系数不变比较收入假设，避免同时改变控制器参数和外部供给而无法解释差异。

账本应能核对月度基础项、月倍率项、税收项、兵池项、官署实付和离散净奖惩，且把升品余额归一化跳变单列；否则成功升品会被误判为收入下降。数学一致性与模型回拉结果不替代正式引擎自然路径、显示、原生月结或保存重载验收。

## 已接入的研究与复算

[来源账本](model.py)提供持续收入分项、一次性事件及初始化接口；[生涯试验](study.py)复用原联合模型的人员、健康、任命和冻结六关，每年读取任免前实际职务重算收入。旧统一收入只保留为显式`legacy`对照。正式游戏与年度控制器输入没有新增这些复杂状态。

已核查11项关键系数，并扫描原版与模组正式`common/`、`events/`中功绩月收入、月倍率、独立奖惩与`change_merit`赋值位置；清单、文件摘要、配置、冻结源码、逐局逐年结果均写仓库外持久目录。源码扫描证明来源存在，不证明每条分支的执行率。测试夹具不列入正式来源。

目前实验保持[当前四带参数](../../../docs/appointment/merit_model.md#首版确定参数)不变，文武共享政策。基准种子50/51，每局120年；七个收入臂及两个单种子压力情景共32局：

- `legacy`：旧统一720/年及旧初始化，专门校验新增接口没有改写旧对照。
- `income_only`：只换持续收入，保留旧资格初始化，分离收入与资格修正。
- `low/reference/high`：按来源计收入，创建时使用已核对的AI考试初始化；贡献基数分别为参考输入的0.25/1/4倍。**reference只是比较锚点，没有实测均值含义。**
- `events`：参考持续收入上另安排明确事件；在任者每五年一次发展度20的建筑奖励，新人入仕15年后若尚未会试则补一次400主奖励及会试资格，25年后若尚未殿试则补一次12000分支及殿试资格。这个集中通过时间表用于检查事件/资格反馈，绝不是原生AI通过率，也不保证提高最高带人口。
- `personal`：参考持续收入上，明示假设每人另有2/月特长、0.25/月师门、0.25/月庄园和0.2月倍率；这是条件敏感性，不是人人拥有的默认。
- 压力只对`reference`检查四倍入仕、头衔收缩，未据其结果重调政策或经济输入。

合成参考贡献基数按四级职务分别输入：月实缴税`[10,60,240,0]`、头衔兵士基础招募价值`[500,2500,10000,0]`。地方角色显式选择标准文省或军事省，没有按品级自动套都会/都护府，也没有把所有帝级槽当大臣；中央示例槽才使用固定20/月。县级省契约是否适用尚须核对真实引擎条件，不能把研究角色分配当成实际县官收入证明。待阙者默认没有未提供的个人来源；普通官署角色及实拨输入默认未提供，不虚构其全国比例。模型已支持通判、提刑及实付奖励，但本轮未把它们擅自塞进四级头衔的既定数量。

因此参考文职按三级地方职务分别为8/48/192每月，武职为12/60/240每月；这些是**给定基数代入真实系数的演算值**，不是测得的逐品收入。中央示例大臣20基础月功绩，在研究帝级实际头衔倍率下为40；待阙为0。不同品级同任一个职务会取得相同职务项，升品不自动加薪；个人来源及修正仍可另变。

会试/殿试`eligible`字段仅表示是否进入普通功绩奖励身份分支，事件本身已经通过，故低出身者可获资格而主奖励为零；它不是考试参与或通过资格。模型的`metropolitan/palace`只计算主奖励，未有乡试且非低出身时的乡试补奖需另用带来源的`raw`事件显式输入，不能把返回值称完整考试净额；本轮事件臂未加入这项补奖。真正的考试通过次数、成绩、低出身与亲属条件仍应由实际输入决定。

采用初始化时学识10的公开合成值；初始化仅执行一次。后续考试通过显式事件改变`cap`，不设终身潜能锁。没有后续事件的各臂，资格仅在初始化后保持不变，是“未给后续考试”的条件情景；事件臂屏蔽使用期末资格构造的`capable_reach3_40`，避免事后选择偏差，保留全队列到达率。

年度代理仍在年初先移除死亡者，再对有效且非创建年人物按上一轮职务计十二个月收入；恢复者计整年，新入仕创建年不计收入/事件。没有按实际任职天数、死亡月份结算。无地庄园、师门变动及家族外溢若未提供具体状态事件，也不自动生成。

复算时指定持久新目录，不使用系统临时目录：

```sh
python3 tools/merit_research/income/checks.py
python3 tools/merit_research/income/study.py \
  --output-dir <仓库外的持久新目录> --game-root <本机原版game目录> --workers 4
python3 tools/merit_research/income/study.py \
  --output-dir <该持久目录> --game-root <本机原版game目录> --check-only
```

相同命令可补齐未完成局；已有局不覆盖，源码/配置变化会拒绝混用。复核目标、原始期望、实际随机取整、候选上界、六关人口流及来源分账；原始账与摘要不入库。当前比较结果和对数值结论的影响由[模型页](../../../docs/appointment/merit_model.md#功绩增长不能用一个平均月收入替代)维护。

## 四带系数全网格

[coefficient_grid.py](../coefficient_grid.py)把四个系数各设为`1.5/2/2.5/3/3.5/4`，总计1296个笛卡尔组合，其余政策参数固定。它原样调用按来源收入、AI考试初始化、年龄健康、任命及冻结六关规则，没有另造固定候选比例的简化控制器。

为控制全网格成本，初筛采用小合成国`J=[20,6,3,1]`，文武共同逐级初始人数`[40,8,4,6,2,3,2,1,0]`、每年2名新人。只缩小外部人口和头衔，不对文武分别套用不同初态缩放；帝级槽只有1个，使两路线中央示例槽占比均为100%，与完整基准相同。两个种子61/62、文武两路、参考/高收入两情景、80年，共10368局，逐局压缩保存。末40年排名只作粗筛，不把小池整数噪声当大国结论。

诊断排序首先比较八个条件中最差的带/尾跟踪误差，其次比较平均误差，最后列预算；高收入不能平均抵消参考收入的失败。带误差排除无法由晋升控制的九品目标，极小目标采用绝对人数尺度，同时保留最高带实际人数、原始目标比例、零人年和预算，不能把低目标下的无人称为良好供给。

每个最高带系数层保留一个跟踪代表，再保留用户指定参考、统一1.5/2.5/4、近优最低预算与最高实际高品供给代表。近优的最差跟踪差阈值为0.05，仅是公开缩减候选的工程规则，不是显著性标准或平衡验收线。完整规模使用新种子63/64、两路和两种收入、120年复核；仍报告每个条件，不把平均排名称福利最优。另列早段/末段最高带均值，不能仅因末40年平均看似平稳就证明已到稳态。

```sh
python3 tools/merit_research/coefficient_grid.py screen \
  --output-dir <仓库外的持久新目录> --game-root <本机原版game目录> --workers 4
python3 tools/merit_research/coefficient_grid.py validate \
  --output-dir <该目录> --game-root <本机原版game目录> --workers 4
python3 tools/merit_research/coefficient_grid.py check \
  --output-dir <该目录> --game-root <本机原版game目录>
```

本搜索覆盖的是1296组合的小规模世界，并对入围组做完整规模复核；不能称1296组合全部完成完整规模搜索，也不能证明未入围组合一定更差。复核结论由模型页统一维护。

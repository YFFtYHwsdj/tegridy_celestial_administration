# 国子监接手实施说明

本页面向尚不熟悉项目和CK3脚本的接手者，说明从设计到代码应如何分工、保存状态与核对接口。**当前没有国子监脚本；下文 `tca_guozijian_*` 名称为拟用接口，不是已存在可直接调用的效果。** 本次仅静态查找并编写文档，不制作测试／探针，不启动游戏。

先读[完整玩法](design.md)，再读[教育算法](education.md)和[参数草案](balance.md)，最后按本页实施；不要只看文件名就开始复制其他官署代码。

## 先理解五个不同概念

1. 官署是长期存在的头衔；判监是当前持有人。换人不能丢学校名单和改革。
2. 学籍是学生与官署的关联；人物可以不住判监宫廷。只遍历廷臣会漏掉世族学生。
3. 品级／Merit是人才资序，不等于实际任职。乡试入品不应让学生自动离学。
4. 任命超时是阻止原生官职继任的桥梁，不是学籍真值；考试或任官可能改写它。
5. 教学收益与成果奖励不同。学校发经验／隐藏分，判监只在真正培养结果发生时拿成果Merit。

## 原版与项目静态依据

原版路径均相对安装目录的 `game/`；本仓库路径相对仓库根。不得把原版路径写成本机个人绝对地址，也不要修改安装文件来验证模组。

### 头衔与任命

- 本仓库 `common/landed_titles/tca_judicial_titles.txt` 展示独立无地公爵头衔格式，如 `landless`、`no_automatic_claims`；`common/scripted_effects/tca_judicial_title_effects.txt` 提醒运行时设无地前先设首府。复制对象格式不等于复制地方司法身份。
- 原版 `common/succession_appointment/_succession_appointment.info` 列出 `level = merit`、`candidate_score`、`cooldown` 等；未见任意人物条件过滤字段，不能臆造 `valid_candidate`。
- 本仓库 `common/succession_appointment/tca_official_appointments.txt` 提供独立官职评分模板；判监应独立对象，复用共用底座，不改所有文官评分来仅服务学校。
- 原版 `common/laws/01_title_succession_laws.txt` 的 `celestial_ministry_appointment_succession_law` 要求 `tgp_is_civilian_minister_title`；这不是任意无地头衔可直接挂上的通用法律。
- [原版任命研究](../appointment/vanilla.md#冷却与退出)、`common/scripted_effects/tca_retirement_effects.txt` 提供 `appointment_timeout_days`、`set_appointment_timeout`、`clear_appointment_timeout` 及旧冷却恢复思路。退休机制是依据，不是学校可直接调用的身份效果。
- 地方在任身份分别用 `tca_is_celestial_governor_trigger` 与 `tca_is_landed_celestial_governor_trigger`；前者含登记无地主官，后者只含实土者。中央官职与宫廷差遣还要分别核对，不能用这两个地方接口包办全部。

### 正常无地朝臣官署与独立契约

用户明确：国子监就是正常的无地朝臣官署，按三省六部同类路径取得朝臣预算；仅契约待遇单独定义，不能给它照搬三省六部的待遇。不是地方拨款官署，也不是需要自建银行或学校资金托管的特殊实体。

原版 `common/subject_contracts/contracts/celestial.txt` 中 `celestial_minister_civil` 使用 `tgp_is_any_minister` 准入，提供朝臣预算基数与固定Merit；`celestial_ministry_budget` 的资格读取原版 ministry 任命法。`common/laws/01_title_succession_laws.txt` 的 ministry 任命法又读取 `tgp_is_civilian_minister_title`。新增头衔必须把这些身份、继任与契约入口按真实职责接通，不能只写 `landless = yes` 就期待自动拿钱。

拟新增独立国子监契约：仅判监官署适用，按[参数草案](balance.md#朝臣预算与判监契约)给自身预算基数、固定Merit与正常俸禄；不得同时领取普通三省六部那份职务待遇。国子监应被识别为中央朝臣官署，但不因此生成一个原版六部议席或调用六部换席专用逻辑。接手者逐消费者审阅朝臣共用身份与六部专用身份，不把两者混在一个全局替换里。

薪俸和预算仍走原生国库系统；换任、死亡及空缺的资金处理参照正常朝臣无地头衔的现有流程，不另设学校资金银行、不保存另一份可消费余额、不手工把旧任全部国库加给新任。若正常朝臣路径依赖具体大臣议席，则只抽取并复用官署交接职责，不能把国子监伪装成某个六部来调用它。

静态可确认原版有 `monthly_treasury_from_ministry_budget_base`；实际收入、契约排他和自然交接仍需未来验收，但这是新增正常朝臣的集成验证，不是重新讨论是否接受另一套财政。原版天朝职位雇员 `modifier` 已有 `monthly_merit` 依据，教师固定功绩可据此定义，不给教师另加官署预算。

### 教育与特质

- 原版 `common/scripted_effects/00_education_effects.txt`：`education_point_add_general_effect` 按儿童重心路由；`education_point_add_point_effect` 修改对应隐藏分变量；`education_point_acquisition_effect` 是正式基础教育流程，**不得每季度整体调用以再跑一遍监护教育**。
- 同文件 `court_tutor_education_boost_effect` 明确按宫廷持有者选教师，学校自定义职位不能只改名称就自动被识别；大学儿童隐藏分接口也不等于成年大学升级。
- 原版 `common/scripted_effects/05_dlc_bp2_effects.txt` 的 `increase_education_level_1_type_effect` 至 `_4_type_effect` 通过移除旧教育、添加新教育升级，但还向 `scope:activity` 写 `trait_rewards`。**不能在没有活动的学校作用域直接整段调用**。可复用其分档和trait替换方式，在学校独立效果内实现最小升级，不生成假大学活动。
- 原版成年大学活动入口 `common/activities/activity_types/university_visit.txt`、`events/dlc/bp2/bp2_adult_education_activity_events.txt` 及 `_oltner` 文件用于追踪最终教育升级实际调用，不能连活动专用临时scope一起照抄到学校。
- 原版 `common/traits/00_traits.txt` 可核对 `confucian_education`、`lifestyle_scholar`、`lifestyle_poet`、`lifestyle_blademaster`、`tourney_participant`、`strong`。竞技轨道实际key为 `foot`、`horse`、`bow`、`wit`，学校不培养 `wit`。
- `add_trait_xp` 与原版 `add_*_lifestyle_xp` 为不同收益；直接能力效果是 `add_*_skill`。不能因都叫经验而互相替换。
- 读取纯基础能力的脚本接口尚未确认；静态搜索未发现不是“不存在”的引擎证明。获取真实文档或后续最小验证，不能猜 `base_*`。

### 季度、任免与科举

- 本仓库 `common/on_action/tca_experience_on_actions.txt` 使用 `quarterly_playable_pulse` 追加子回调；这是错峰的可玩角色脉冲，不涵盖所有廷臣，也不等于固定季度日。
- `common/on_action/tca_tongpan_on_actions.txt` 展示 `on_game_start_after_lobby`、`on_title_gain`、`on_title_destroyed`、`on_vassal_change` 等跨文件追加；事件上下文需逐项看原版文档，不想当然共用 `scope:title`。
- `common/scripted_effects/tca_exam_effects.txt` 的 `tca_exam_award_candidate_effect`／整届结算入口要看实际收据与前十／补录过程；代办链不是每个候选先走一场独立殿试。
- `common/scripted_triggers/tca_military_court_position_triggers.txt` 中待阙入口及 `common/scripted_triggers/tca_court_position_triggers.txt` 的文武入口需要共同审阅，不只排除旧军事一个函数。

## 拟新增文件与职责

以下仅是文件规划，不创建空壳脚本，也不代表任何效果已经登记。

- `common/landed_titles/tca_guozijian_titles.txt`：唯一学校头衔；不把研究文稿塞进history。
- `common/laws/tca_guozijian_succession_laws.txt`、`common/succession_appointment/tca_guozijian_appointments.txt`：判监继任／评分，五四品范围和选任池按任命模块落实。
- `common/court_positions/types/tca_guozijian_positions.txt`：七直讲与两行政职位；任务若有独立文件，不和学校事件揉在一起。
- `common/law_groups/tca_guozijian_law_groups.txt`、`common/laws/tca_guozijian_laws.txt`：四组国家法律，不滥用 `can_keep` 造成阶段变化自动废法。
- `common/scripted_triggers/tca_guozijian_triggers.txt`：统一学校有效、招生资格、学籍、应离学、教育参与等判断。
- `common/script_values/tca_guozijian_values.txt`：唯一参数／评分／收益计算入口。
- `common/scripted_effects/tca_guozijian_*_effects.txt`：按学籍、教育、任命桥接、科举成果拆分；同一规则只维护一处。
- `common/on_action/tca_guozijian_on_actions.txt`：只追加独立子on_action；正式效果集中在下游。
- `common/character_interactions/tca_guozijian_interactions.txt`、`common/decisions/tca_guozijian_decisions.txt`、`events/tca_guozijian_events.txt`：申请、邀请、访求与审批／通知。
- 本地化分简中与英文，UTF-8 BOM；特质说明解释身份，获得提示直接使用原生结果，不写成开发规则说明书。
- GUI 文件规划见[界面](gui.md)。测试文件只在未来实现时按验证缺口增加，本次不新建。

## 状态放在哪里

### 学校头衔：长期公共状态

保存本校学生人物列表、当前学校有效状态／暂停时间、上次稳定持有人、学校所属国家、换任中标记及必要待处理队列。选择头衔而非判监人物作为学校关联，使换人不丢学校。

拟用名单 `tca_guozijian_students`。它是学校名册，不是每次打开窗口从全国重扫出来的临时猜测。季度与GUI共用名册，但GUI不可在每帧改它。

### 学生：当前与终身分开

当前学籍至少包含：学校头衔引用、入学日、有效培养日、已结算日／余额、居监或世族非迁宫标志、原雇主、儿童重心和成年切分所需状态、当前考试届次／延期状态、申请与退出事务编号、任命超时收据。

终身保留：六项学校直接属性贡献、隐藏分总贡献、教育／科举成果领奖收据。成年升级等待、特质资格日数和未消费机会按参数页建议跨退学保留，不能混成清理时一律remove所有 `tca_guozijian_*`。

派生状态不要重复存多个真值。特质表达在籍，学校引用表达归属，名册用于索引；出现不一致时由统一维护按仍有效事务修复或退出，不让GUI看到假特质就再次录取。

### 申请：短期事务

保存申请人、学生、同意方、目标学校、申请时判监、当前阶段和实际付款收据。申请时判监仅用来判断是否发生换任，最终审批必须是当前有效判监；换任后建议使旧审批失效并允许重新申请，而不是让离任者替学校付钱。

申请编号防止旧回应晚到。收到拒绝／过期后清临时字段，不能连学生原有任命超时一起清理。

### 教学日志不是成绩系统

只需保存本次收益摘要、累计限额、下次检查是否已到期，供窗口显示；不新建逐科成绩、排名、班级、学额或每季历史日志。长期存档不为每个季度建立一个story对象。

## 正式接口契约

以下名称是拟用接口。每个正式实现都须在附近写中文注释说明root、参数、输出、持久状态和副作用。

- `tca_guozijian_can_enroll_trigger`：root学生，显式传学校；只读招生资格，不扣钱／迁宫／初始化。
- `tca_guozijian_enroll_effect`：root学生，显式学校与同意收据；最终复核并一次性提交，重复提交无效，失败不留费用或半份学籍。
- `tca_guozijian_settle_student_effect`：root学生，显式截止日期与结算原因；先算未消费时间，再分渠道结算、更新收据，不触发招生。
- `tca_guozijian_leave_effect`：root学生，显式原因；独立处理结算、名册、特质、超时和必要迁宫，不负责授官。
- `tca_guozijian_award_result_effect`：root学生，显式结果种类／届次；检查真实在籍、最低培养与防重，给当前判监发一次奖，不伪造考试标记。
- `tca_guozijian_refresh_school_effect`：root学校；清无效引用、维护持有人交接／暂停、检查异常学生。不能每次维护给全校补一轮收益。

脚本不支持某种命名参数／日期运算时要改成已核对的传参形式；此清单是契约，不是已验证语法。

## 两个必须写清的实现难点

### 任命超时不是简单保存再清除

原生只有一个可读超时字段。学校设长超时后，考试可能清它，真实任官又可能写新超时。只存入学旧值，离学 `clear` 后还原，会误删在学新冷却；只取当前最大，又会把学校自身长超时保留下来。

建议把“学校占用”和“外部应保留截止日”分别记账，所有本模组可控超时写入通过共用桥接登记：学校在学时保持桥接值，离学去掉学校项后取其余未到期截止日。保留退休／辞谢等身份自己的所有权，不清其他模块字段。

原生自动写入若不经过该桥接，必须沿真实任官／考试回调捕获；不能只在下一季度猜。快照截止日、回调顺序和原生getter在非天朝身份时的行为需要后续验证。接口未确认前把本难点视为阻塞条件，不声称“每季度刷新150年就安全”。

### 不能回溯不知道的教师历史

只记录入学日，季度时看当前教师，无法知道三个月中是否换师／停课。建议在学校暂停、恢复、教职获得／离任、法律裁撤、学生成年／换重心等边界先结算旧区间再更新快照；学校名单不设容量，但禁止每个学生每帧全世界搜索。

若原生某边界只有变更后回调，应保存上期师资／重心快照，并验证跨日刷新；不要用已换任教师给过去全年追补。未能稳定捕获时可提出“按季度末师资估算”的替代，但必须明确误差并征求用户，不静默改变实学日语义。

## 入品、科举与结业顺序

学校不改考试自身成绩／修正／记忆。科举正式入口先结学生实际成绩和奖励，再在最终名单确认的位置调用学校成果，最后结业。一次会试中前十与补录可能在候选逐人循环内产生，不能在读到会试修正的同一行就退出。

期中只设置“本届待最终处理”状态，结果终结时再清。活动取消／玩家中断／主持人死亡不能伪造殿试失败；学校可暂恢复正常在学并清本届延期，具体沿活动真实终止回调。

成年时学校隐藏分必须先于原版生成教育结果生效，判监成果则读取最终教育特质；原版on_action合并顺序要查清，不能为了前置而覆盖整份 `game_start.txt` 或重写原版教育流程。

## 推荐实施次序与停手条件

1. 静态核对身份、任命法、预算准入与监护权限；把确需游戏确认的留入验证清单。
2. 先实现单学校、学籍和录取／离学事务，再接任命超时与待阙排除；没有完整清理不要批量AI招生。
3. 再接季度有效日、单教师与收益限额，最后接特质和成果通知，便于定位重复发放。
4. 接四项法律、师资空缺与AI；最后才做GUI，不让界面回调承担业务初始化。
5. 未来必要验证按[清单](verification.md)最小充分执行；图形探针和游戏测试本次均不做。

遇到普通儿童迁宫破坏监护权限、中央预算无法原生接入、共享超时无法安全释放等问题，应停在相关前置并报告。文档完整不等于已消除引擎未知，不允许接手者为“完成”擅自改成远程全员、独立财政或无冷却任官。

## 任命超时写入来源清单与处理顺序

以下由当前仓库静态搜索所得，排除 `tests/fixtures` 的夹具写入；接手前再搜一次，不能把清单当永久完整。

- `common/scripted_effects/tca_official_appointment_effects.txt`：`tca_set_official_appointment_cooldown_effect` 写正式获任冷却。学校离学不能清它；先记录本次外部截止日，再释放学校项。
- `common/scripted_effects/tca_circuit_succession_effects.txt`：部分候选／继任适配清超时。核对其原有目的，在学者不能借它清掉学校限制重新参选，不把它对普通官员的行为改坏。
- `common/scripted_effects/tca_retirement_effects.txt`、`tca_retirement_office_effects.txt`：退休长超时与起复恢复，各自身份仍是该模块真值；学校只释放自己，不重置奉祠／致仕快照。
- `common/scripted_effects/tca_retirement_native_effects.txt`：辞官应试分支写三年超时；不能作为“考试准备必清所有冷却”的借口。
- `common/activities/activity_types/zz_tca_local_examination.txt`、`zz_tca_imperial_examination.txt`：活动准备有清超时，另有短超时／收尾清理；逐个分支看上下文，不能仅修改代办链就认为已覆盖AI。
- `common/decisions/dlc_decisions/tgp/zz_tca_merit_career_decisions.txt`：辞谢任命／恢复路径；恢复不应清掉仍在籍者的学校项，主动永久辞谢也不能在退学后消失。
- `common/decisions/dlc_decisions/ep_3/zz_tca_retirement_entry_decisions.txt`：原生辞官适配写超时；按实际入口保存其外部截止日。
- 原版 `common/scripted_effects/tgp_imperial_examination_scripted_effects.txt` 也有 `clear_appointment_timeout`；须追踪调用者和当前覆盖，不假定所有考试清理都在本模组文件。

建议统一时序示例：考试准备请求清自己的短超时→桥接移除对应考试项并保留学校项→应试正常进行→真实授官回调记录新任官截止日→学校因实际任职离学→仅移除学校项→原生字段反映仍有效的新任官冷却。任何一步都不能短暂把在籍学生以零冷却暴露给原生继任扫描。

单字段无法从数值判断“这次清的是谁”的原生不可拦截路径，列入明确阻塞；优先找正式完成回调或可最小追加的效果，不靠每季度事后修复掩盖中间窗口。`set_appointment_timeout.days` 在现有项目用命名script value传值，直接 `var:` 的可用性不能凭直觉猜。

## 判监选任与正常朝臣身份的建议拆分

判监是中央教育朝臣，不登记成地方主官；地方 `tca_is_celestial_governor_trigger` 的扩展范围不因为学校无地就包含它。招生排除正式官员则必须另外识别此中央身份。

拟用独立 `tca_guozijian_appointment` 与对应任命法，保留原生Merit候选和正式任命底座，专业加分草案：学识×1.5、管理×0.5、外交×0.25，儒家经验×0.1，学者特质+5；五／四品（实际等级以现有Merit映射为准）再给予10分偏好。底座、投资、宗教等原有因素只复用一次，不把 `appointment_score_governor` 中考试加分重复加两遍。

“主要参与五四品资序池”不能只靠此偏好分保证；需核对公爵官署原生Merit等级准入。若原生等级池与设计不符，按现有官署登记／任命法层的接口适配，不通过给所有低品者-9999称为硬排除。直接授职、候选竞争与自然继任分别核对。

朝臣共用识别应承认新增国子监；六部／三省专属议席、换席任务与特定大臣法律则不应仅因“也是朝臣”自动执行。接手者先列出 `tgp_is_any_minister`、`tgp_is_civilian_minister_title` 及相关契约消费者，再选择最小独立入口或必要原对象适配，登记理由与基线。

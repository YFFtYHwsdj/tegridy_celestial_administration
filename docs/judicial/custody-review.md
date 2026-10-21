# 详覆羁押

## 当前行为

提刑复核本路其他统治者关押的一名囚犯，发送后立即按双方评分判定，不再先询问关押者是否同意移交。成功表示找到足以改变原关押处置的理由，实际效果是囚犯移交给提刑；失败表示理由不足，囚犯继续由原关押者关押。只改变当前看管者和现有处置权限，不新增案件、判决记录或无罪认定；不以缺少当前拘捕理由认定原拘押违法。

使用可用弱／强牵制时，直接移交并消耗牵制，跳过评分判定。政治强制移交不代表复核理由成立。成功移交保持原监禁类型，清除旧官署登记并登记到当前提刑官署；后续释放、死亡、换任使用已有公职囚犯维护。

双方评分仍为：学识＋外交×0.5＋儒学加成＋性格修正。儒学经验0/20/40/60/80档加2/4/6/8/10，无特质加0；公正加3，专断减3。不加入功绩、科举或囚犯关系。

令D为提刑评分减关押者评分，成功权重=max(1,50+3D)，失败权重=max(1,50−3D)，成功率=成功权重/总权重。同分50%，高5分65%，高10分80%。正式random_list直接按完整复合评分差组成权重，悬浮明细使用等价的完整评分脚本值；在发送时按当时属性计算一次。

## 资格、费用与AI

发起人为有效在任成年提刑，存活且未被关押，所属路司法制度有效。关押者须属于本路统一司法辖区：主要行政头衔法理在该路下，或该路是其路长官的主要头衔；主头衔为世族时按真实庄园县的法理路，不区分实际领主身份。主要行政官职优先于庄园。且关押者须处于同一皇帝领国、存活、自由、为统治者，双方不交战。非主要路提刑不能详覆兼任长官；皇帝及其关押的囚犯排除。旅行、随军或参加／筹备活动不阻止复核。囚犯须仍实际由该人关押、存活，不是发起者或关押者本人，不在自动引渡、酷刑或其他复核处理中。不限制拘捕来源或囚犯本人的辖区。季度AI从同一皇帝领国内筛选，再以该辖区规则过滤，不只扫描路长官实际封臣。庄园跨路迁移会使旧提刑的未结上下文失效；真实囚犯、取消清理和新路移交测试见[庄园回归记录](verification.md)。

发起费用及提刑失败代价统一按囚犯`tca_judicial_identity_tier`查档，当前五档为：

- 第1档（<30）：发起15影响力；提刑失败另损失15影响力、30威望。
- 第2档（30—49）：发起25影响力；提刑失败另损失25影响力、60威望。
- 第3档（50—79）：发起40影响力；提刑失败另损失50影响力、125威望。
- 第4档（80—99）：发起65影响力；提刑失败另损失100影响力、250威望。
- 第5档（≥100）：发起100影响力；提刑失败另损失200影响力、500威望。

15个`tca_review_tier_<档位>_<start_cost/influence_loss/prestige_loss>`值独立定义，3个囚犯作用域查档值统一提供费用与两种败方损失，不读取身份分项。额外失败代价仅由提刑承担；详覆成立时原关押者不损失威望、影响力或好感。提刑失败时对关押者降低10好感，沿用原2年期限；非影响力政府不扣影响力。发起者冷却3个月、囚犯冷却1年。牵制仍付同档发起费，但跳过普通失败代价与好感损失。五档数值仍待平衡验收。

玩家互动使用原生cost扣费，on_send内临时标记tca_review_cost_paid跳过prepare中的重复扣费和扣费后余额检查；原生cost由secondary_recipient的费用值计算，未选囚犯时返回0，不能发送，结束即清除。AI与直接start调用由prepare扣费。需要验收实际引擎cost/on_send顺序及恰好该档费用及差1点边界。

季度AI仍在本路候选中选一个最高兴趣目标，以25%概率发起；兴趣考虑亲近／仇敌关系、正式成功率与性格。低胜率且囚犯亲近时可用牵制。已移除关押者选择移交／应辩的AI权重，移除合作好感定义和本地化，AI发起后使用同一直接结算入口。

## 界面与实现入口

互动标题与发送按钮均为“详覆羁押”。正文说明复核目标；成功分支“详覆成立”中的“详覆”二字绑定tca_review_score_breakdown悬浮提示，失败分支显示“不成立”且不绑定提示，can_send复用同一提示，费用使用原生费用栏。旧版只有发送按钮悬浮文本，未满足直接查看概率的需求；当前结果概率使用原生random_list预览，因素明细改为结果文字的悬浮提示。

评分明细直接来自正式tca_review_score：四个add分项以desc标注学识、外交贡献、儒学修养及性格名称，数值仍调用既有正式加成脚本；链接提示从CharacterInteractionConfirmationWindow.GetPuppetOrActor／GetRecipient取得双方角色，再调用MakeScope.GetScriptValueDesc('tca_review_score')自动生成贡献明细，只补双方名称、总评分及最终成功率，不重复编写加成条件或数值。tca_review_actor_wins仅在“详覆”二字上通过#tooltip:tca_review_score_breakdown绑定提示；tca_review_keeper_wins为普通文字“不成立”；移交和维持原押分别由分支正文说明；can_send旧明细键改为引用同一提示。此接口解释正式评分，不声称能自动解析random_list内部权重。保留既有评分回归，未为纯明细标签新增业务用例。

依据为原版07_ep3_values.txt的governor_efficiency：实际add数值项带desc；government_administration_window_l_english.yml的ADMIN_WINDOW_THEME_GOVERNOR_EFFICIENCY_VALID_TT直接调用GetScriptValueDesc。文本绑定参考tgp_tribute_mission_l_english.yml的#tooltip语法。当前文字提示绑定已实际出现，但旧角色别名读取失败；修正后的明细仍需重启后在普通确认页悬浮成功分支的“详覆”二字，核对双方角色、四项贡献及总评分；用同分50%、固定差10分80%、无儒学／公正／专断及已有复合抵消场景核对。0贡献是否隐藏、嵌套脚本值展开样式、数值精度与文本提示绑定是否生效均待引擎验证。

牵制选项常驻显示；仅在发起者对当前关押者拥有可用牵制时允许勾选，没有可用牵制时禁用。沿用原版00_prison_interactions.txt中imprison_interaction的send_option.is_valid写法，移除原先导致整项隐藏的is_shown。发送资格仍检查牵制可用性，勾选后直接移交。真实确认页仍待验证：无牵制或强牵制暂不可用时选项可见但不可选，有可用牵制时可选，切换后显示直接移交且不提前使用牵制。

当前不修改GUI文件，不使用ai_accept作胜负判定。on_send准备上下文并直接调用正式random_list；on_accept通过show_as_tooltip调用同一段random_list，仅在原生效果预览中显示成功／失败分支及概率。两个分支显式show_chance=yes。牵制分支仅显示直接移交。原生结果树的排版与悬浮位置须实际打开确认页验证，不承诺独立的按钮上方进度条。

共享tca_review_random_result_effect以ACTOR/KEEPER参数接收角色，以SUCCESS/FAILURE参数接收结果回调：正式调用使用已保存角色和真实结算；预览使用原生actor/recipient/secondary_recipient角色，成功回调含移交说明；失败回调含维持原押说明及原生威望／影响力／好感效果。回调仅在show_as_tooltip内使用，效果只用于生成预览文本。预览不准备请求、不读序号、不执行正式结算，也不触发任何选择事件。最终结算对AI／玩家使用同一random_list。

两个random_list分支的基础权重为0，通过modifier.add直接读取参数角色的完整tca_review_score，计算max(1,50±3D)。下限在内联数值公式的最后应用，不再拆分学识与其他贡献，也不使用duel_value。正式结算和确认预览共享同一效果及内联公式，悬浮明细、AI兴趣和数值断言继续使用数学等价的tca_review_actor_weight／tca_review_keeper_weight脚本值。内联公式直接接收ACTOR/KEEPER参数，预览无需建立pending或保存正式请求作用域。

参考本机原版00_diarch_interactions.txt的diarch_legal_meddling_interaction中随机资源选项：on_accept使用random_list与desc展示两种结果。复核额外显式show_chance=yes，并用show_as_tooltip隔离实际操作。脚本权重、预览安全与真实界面渲染分别验收，不能由数值断言推定全部显示正确。没有新增原版同名对象或GUI覆盖。

- common/character_interactions/tca_custody_review_interactions.txt：玩家入口与只读预览。
- common/scripted_effects/tca_custody_review_effects.txt：on_send→start→prepare→正式评分判定／牵制移交→清理。on_accept仅调用原生对抗的show_as_tooltip预览，不负责正式结算，避免确认页预览产生副作用。
- common/script_values/tca_custody_review_values.txt：正式评分、权重和AI发起兴趣。
- common/scripted_triggers/tca_custody_review_triggers.txt：原生角色输入、辖区和结算上下文校验。
- events/tca_custody_review_events.txt：移除旧回应事件.1；.3保留按序号匹配的30天清理保护。新发送不等待回应，正常结算会立即清除待处理状态，保护事件不会再次结算。不保留旧回应版本的存档兼容入口。

参考原版00_diarch_interactions.txt的diarch_legal_meddling_interaction：auto_accept后按学识对抗或资源选项直接结算；复核沿用这一直接判定结构，但继续使用自身复合评分和囚犯移交效果。原生interaction_confirmation.gui的发送按钮读取GetSendName/费用栏读取cost，概率条读取回应预测，不能将其自动等同正式复核成功率。未新增GUI覆盖。

## 确认页与通知的作用域

结果链接提示使用 `CharacterInteractionConfirmationWindow.GetPuppetOrActor`／`GetRecipient`，不能依赖链接未携带的 `actor`／`recipient` 别名；该接口只用于确认窗口。成功行“详覆”提供评分提示，失败行不重复绑定。成功预览说明移交，失败预览在发起者作用域读取当前囚犯档位，以原生效果展示实际代价；`show_as_tooltip` 隔离副作用。

正式发送在 prepare 保存囚犯两种失败代价；回复读取快照，避免身份变化改变已发送请求。普通成功只移交、登记及通知，不惩罚原关押者。双方各有一条结果通知，正文使用保存的 `tca_review_actor`／`keeper`／`prisoner`；牵制移交单独说明强制来源，不称为详覆成立。

## 验证与限制

测试源为 `events/tests/tca_custody_review_test_events.txt`，登记与运行见[统一测试入口](../testing/README.md)。覆盖成功、失败、牵制、重复结算、预览无副作用、身份分档、发送时快照、余额差一点与恰好足够，以及 AI 可负担候选筛选。直接效果调用不证明真实界面的 cost／on_send 顺序。

专用测试局分别选择五档囚犯，核对发送费及失败代价；切换普通／牵制选项不扣资源、不改好感；实际移交保持软禁／地牢类型。第4档失败应为250威望、100影响力及10好感，成功不处罚关押者。随后核对两方各一条通知、季度自然 AI、庄园跨路取消、非影响力政府及保存重载。已有评分提示截图只覆盖当时确认页，不能扩展到新通知、全部费用边界或长期概率分布。

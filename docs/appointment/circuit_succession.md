# 路主任命继承补授

状态：P0–P4 已接入。默认启用：路类型登记、继承顺位资格（P1）、回落检测与待补授标记、季度预清冷却、在任资格审计（P2，只记录官品低于头衔等级）。自动补授因引擎脚本授予在部分路径会销毁有地头衔而默认关闭；强制收回（P3）只针对低品在任者，保留最小路径，双开关都开启才执行，默认关闭；文官路补挂任命法（P4）改为默认关闭的可选开关；一人多路按"兼任不干预"处理，只提供默认关闭的信息记录。本页维护当前规则、实现接口、状态、日志、开关与验收边界；设计理由、候选范围与兼任规则见[路主继承补授设计](circuit_succession_design.md)，本轮阶段与剩余工作见[本轮计划](circuit_succession_plan.md)。

## 适用范围

路是 h_china 法理下的王国级有地世俗头衔。文官路使用民政契约，军区／都护路使用 `celestial_provinces` 的军事档位；路类型由持有人契约推导，记在头衔持久变量 `tca_circuit_kind` 上（1 文官、2 军区、3 都护）。只有**曾由天朝封臣持有并写入类型标记**的路进入本机制；皇帝通过战争、剥夺或正常授予取得且从未由天朝封臣持有的路不处理，旧存档不追溯迁移。

在任资格审计只覆盖已登记路；文官路补挂任命法只覆盖 `tca_circuit_kind = 1` 的路。

## 现行流程

1. **原生继承优先**：正常继任完全由原生任命产生，本机制不介入。P1 只把"第一顺位不存活、是领主、或功绩等级不足"视为无效顺位，不改变原生评分与排序。
2. **季度预清**：登记路仍由天朝封臣持有、没有有效继承顺位时，清除"只差近期受任冷却"的候选人的冷却，让原生继承继续选人。预清判据：`0 < appointment_timeout_days <= 1825`（5 年受任冷却全区间，含已衰减至 3 年以内的原版受任官员）；150 年辞谢、奉祠／致仕、原版 3 年辞官致仕（`ep3_renounced_governorship_merit`）、考试赶考与正在参与乡试／会试活动（`involved_activity`）均由排除清单挡住。
3. **在任资格审计（P2，默认只记录）**：持有人变更（`tca_circuit_register_road_holder_gain_effect`）与季度维护的轻量同步循环都会审计在任者。只有官品低于头衔等级才记 `tca_circuit_incumbent_invalid = 1`，并用 `tca_circuit_audit_reported` 去重；恢复合法后清除。一人多路不判不合格，仅在可选诊断开关开启时记 `tca_circuit_multi_road_reported` 与 `INCUMBENT_MULTI_ROAD_INFO`。默认不写待处理、不收回、不改持有人。
4. **回落检测与待补授**：带类型标记的路由皇帝取得、且前任已死时写入 `tca_circuit_pending_appointment` 并排队次日维护。回落约 1 tick 内 AI 可能已把路授予他人，因此标记不在取得头衔时自动清除。
5. **待补授结算（默认关闭）**：开关 `tca_circuit_self_grant_enabled` 存在时，维护按当前持有人分流——皇帝持有则按权重 `1 + 功绩等级` 选人自授；合格天朝封臣持有则接受并清标记；不合格天朝封臣持有则先以 `granted` 事务收回皇帝再自授；外部持有人保留标记等待下季度。默认关闭时只记录 `SELF_GRANT_DISABLED`，保留待补授标记与登记，不授予、不改持有人；合格现持有人的接受分支不受开关影响。
6. **强制收回（P3，默认关闭，仅低品）**：全局变量 `tca_circuit_retract_unqualified_enabled` 存在时，审计才会为低品在任者写 `tca_circuit_incumbent_pending` 并排队；维护处理时还要求 `tca_circuit_self_grant_enabled` 同时存在才会真正收回。收回走回落收回效果，成功后补写待补授标记并按补授流水线处理。**没有多头衔收回分支**：一人多路不写待处理、不会被收回。
7. **旧头衔处理（递归，默认关闭）**：被授者每个非家门头衔先读自身 `current_heir`；继承人存活、不是该头衔领主且满足条件时按原头衔、原领主、原法理转交，否则对该头衔重复选人（递归深度上限 4），仍无人可选时生成新角色。任何一步都不把空缺头衔交给领主。
8. **生成补授（默认关闭）**：文官用 `tgp_minister_scholar_template`，军区／都护用 `tgp_minister_commander_template`；功绩按头衔等级起始值，补齐世族、天朝政体、主头衔、任命冷却与近期受任标记。
9. **文官路补挂任命法（P4，可选，默认关闭）**：全局变量 `tca_circuit_civil_law_ensure_enabled` 存在时，`kind = 1` 的已登记路由天朝封臣持有、缺 `celestial_appointment_succession_law`、无 `celestial_military_appointment` 与 `locked_to_partition` 契约标记时，才补挂该领地法并记录 `CIVIL_LAW_ENSURED`；季度维护重试。默认关闭时不改写任何持有人的领地法，也不追溯既有继承路径。
10. **授予方式**：有地头衔连同其封臣一起转移（`change_title_holder_include_vassals`）；无地官署保持普通 `change_title_holder`。无地且无家门的接收者先建立王朝、家门、真实领主关系与天朝政体；由于引擎在同一效果链内不承认刚创建的家门状态（会销毁目标头衔），这一步与授予拆成两段：当日准备并记录在头衔变量 `tca_circuit_prepared_candidate`，次日维护按记录完成授予（已有家门／有地接收者仍当日完成）。旧头衔的无地无家门继承人也走同一两段式。事务类型为 `granted`，不使用 `appointment` 事务。

## 实现入口

### 文件

| 文件 | 用途 |
| --- | --- |
| `common/scripted_triggers/tca_circuit_succession_triggers.txt` | 路／登记／顺位判定、等级要求、低品审计与可选兼任阈值判定、候选人资格与排除、待补授与预清状态 |
| `common/scripted_effects/tca_circuit_succession_effects.txt` | 登记、回调、季度巡检、预清、在任审计、强制收回、文官补法、自授、收回、旧头衔递归、生成 |
| `common/script_values/tca_circuit_succession_values.txt` | 抽选权重、生成功绩、一人多路信息记录的阈值与计数 |
| `common/on_action/tca_circuit_succession_on_actions.txt` | 开局／年度重建、季度巡检、`on_title_gain`、`on_title_destroyed`、次日维护 |
| `common/scripted_effects/tca_official_appointment_effects.txt` | 共享冷却入口：写 1825 天冷却时同步 `tca_recent_appointment` 标记 |
| `events/tests/tca_circuit_succession_test_events.txt` | 引擎回归用例（模块登记在 `common/scripted_effects/tests/modules/`） |
| `tools/upstream_overrides.json` | `on_title_gain` 等同名追加的覆盖登记 |

### 主要效果与触发器

- 回调与排队：`tca_circuit_on_title_gain_effect`、`tca_circuit_mark_lapsed_title_effect`、`tca_circuit_register_road_holder_gain_effect`、`tca_circuit_queue_maintenance_effect`、`tca_circuit_on_title_destroyed_effect`。
- 登记与类型：`tca_circuit_register_title_effect`、`tca_circuit_unregister_title_effect`、`tca_circuit_sync_kind_effect`、`tca_circuit_rebuild_registry_effect`、`tca_circuit_apply_road_kind_contract_effect`。
- 维护与流水线：`tca_circuit_run_maintenance_effect`（皇帝作用域）、`tca_circuit_maintain_title_effect`、`tca_circuit_handle_pending_title_effect`、`tca_circuit_retract_title_to_emperor_effect`、`tca_circuit_preclear_cooldowns_effect`、`tca_circuit_clear_recent_appointment_effect`、`tca_circuit_fill_lapsed_title_effect`、`tca_circuit_fill_vacant_title_effect`、`tca_circuit_build_qualified_candidates_effect`、`tca_circuit_assign_selected_candidate_effect`、`tca_circuit_transfer_title_granted_effect`（统一授予入口，由当前持有人发起事务）、`tca_circuit_prepare_landless_recipient_effect`（授予前把无地接收者准备为无地统治者）、`tca_circuit_process_old_titles_effect`、`tca_circuit_reassign_old_title_effect`、`tca_circuit_generate_holder_effect`。
- 在任资格审计与 P3／P4：`tca_circuit_audit_incumbent_effect`（头衔作用域，默认只写状态与日志）、`tca_circuit_clear_audit_effect`（空作用域，开启强制模式前后重扫）、`tca_circuit_handle_incumbent_invalid_effect`（头衔作用域，维护处置）、`tca_circuit_enable_retract_unqualified_effect`／`tca_circuit_disable_retract_unqualified_effect`（强制收回调试开关）、`tca_circuit_ensure_civil_appointment_law_effect`（头衔作用域，文官路可选补法）、`tca_circuit_enable_civil_law_ensure_effect`／`tca_circuit_disable_civil_law_ensure_effect`（补法开关）、`tca_circuit_enable_multi_road_audit_effect`／`tca_circuit_disable_multi_road_audit_effect`（一人多路信息记录开关）。
- 判定：`tca_circuit_is_road_trigger`、`tca_circuit_is_tracked_road_trigger`、`tca_circuit_has_celestial_vassal_holder_trigger`、`tca_circuit_has_valid_heir_trigger`（P1 加严）、`tca_circuit_heir_meets_level_trigger`、`tca_circuit_has_title_level_requirement_trigger`、`tca_circuit_incumbent_meets_level_trigger`、`tca_circuit_holder_exceeds_road_limit_trigger`、`tca_circuit_incumbent_invalid_trigger`、`tca_circuit_has_incumbent_pending_trigger`、`tca_circuit_has_pending_appointment_trigger`、`tca_circuit_is_lapsed_trigger`、`tca_circuit_should_preclear_trigger`、`tca_circuit_needs_maintenance_trigger`（含在任待处理）、`tca_circuit_needs_candidate_pool_trigger`、`tca_circuit_candidate_realm_trigger`、`tca_circuit_candidate_base_trigger`、`tca_circuit_candidate_excluded_trigger`、`tca_circuit_has_recent_appointment_cooldown_trigger`、`tca_circuit_is_native_appointment_eligible_trigger`、`tca_circuit_is_qualified_candidate_trigger`、`tca_circuit_is_acceptable_road_holder_trigger`、`tca_circuit_is_preclear_candidate_trigger`。

### 开关与启用范围

| 范围 | 默认 | 说明 |
| --- | --- | --- |
| 路类型标记、登记同步、年度重建 | 启用 | 只写头衔脚本状态，不改头衔归属 |
| 继承顺位资格（P1） | 启用 | 只把不合格第一顺位视为无效；不改变原生评分与排序 |
| 回落检测、待补授标记、次日/季度维护排队 | 启用 | 只写标记与队列，不授予 |
| 季度预清近期受任冷却 | 启用 | 清 `0 < appointment_timeout_days <= 1825` 近期受任冷却与模组标记（致仕／拒任／考试由排除清单拦截），不改头衔 |
| 在任资格审计（P2） | 启用 | 只写 `tca_circuit_incumbent_invalid`／`tca_circuit_audit_reported` 与调试日志，不改持有人 |
| 文官路补挂任命法（P4） | **关闭** | 需 `tca_circuit_civil_law_ensure_enabled`；只对 `kind = 1` 补 `celestial_appointment_succession_law`，默认不执行、不改写既有继承路径 |
| 一人多路信息记录 | **关闭** | 需 `tca_circuit_multi_road_audit_enabled`；只写 `tca_circuit_multi_road_reported` 与 `INCUMBENT_MULTI_ROAD_INFO`，不判不合格、不收回 |
| 强制收回（P3） | **关闭** | 需 `tca_circuit_retract_unqualified_enabled`；只针对低品在任者，真正收回还须 `tca_circuit_self_grant_enabled`，双开关才执行 |
| 自动补授（自授、收回再授、生成两段式、旧头衔递归授予） | **关闭** | 引擎脚本授予在部分无地接收者路径会销毁有地头衔；默认保留待补授，等待后续安全方案 |

开关与阈值均只给开发／调试用，不接玩家入口：

- `tca_circuit_self_grant_enabled`（不存在＝关闭）：自动补授总开关，调试入口 `tca_circuit_enable_self_grant_effect`／`tca_circuit_disable_self_grant_effect`。
- `tca_circuit_retract_unqualified_enabled`（不存在＝关闭）：低品在任者强制收回，调试入口 `tca_circuit_enable_retract_unqualified_effect`／`tca_circuit_disable_retract_unqualified_effect`；开启时会先清空全部登记路的审计状态再重扫。
- `tca_circuit_multi_road_audit_enabled`（不存在＝关闭）：一人多路信息记录，调试入口 `tca_circuit_enable_multi_road_audit_effect`／`tca_circuit_disable_multi_road_audit_effect`；只记录、不处置。
- `tca_circuit_civil_law_ensure_enabled`（不存在＝关闭）：文官路补挂任命法，调试入口 `tca_circuit_enable_civil_law_ensure_effect`／`tca_circuit_disable_civil_law_ensure_effect`；默认不执行。
- `tca_circuit_max_kingdom_roads`（不存在＝1）：一人多路信息记录的阈值，由 `tca_circuit_max_kingdom_roads_value` 读取；只影响可选诊断，不改原生任命与继承规则。

### 状态

- 持久：头衔变量 `tca_circuit_kind`、`tca_circuit_pending_appointment`、`tca_circuit_incumbent_invalid`（只表示 1 官品低于头衔等级）、`tca_circuit_audit_reported`（去重）、`tca_circuit_incumbent_pending`（待强制处理）、`tca_circuit_multi_road_reported`（可选兼任信息去重）、`tca_circuit_processed_serial`、`tca_circuit_prepared_candidate`（两段式 day1 记录，人物作用域值）、`tca_circuit_prepared_mode`、`tca_circuit_prepared_serial`；全局列表 `tca_circuit_titles`、`tca_circuit_prepared_titles`；人物最近受任标记 `tca_recent_appointment`（与 1825 天冷却同期限到期）。
- 单轮：全局 `tca_circuit_run_serial`、`tca_circuit_transaction_depth`、`tca_circuit_transaction_kind`、`tca_circuit_grant_kind`、`tca_circuit_grant_merit`；人物 `tca_circuit_maintenance_pending`、`tca_circuit_maintenance_running`、`tca_circuit_used_serial`、`tca_circuit_pregrant_landed`（授予前有地标记，收尾即清）；局部列表 `tca_circuit_candidate_pool`、`tca_circuit_qualified_candidates`。
- 登记表在开局与年度从 h_china 侧重建设；脚本列表不随存档保存，头衔持久变量是类型与各类待处理状态的唯一来源。审计相关变量（含可选兼任信息）与回落待补授分开，互不消费。

### 日志与诊断

调试日志统一使用 `TCA_CIRCUIT ` 前缀，需要定位作用域时同时设置 `debug_log_scopes = yes`。本轮新增与相关的日志标记：

| 标记 | 含义 |
| --- | --- |
| `TITLE_GAIN_EMPEROR`／`TITLE_GAIN_CELESTIAL` | `on_title_gain` 皇帝回落分支／天朝封臣取得分支，带作用域便于核对 `transfer_type` 与持有人 |
| `HEIR_LEVEL_LOW` | 预清入口发现第一顺位不合格，随后照常预清 |
| `INCUMBENT_LEVEL_LOW` | 在任审计判为官品低于头衔等级，带去重 |
| `INCUMBENT_MULTI_ROAD_INFO` | 可选兼任信息（需 `tca_circuit_multi_road_audit_enabled`），只记录、不判不合格 |
| `INCUMBENT_NOW_VALID`／`INCUMBENT_KEPT` | 恢复合法／默认关闭下只记录不收回 |
| `INCUMBENT_RETRACT_WAIT_SELF_GRANT`／`INCUMBENT_RETRACT_BEGIN`／`INCUMBENT_RETRACT_PENDING`／`INCUMBENT_RETRACT_FAILED` | P3 各阶段：等待补授开关、开始收回、写回落待补授、收回失败 |
| `RETRACT_UNQUALIFIED_ENABLED`／`RETRACT_UNQUALIFIED_DISABLED` | 强制收回开关切换 |
| `CIVIL_LAW_ENSURED` | 文官路补挂任命法（仅在补法开关开启时） |
| `CIVIL_LAW_ENSURE_ENABLED`／`CIVIL_LAW_ENSURE_DISABLED` | 文官补法开关切换 |
| `MULTI_ROAD_AUDIT_ENABLED`／`MULTI_ROAD_AUDIT_DISABLED` | 一人多路信息记录开关切换 |

P0 只负责把授予／继任路径与持有人功绩落到日志，不改变任何头衔状态；具体探针结论与未留痕字段见[设计页](circuit_succession_design.md#待验证与风险)。

### 幂等与性能

- 审计按 `tca_circuit_audit_reported` 去重：同一次低品只记一次日志；恢复合法后清除，可再次记录；重复调用只更新稳定变量值，不重复排队。
- 可选兼任信息按 `tca_circuit_multi_road_reported` 去重；开关关闭时清除该标记，避免旧诊断被当作待办。
- 审计只在"已登记路 + 天朝封臣持有人 + 无回落待补授"时工作，且先判资格再写状态；默认关闭路径不写 `tca_circuit_incumbent_pending`。
- 维护先在轻量循环里同步类型并审计，只有 `tca_circuit_needs_maintenance_trigger` 成立时才进入维护事务，且只有 `tca_circuit_needs_candidate_pool_trigger`（确有需要季度预清的路，或已开启自动补授且有待补授／待收回）成立时才从皇帝侧收集候选池；候选入池前先按功绩等级下限（默认只收五品以上）短路过滤。
- 季度巡检范围只覆盖登记路；年度重建从 h_china 侧只遍历皇帝本人及直属的王国级封臣（`every_vassal` + `highest_held_title_tier >= tier_kingdom`），不下探到州、县或无地官署。

## 与其它模块的边界

- 路的继承法、原生评分与正常继任仍归原版；本机制只在原生无有效顺位后介入。P1 不复制原生评分与排序。
- 提刑／通判等无地官职只在旧头衔层按其自身 `current_heir` 转交，生命周期、绑定与专职资格仍由所属模块维护。
- 司法辖区、通判辅佐、官署经费按现任持有人实时读取，补授后通过既有维护重接；本机制不直接改这些模块的绑定。
- 官品／功绩只读不改：审计读取原生 `merit_level`，不读、不改核定官品；生成角色按头衔等级起始功绩入仕。考试、退休、致仕加恩、年度升品不阻塞审计或补授，也不替它们结算。
- 文官路补挂任命法是补法而非新法：不复制官品／考试规则，不给军区／都护补民政任命法；原生 `appointment_title_value` 等评分覆盖仍由原版基线维护。
- 一人多路按"兼任不干预"处理：不改变原生"同级可竞争"的法律与授予结果，不拆分既有兼任；可选信息记录默认关闭且不进入处置链路。
- 文官补法是可选"补充等效"，默认关闭；开启后也不追溯既有继承结果。

## 验收与限制

自动回归按项目测试规范登记，运行方式：

```sh
python3 tools/run_game_tests.py --suite circuit_succession --timeout 900
```

既有 4 个 circuit 用例此前的正式回归结果（独立 1066 观察者局）：23 条断言全部通过，观察者确认、未检出模组相关引擎错误。覆盖：

- 旧头衔按 `current_heir` 交接（含继承人非升迁者本人、`top_liege` 属皇帝侧的断言）；
- 排除清单：奉祠／致仕、辞谢／拒任、中央大臣；
- 季度预清：真实候选写入近期冷却与标记 → 排除项不清、解除后清、冷却归零、标记移除；
- 默认关闭自动补授的开关行为：路回落皇帝后仅记录 `SELF_GRANT_DISABLED`，pending、登记与 kind 保留，holder 不变。

本轮用例已按新政策更新登记：`.13`（继承顺位等级门槛，7 断言）、`.14`（在任等级审计，7）、`.15`（一人多路仅信息记录，5）、`.16`（默认保留，8）、`.17`（强制收回开关存在时一人多路也不得判不合格或收回，4）、`.18`（文官补法需显式开启，3），均 `EXCLUSIVE`、`GROUP = tca_circuit_succession_test`。

`--list` 当前为 **10 个用例、57 条断言**（既有 `.4`/`.6`/`.8`/`.11` 与上述新增用例之和）。本轮策略修订后的定向回归结果（独立 1066 观察者局，`--suite circuit_succession`）：**10 个用例、57 条断言全部通过**，`SUITE_ALL_PASSED`、观察者确认、未检出模组相关引擎错误；`.13`–`.18` 均为新语义（`.15` 一人多路仅信息记录、`.17` 强制收回开关存在时也不判不合格/收回、`.18` 显式开启补法开关）。此前的旧用例语义与断言数已被本轮策略更新取代。

自动补授默认关闭后，以下场景不在正式回归内（实现与失败用例快照保留，待引擎安全授予方案后再启用并补充）：

- 真实无地候选自授（`fill_lapsed`／`handle_pending` 自授入口）；
- 生成兜底的两段式授予；
- 旧头衔无地无家门继承人的交接与递归生成；
- 都护 `kind = 3` 契约、GUI 显示、真实 AI 长期行为与保存重载仍属人工验收范围。

已确认的引擎事实（独立 1066 观察者测试局）：

- 回落转移类型为 `flag:inheritance`，正常任命继任为 `flag:appointment_succession`；`scope:previous_holder` 为已死前任；头衔持久变量跨持有人变更保留。
- 回落后约 1 tick 内 AI 以 `flag:appointment` 再授予；原生任命写 `appointment_timeout_days`（1825 起递减），`clear_appointment_timeout` 恢复原生按级候选。
- 候选耗尽时 `current_heir` 与 `any_title_heir` 只剩领主；无地候选人的 `top_liege` 等于皇帝，皇帝侧结构遍历与全世界按 `top_liege` 过滤的人物集合一致。
- 有地头衔授予无地接收者必须用 `change_title_holder_include_vassals`；普通 `change_title_holder`（无论 granted 还是 appointment）会销毁目标头衔。
- 引擎对"真实角色的无地接收者"脚本授予有地头衔不稳定：同 tick 新建家门、跨日准备后均实测过目标头衔被销毁；已持有家门头衔的接收者可同 tick 成功。因此当前实现只对"已有家门头衔（或已有地）"的候选做自动补授，无家门无地的真实候选不进入抽选；生成角色走"准备→次日授予"两段式并有通过记录。
- 独立存档只读核对：路主可在九品持有王国级路且 realm law 为任命继承；自动继任顺位可出现低品亲属（第一顺位七品）；同一人可同时持有两套"路＋法理公国"。
- 原生互动层的 `has_appointment_level_for_title` 在"目标头衔由皇帝持有"的空位语境下不可用；本机制的候选等级门槛改用等价的头衔等级下限（王国 5／公爵 3／伯爵 1）。

已知限制：

- 无家门头衔的无地真实候选人暂不自动补授（在抽选中跳过），由生成兜底或下一轮处理；旧头衔继承人同样要求"已有地或已有家门"，否则按无可用继承人走递归／生成。该限制来自引擎脚本授予行为，原生任命与第一层预清不受影响。
- 两段式授予依赖次日维护入口解锁；队列事件异常丢失时由季度脉冲兜底。
- 在任审计的默认配置只记录低品问题，不纠正；P3 强制收回依赖"收回＋改授"引擎安全方案，尚未验证。
- 一人多路按"兼任不干预"处理；可选信息记录阈值默认 1 只是诊断值，不构成"一人一路"规则，也不进入处置链路。

仍需引擎回归或人工验收：

- P0 探针：`on_title_gain` 现会打印作用域，但王国级头衔的 `transfer_type` 与持有人功绩尚未单独核对；取得路径仍只能从任命法、授予方式与时间线反推。
- P1：低品／亲属第一顺位被判无效后，季度预清是否总能恢复原生候选；需确认不会把原生确实可继任的顺位误判为无效。
- P2：审计日志规模、恢复合法后的标记清理、季维护与持有人变更两条路径的重复记录行为；可选兼任信息默认关闭，开启后需观察记录频率。
- P3：只针对低品在任者的收回＋改授引擎安全性、失败后的头衔状态与恢复路径；一人多路不进入收回链路，默认关闭，不作为本轮验收重点。
- P4：默认关闭时是否完全无副作用；显式开启后 `add_realm_law_skip_effects` 的生效时点、继承面板刷新与保存重载后的法律状态。
- 本轮策略修订后的定向引擎回归已通过：10 用例／57 断言、`SUITE_ALL_PASSED`、观察者确认、无模组相关引擎错误；全量回归、保存重载与人工界面仍未验收。
- 都护契约 `level = 4` 是否被契约 `is_valid` 接受；实现已准备"回退军区 `level = 3`"的兜底，回退本身待验证。
- 有地候选人旧头衔交给 `current_heir` 后的领主链与法理效果；实现不显式改旧头衔领主。
- 授予事务内 `has_subject_contract_group` 的可读时点；合同组未建立时保留原类型、下一季度重试补约。
- 递归在真实规模下的性能与链式任命体量。
- 保存重载：头衔标记、全局登记、回落待补授与审计状态、冷却的恢复。
- 真实 AI 长期行为、与其他模组同时追加 `on_title_gain` 的加载顺序、玩家为皇帝时的观感；第一版不发通知。
- 客卿／寄宿者不进入候选池，与"同一天朝"的 `top_liege` 口径一致；原生候选池是否包含这类人物未单独验证。

性能：候选池只在 `tca_circuit_needs_candidate_pool_trigger` 成立时从皇帝侧收集，且入池前先按功绩等级短路；审计与类型同步只遍历登记路；年度重建从上到下只遍历皇帝与直属王国级封臣，仅用于登记兜底。

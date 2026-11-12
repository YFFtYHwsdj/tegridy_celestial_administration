# 路主任命继承补授：本轮计划

状态：本轮政策已定型：P0 诊断日志、P1 继承顺位资格、P2 在任资格审计默认启用；P3 强制收回只针对低品在任者，默认关闭；P4 文官补法改为默认关闭的可选开关；一人多路按"兼任不干预"处理，只提供默认关闭的信息记录；季度预清冷却覆盖 `0 < appointment_timeout_days <= 1825` 全区间（含衰减至 3 年内的原版受任冷却）。规则正文见[设计](circuit_succession_design.md)，接口、状态、开关与日志见[实现入口](circuit_succession.md)。

## 本轮范围

| 阶段 | 内容 | 默认 | 状态 |
| --- | --- | --- | --- |
| P0 诊断 | `on_title_gain` 两分支打印作用域与 `TITLE_GAIN_*`；预清入口记录 `HEIR_LEVEL_LOW` | 启用 | 日志已接入；探针未运行，王国级 `transfer_type` 与持有人功绩尚未核对 |
| P1 继承顺位资格 | `has_valid_heir` 要求 `current_heir` 存活、非领主且满足头衔等级；不合格顺位按无效处理，进入预清／审计 | 启用 | 已接入；`.13` 引擎回归通过 |
| P2 在任资格审计 | 只判官品低于头衔等级，写 `tca_circuit_incumbent_invalid = 1` 与去重日志；一人多路不判不合格 | 启用 | 已接入；`.14`–`.17` 引擎回归通过 |
| P4 文官路补挂 realm law | 需显式开启 `tca_circuit_civil_law_ensure_enabled`；`kind = 1` 的已登记路缺 `celestial_appointment_succession_law` 时补挂，季度维护重试 | **关闭** | 已接入；默认不执行，引擎生效时点待验证 |
| P3 强制收回 | 只针对官品低于头衔等级的在任者；双开关才收回，无多头衔收回分支 | **关闭** | 最小路径已接入；引擎安全授予未验证，不作为本轮验收重点 |
| 一人多路 | 兼任不干预：不写 invalid／pending、不收回；可选开关 `tca_circuit_multi_road_audit_enabled` 仅记录信息 | 不干预（信息记录关） | 已接入；`.15`／`.17` 引擎回归通过 |

不在本轮范围：

- 自动补授（自授、收回再授、生成两段式、旧头衔递归）仍默认关闭，等待引擎安全授予方案；
- 不拆分既有兼任，不设"一人一路"；P3 不处理多头衔；
- P4 不默认开启、不追溯既有继承路径；
- 玩家通知、界面文案、旧存档批量迁移。

## 默认开关与前置条件

- `tca_circuit_self_grant_enabled`：自动补授总开关，默认不存在＝关闭；调试入口 `tca_circuit_enable_self_grant_effect`／`tca_circuit_disable_self_grant_effect`。
- `tca_circuit_retract_unqualified_enabled`：P3 强制收回开关，默认不存在＝关闭；调试入口 `tca_circuit_enable_retract_unqualified_effect`／`tca_circuit_disable_retract_unqualified_effect`，开启时先清空审计状态再重扫。
- `tca_circuit_multi_road_audit_enabled`：一人多路信息记录开关，默认不存在＝关闭；调试入口 `tca_circuit_enable_multi_road_audit_effect`／`tca_circuit_disable_multi_road_audit_effect`；只记录，不处置。
- `tca_circuit_civil_law_ensure_enabled`：文官补法开关，默认不存在＝关闭；调试入口 `tca_circuit_enable_civil_law_ensure_effect`／`tca_circuit_disable_civil_law_ensure_effect`。
- `tca_circuit_max_kingdom_roads`：一人多路信息记录阈值，默认 1；只影响可选诊断，不构成"一人一路"规则。
- P3 真正收回需要**双开关同时存在**（`retract_unqualified_enabled` + `self_grant_enabled`），且只处理低品在任者；依赖"收回＋改授"的引擎安全授予方案验证通过。P3 开启后仍可能出现头衔真空、再次回落或天命循环催化剂影响，须在独立测试局观察。
- 默认配置下的硬约束：任何路径都不得改变头衔持有人；P2 审计只写头衔持久变量与日志。

## 验收清单

自动回归（独立 1066 观察者局，按测试规范登记，先跑 `python3 tools/check_test_parallel.py` 与 `python3 tools/run_game_tests.py --list`）：

- P1：第一顺位低品／亲属 → `tca_circuit_has_valid_heir_trigger = no`，可预清路径触发；第一顺位合格时行为不变。
- P2：官品不足 → `incumbent_invalid = 1`；一人多路**不写** invalid；连续审计只记一次；默认开关下不写 pending、不改持有人；恢复合法后标记清除。
- 兼任不干预：即使强制收回开关存在、上限临时压到 0，一人多路也不得判为不合格或收回（`.17`）；可选信息开关开启时只写 `multi_road_reported` 与 `INCUMBENT_MULTI_ROAD_INFO`，不写 pending（`.15`）。
- P3 默认路径：收回开关不存在时 `handle_incumbent_invalid` 只记录并清 pending，holder 不变；双开关路径未运行。
- P4：补法开关不存在时无操作、不改任何持有人的领地法；显式开启后 `kind = 1` 缺任命法时补挂，已具备时无操作、重复调用幂等（`.18`）；不改军区／都护。
- 用例登记：`.13`–`.18` 按 `EXCLUSIVE`、`GROUP = tca_circuit_succession_test` 登记；定向引擎回归为 10 用例／57 断言全部通过。
- 既有 4 个 circuit 用例不得回归失败，不放宽断言；默认关闭的自动补授、P3、P4 与可选信息记录路径不改变任何头衔持有人。

命令（需图形会话与 Steam；环境不许可或尚未执行时记"未执行／待引擎复现"，不得写通过）：

```sh
python3 tools/run_game_tests.py --suite circuit_succession --timeout 900
```

定向之外，仅在共享接口或默认行为变化确有影响时扩展受影响组；按[项目测试策略](../../AGENTS.md#测试与验证)优先并行，以最小充分范围验收，不例行补跑K=1或全量。

## 剩余工作

1. **定向回归已跑通**：`--suite circuit_succession` 10 用例／57 断言全部通过、`SUITE_ALL_PASSED`、观察者确认、无模组相关引擎错误；全量回归仍待收口时执行。
2. **P0 探针复现**：在独立观察者局打印 `on_title_gain` 的头衔、`transfer_type`、前任与持有人功绩，确认王国级授予／继任路径；现有日志只补了作用域，尚不能直接定案。
3. **P3 引擎安全验证**：只针对低品的收回＋改授在 `granted` 事务下是否销毁头衔、失败后的恢复路径；验证通过前保持默认关闭。
4. **P4 默认关闭验证**：确认开关不存在时完全无副作用；显式开启后 `add_realm_law_skip_effects` 的生效时点、继承面板刷新、保存重载后的法律状态。
5. **兼任信息记录**：默认关闭；开启后观察记录频率与日志规模，确认不进入不合格处置链路。
6. **旧存档与保存重载**：待补授、审计标记、可选诊断标记与开关的恢复；不追溯历史资格问题。
7. **人工验收**：头衔窗口与人物面板显示、真实 AI 长期行为、与其他模组 `on_title_gain` 的加载顺序、玩家为皇帝的观感。
8. **政策变更**：若未来要"一人一路"或默认开启补法，需单独设计授予拒绝、旧头衔交接、兼容与回滚方案，并先验证引擎安全路径。

## 交接入口

- 规则、处理顺序、在任审计／兼任／补法三节与验收边界：[circuit_succession_design.md](circuit_succession_design.md)
- 文件、trigger／effect 名称、持久状态、开关默认值、日志前缀、幂等与性能、验收与限制：[circuit_succession.md](circuit_succession.md)
- 原版任命法律、功绩门槛与排序依据：[vanilla.md](vanilla.md)
- 引擎回归用例与模块登记：`events/tests/tca_circuit_succession_test_events.txt`、`common/scripted_effects/tests/modules/tca_test_modules_circuit_succession_effects.txt`
- 同名追加与覆盖登记：`tools/upstream_overrides.json`

本轮定向引擎回归已通过（10 用例／57 断言），全量回归、保存重载与人工界面仍待收口验收；后续结果回写[实现入口](circuit_succession.md#验收与限制)。

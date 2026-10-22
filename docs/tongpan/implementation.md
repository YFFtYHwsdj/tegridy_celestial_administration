# 通判实现与验证

规则、费用和评分以[模块说明](README.md)为准。

## 实现入口

- `common/script_values/appointment/tca_tongpan_appointment_values.txt`：绑定州的任命重要度；`common/script_values/appointment/zz_tca_appointment_values.txt`在既有原版覆盖内按官署标记分流，保留提刑和其他头衔算法。中英文重要度分项由 `tca_tongpan_prominence_l_*` 提供。
- `tools/build_tongpan_catalog.py`：3,442个固定官职、128个池官职、固定映射、限定官职的持有人称谓和双语名称；不含测试生成。
- `common/scripted_effects/tca_tongpan_effects.txt`：绑定、三级挂靠、本职原生评分补位、destroy与恢复、角色分权同步和皇帝级维护。
- `common/scripted_triggers/tca_tongpan_triggers.txt`：实际政权与伯爵主头衔资格、专职校验、双向绑定与生效条件。
- `common/laws/tca_tongpan_laws.txt`、`common/law_groups/tca_tongpan_law_groups.txt`：皇帝级开关、费用、冷却和开局默认。
- `common/diarchies/`、`common/script_values/tca_tongpan_values.txt`：单使命、称职度、0/20/40/60/80档位和数值。
- `common/on_action/tca_tongpan_on_actions.txt`、`events/tca_tongpan_events.txt`：原生回调追加维护，合并到次日；季度及年度补查。
- `common/script_values/zz_tca_tongpan_native_values.txt`：原版治理效率与四项威望附费的包装；保留原生治理效率0.5—1.5总上限。
- `common/character_interactions/zz_tca_tongpan_action_costs.txt`：原版四项互动追加影响力费用，代理操作沿用原版承担者路径；本模组两项司法拘捕入口也追加费用。
- `common/on_action/diarchy_on_action.txt`：修正原版退出分权时直接读取已故旧分权者变量的问题。仅给共治头衔变量分支增加存活检查，其余四个回调原样保留；采用同名文件遮蔽，避免多个effect定义的加载错误。五个对象均登记并保留原版基线。

新增同名原版对象及追加回调已登记 `tools/upstream_overrides.json`；原版主体保存在已审阅基线／原样helper中。影响力需要覆盖整个互动对象，兼容范围大于仅追加数值的威望适配。

原版不允许给无持有者头衔查询任命分数；原版`celestial_appointment_succession_law`属于realm法，不能直接当作官署title法安装。因此首次／纠错时在同一次效果内先由挂靠上级暂持官职，安装通判官署头衔法，再按本职引擎分数抽选并立即授予专职人选。有效在任者不经过暂持步骤。此处的原生头衔回调可能被其他模组观察到，属于需要兼容验收的边界。

补位使用`granted`事务精确授予已抽中的人，避免`appointment`事务再次使用原版缓存继承人。持有者保留原版realm文官继承法，官署的独立title法决定本职评分；精确补位后只为最终官员补齐原版任命冷却，不缩短更长超时、不冷却临时上级，日常维护不续期。正常死亡交接不走初始加权补位。具体共用入口见[官职任命](../appointment/README.md#实现入口与验收)。

分权资格复用`is_diarch_valid_trigger`，可履职状态复用`is_diarch_able_trigger`，对应原版`scripted_rules/00_rules.txt`。原版资格失效时暂停分权，保留官职；恢复后维护重新连接，不另造特殊状态资源或代理职位。

## 资源与生成资产

`tools/build_tongpan_catalog.py` 从安装游戏的 `game/` 目录生成固定官职、预留池、索引和双语名称。不要逐条修改生成文件；扩充池时同步审阅初始化迁移。历史人物快照位于 `common/scripted_effects/tca_historical_character_registry.txt`，用于首次／纠错补位排除，正常原版继任不因此排除合格历史人物。更新名单需重新审阅来源；当前没有重建该快照的工具。

## 自动验证与尚未解决的问题

任命重要度单项：`python3 tools/run_game_tests.py --case tca_tongpan_prominence_test.1 --timeout 600`。用例自建无地公爵数值夹具，故意使官职定位与绑定州不同，检查首都同址、远距归零、缺绑定、空缺官职、提刑分流及原版回退；该夹具不验证伯爵官职生命周期。完整通判组使用 `--suite tongpan`，其中生命周期场景检验真实伯爵官职。重要度浮窗的双语显示、实际职位调任及保存重载仍需人工验收。

运行 `python3 tools/run_game_tests.py --case tca_tongpan_test.1 --timeout 600`；当前 `tca_tongpan_probe_test` 验证预定义无地伯爵的同僚分权；被拒绝的动态创建源码单独归档，不能把两者视为同一失败到通过场景。登记、结果与计数以该次冻结计划为准，不在本文手填总数。

### 未解决的生命周期一致性

已有全组运行出现生命周期断言失败，单项运行未稳定复现；根因尚未确认。历史报告只能提供调查线索，不代表当前源码一定复现，也不能因某次单项通过认定已修复。检查源为 [原生生命周期用例](../../events/tests/tca_tongpan_test_events.txt)：

- 断言28：主管改制退出再恢复后，原官署绑定、有效专职持有人及活动分权应一致。
- 断言46：死亡当下实际继任者应属于死亡前枚举的头衔候选名单；曾出现名单外继任。候选枚举人数与原版搜索门槛相符不足以证明截断或缓存就是原因。
- 断言56：临时边界场景清理后，原主管、原官员和分权关系应恢复，避免影响后续用例。

复核时在独立1066中国观察者局，以相同种子比较完整同局和单项：

```sh
python3 tools/run_game_tests.py --seed 1538798675 --timeout 600
python3 tools/run_game_tests.py --case tca_tongpan_test.1 --seed 1538798675 --timeout 600
```

比较失败时的绑定头衔、实际持有人、领主、候选及分权关系，检查前序用例清理和原生回调顺序，不通过事后维护或放宽断言覆盖差异。严格首位继任另用 `--strict-title-heir`；普通名单成员检查不证明预览首位必然接任。

## 人工与真实路径验收

准备：专用1066debug局，仅加载本模组；选择一个法律启用且主管、通判有效的州，记录州与官署ID、实际领主、持有人、分权者、天平和治理效率。启停测试要满足正式改革资格、资源和冷却；使用可丢弃副本分别验证不同路径，不以直接改变量绕过门槛。

1. 首次暂停时查看官职及分权。预期：有且仅有绑定官署，通判与州主管关系有效。通过真实法律界面关闭制度，官职撤任、分权结束但保留绑定；满足条件后重启应复用原官署，不遗留加成。尚未走到冷却结束只记录关闭路径。
2. 分别以通判和知州查看关系窗口。预期：自身、领主、所辅佐知州标签选中互斥，窗口目标与官员相符；头衔窗口和分权窗口的继任名单顺序一致。普通摄政和首辅仍显示原版使命，悬停没有丢失上下文或空白。
3. 查看忠诚度、称职度和治理效率分项。预期：读到所辅佐主管，最终效率仍受原生0.5至1.5限幅；换任或退出后旧主管不残留加成。评分规则以[模块说明](README.md)为准，不从截图合计反推全部计算。
4. 在独立副本逐一真实发送拘捕、处决、撤销及收回封臣，记录发送前后的资源、天平及原生费用。预期：附费来自对应档位，取消或未发送无额外扣款，同一行动不重复收取。只做处决不能覆盖另外三类；代理操作分别记录实际付款者。
5. 保存重载后复查同一ID、绑定、持有人、分权及费用；连续死亡、调任、路／政事堂回退、跨政权、地图扩展和池耗尽各自建立场景。没有准备的边界保持未覆盖，不由池分配单项推定扩展地图兼容。

当前上述真实路径及画面仍待验收；实际错误、重复对象、残留状态或相关引擎错误都阻止对应项目通过。所测语言、缩放和角色视角应明确记录。

GUI探针 `python3 tools/run_diarchy_ui_probe.py --timeout 180` 验证固定场景的真实窗口目标及正式表达式，完整边界见[测试运行](../testing/README.md)。它不证明不同玩家角色、实际鼠标、全部缩放与保存重载均已验收。

## GUI维护约定

三个关系标签直接读取正式角色对象：自身使用 `IsLocalPlayer`，领主与所辅佐知州使用 `.Self` 对象比较，并排除玩家自身，保持选中互斥；不另存选中状态。通判继任行直接读取绑定官署头衔的原生名单，不以称职度重新排序。

使命提示按分权类型使用互斥文本节点：普通分权直接求值字面键 `DIARCHY_WINDOW_MANDATE_TOOLTIP`，通判使用自身键，不能用 `SelectLocalization` 间接展开而丢失 `Mandate` 数据上下文。普通分权保留全部原版使命及权限，通判非主管仅显示当前使命的只读图标。精确本地化键的错误归属由覆盖清单的 `diagnostic_localization_keys` 维护，不能把所有原版错误都算作模组问题。

# 1066 固定提刑机构

## 目的与当前行为

2026-10-11：把原版 1066.9.15 开局的 15 个文官路对应的提点刑狱司定义为固定无地公国头衔，便于独立维护历史人物、任期和初始状态。机构定义与人物考证分开：头衔历史调用通用 `tca_bind_judicial_circuit_effect` 声明所属路，当前不编造任职者；`holder = 0` 只是未填人物的占位，不断言史实空缺。

固定定义不包含下属州县，不授予土地，也不增加官署建筑。历史尚无人时，退出大厅后的既有补位流程仍选任非历史的合格文官，无候选人时生成角色；本次并未增加可在大厅直接选择的历史提刑人物。

固定对象只在 `game_start_date = 1066.9.15` 的游戏中优先使用。该条件读取开局日期，推进年份后仍能恢复同一固定官职。867、1178 等其他开局维持原有动态机制，不把本名单视为那些日期的历史机构清单。固定数据库定义本身在所有开局均可被引用，定义存在不等于已经授予持有者。

## 15 路与固定 ID

- 河南：`k_henan` → `d_tca_judicial_henan`
- 河东：`k_hedong` → `d_tca_judicial_hedong`
- 青徐：`k_qingxu` → `d_tca_judicial_qingxu`
- 淮南：`k_huainan` → `d_tca_judicial_huainan`
- 江东：`k_jiangdong` → `d_tca_judicial_jiangdong`
- 江西：`k_jiangxi` → `d_tca_judicial_jiangxi`
- 两浙：`k_liangzhe` → `d_tca_judicial_liangzhe`
- 福建：`k_fujian` → `d_tca_judicial_fujian`
- 山南：`k_shannan` → `d_tca_judicial_shannan`
- 湖南：`k_hunan` → `d_tca_judicial_hunan`
- 西川：`k_xichuan` → `d_tca_judicial_xichuan`
- 东川：`k_dongchuan` → `d_tca_judicial_dongchuan`
- 兴元：`k_xingyuan` → `d_tca_judicial_xingyuan`
- 夔州：`k_kuizhou` → `d_tca_judicial_kuizhou`
- 岭南：`k_lingnan` → `d_tca_judicial_lingnan`

此名单对应游戏头衔和契约抽象，不等同于史实宋代路制。

## 原版依据（本机声明版本 1.20.0.4）

- `game/history/titles/e_china.txt`：按 1066.9.15 累积历史，18 个王国级头衔的持有者为天朝政府，直属 `h_china`；未发现这些持有者兼持帝国或天下级头衔。
- `game/common/on_action/game_start.txt` 的 1066 分支：河北、关内、岭西设为军区；河北重复调用一次，不是第四个辖区。
- `game/common/scripted_effects/10_dlc_tgp_history_effects.txt`：`tgp_make_military_celestial_provinces_effect` 设置军事契约（level 3）及军事任命法。
- `game/common/subject_contracts/contracts/celestial.txt`：标准类型默认，标准、工业及都会类型属文官；现有模组适用条件排除军事与都护契约。
- `game/common/landed_titles/_landed_titles.info`、`02_china.txt`：静态无地属性、首府、宣称和销毁设置的实际语法。首府来自所属路定义；河南使用其 1066 历史设置的汴州，运行时继续随所属路首府刷新。
- `game/history/titles/e_goryeo.txt`：历史日期的 `effect` 可用 `set_variable` 保存 `title:k_*` 引用；`01_laamp_titles.txt` 在头衔历史中调用 scripted effect。参数替换语法参照 `common/scripted_effects/00_debug_and_shortcut_effects.txt`。这些只确认写法，不证明无人机构历史效果必定执行。
- `game/history/titles/01_admin_titles.txt`：原版有 `holder = 0` 的无人历史状态。这仅提供语法依据，不代表家族继承适合司法官职。

## 实现入口与旧存档

- `common/landed_titles/tca_judicial_titles.txt`：15 个独立顶层定义，不嵌入原版路的法理层级。
- `history/titles/tca_judicial_titles.txt`：每个机构在 1066.9.15 的 `effect` 中以 `CIRCUIT = title:k_*` 声明对应关系；人物留空，不覆盖原版头衔历史。
- `common/scripted_effects/tca_judicial_static_title_effects.txt`：通用绑定器在官职作用域接受 `CIRCUIT` 参数，设置路上的 `tca_static_judicial_title` 备用引用，并在没有有效现职绑定时建立双向引用和登记。既有动态绑定不被覆盖。标记 `tca_judicial_static_title` 只表示固定对象来源。
- `common/scripted_effects/tca_judicial_title_effects.txt`：有效双向绑定优先；无绑定时清除临时官职作用域，先查固定对象，再动态创建。固定对象通过路上的备用引用直接读取，不再按路 ID 执行 `if / else_if` 查找；两者随后共用任命和身份维护。
- `localization/{simp_chinese,english}/tca_judicial_static_titles_l_*.yml`：无人且尚未初始化时也有静态机构名及形容词；运行中使用稳定的机构本地化键，通过GetTitleByKey读取所属路当前名称；旧动态机构属于这15路时也使用同一键。

旧存档已有有效动态绑定时保留对象、现任官员及囚犯记录，不自动迁移到固定对象。旧存档不会重新执行头衔历史；全局维护先执行一次有界补接清单，每个固定机构一行，调用与历史相同的通用绑定器。它也兜底处理无人头衔未执行历史效果的情况。无有效绑定时才接入固定对象；新定义能否在旧存档加载时被完整纳入仍待验证。其他路仍动态创建。补接清单仅在 1066 开局执行，并由 `tca_static_judicial_bindings_v1` 标记限制为每存档一次。修改或新增历史映射时须同步该清单。

废置时先交接公职囚犯，再销毁当前持有状态；动态与固定官职均保持 `delete_on_destroy = no`，不解除双向绑定或移出登记列表。显式废置保留 `tca_judicial_disabled`，季度、年度与延迟维护均不补位；恢复复用原 ID。暂时转出适用制度的路也保留官职，恢复文官路时复用。

本次只新增独立定义和修改模组自己的效果，不新增原版同名覆盖或扩展，不需新增覆盖登记。

## 后续补入历史人物

在 `history/characters/` 增加或引用经过考证的角色，在对应固定头衔的日期块中填写 `holder`、天朝 `government` 和所属路 `liege`，保留通用绑定效果。有更早任期时需移除或调整现有 1066.9.15 的 `holder = 0`，避免覆盖有效任职。不能只增加人物而不授予官职。

记录史料依据、日期可信度与原版人物 ID 是否复用。历史人物的政府、家族、功绩及任命继承仍应检查；现有补位算法保留合格在任历史人物，但不会把其他历史人物随机抓来填空。史料明确的空缺与尚未考证的任职者应分别记录。

## 验证与待验证

2026-10-11 已完成静态检查：

- 15 个定义、历史条目与绑定映射一一对应，未纳入河北、关内、岭西；所有首府引用均存在于本机原版。
- 新增及修改脚本的括号和顶层定义解析通过；中英机构名与形容词键一致，本地化 UTF-8 BOM 保留。
- `python3 tools/check_upstream_overrides.py` 通过：5 个原版覆盖基线匹配，14 个附加 on_action 已登记。
- `python3 tools/scan_upstream_overrides.py` 通过：无未登记同名对象、过时登记或同路径脚本覆盖。
- `git diff --check` 通过。

以上是静态验证；新固定头衔尚未完成引擎加载或游戏内行为验证。验收步骤：

1. 重启游戏，1066 新开局：先在大厅检查历史效果是否已经设置机构标记和路上的双向引用；退出大厅后会有补接兜底，因此不能用退出大厅后的成功反推历史效果已执行。退出大厅并推进两天：15 路绑定应分别指向上述固定 ID；河北、关内、岭西没有提刑绑定。检查日志中的标题历史、无地首府、作用域及本地化错误。
2. 重复维护：固定 ID、现任人物及囚犯登记不变化，不额外创建同路动态官职。查看机构名、称号、首府和直属路关系。
3. 保存后重载：核对双向绑定、现任者、天朝文官任命法与固定 ID。
4. 对一个路显式废置，推进年度维护：不补建；再恢复：复用同一固定 ID，验证重新授予成功。检查死亡继承不销毁职位。另对动态官职重复本步骤，确认 ID、双向绑定及登记也保留。
5. 载入已有动态官职的 1066 测试存档：已有绑定、持有者与囚犯归属不迁移，不额外激活固定官职。
6. 867、1178 新开局：仍使用动态创建；1066 开局中的未列入辖区如之后转为合格文官路，仍动态创建。
7. 人物史料补齐后，再独立验证大厅选人及历史持有者不会被补位流程替换；本次未执行该项。

## 销毁与删除的区别及本次变更

当前规则补充（2026-10-15）：官署对象及原路绑定仍保留，但停用、废置和销毁时不再留在真实路法理树中；恢复时才重新挂回。引擎内部仍有退役父引用，不等于直接清空父字段。最新引擎验证及待验保存重载见[法理停用记录](judicial_de_jure_probe.md)。

原版 `_landed_titles.info` 将 `delete_on_destroy` 列为独立属性：销毁时是否删除头衔。`destroy_title` 撤销当前持有状态；关闭删除标记时保留对象，未来可再授予。开启删除标记则可移除动态对象，需要另建，不适合持续机构。`destroy_on_succession` 决定继承时是否销毁，与删除标记不同。

2026-10-11 初次固定头衔实现仍删除被废置的动态官职并解除固定官职绑定；现已改为两类官职均持久保留。代码不再开启提刑删除标记，销毁回调保留路绑定。过去已删除的对象无法原地恢复。外部模组主动删除官职或所属路对象也不在本模组保证范围内。

脚本保留引用、变量及登记的意图已完成，静态结构及原版覆盖检查通过；销毁后引擎能否完整保存动态无地对象及其变量，仍需验证废置、恢复、保存重载，不能由静态检查确认。

## 提交前审查修复

退休交接先清除临时 `tca_custodian`，防止所属路没有持有者时沿用另一轮的接收人。延迟捕获交接也显式排除已废置的路，避免持久绑定使停用官职被当作有效接收机构。这两项仍需结合路销毁与延迟拒捕流程进行游戏内验证。

# 已终止实验与引擎边界

这些结论按当时游戏版本成立；恢复方案前应重新核对接口，不能当作现行待办。原完整源码和流水见[历史索引](README.md)。

## 王国级圣职区（已终止）

### 结论与加载状态

2026-10-10 结束验证，放弃将原生圣职区作为天朝提点刑狱司头衔的实现路线。测试只证明若干技术组合可以运行，不代表该机制适合天朝行政玩法。

用户在游戏中观察到：宗教圣职区与其他宗教的圣职区共同显示，并参与宗教间竞争。结合本轮已验证的宗教上级关系，以及原版圣职区的租赁、宗教互动和失配处理链，圣职区与宗教绑定过深。强行挪作天朝官职需要持续干预宗教机制，也会影响天朝自身可能采用的宗教玩法。因此不继续做正式迁移或进一步隔离实验。

已移除本次测试的头衔、人物与头衔历史、区域定义、两个事件文件及中英本地化，共 8 个文件。特别是对 `pam_clergy_events.0051/.0052` 的测试覆盖已移除，模组不再由该原型覆盖这两个原版事件。完整最终源码可从[固定Git版本](README.md)的原 `docs/clerical_region_probe.md` 附录读取，不在当前文档重复维护。正式提刑仍沿用既有公国方案。

清理在磁盘上完成；已经运行的游戏进程需完全退出后重新启动才会重新加载。历史测试存档包含原型对象，不作为清理后正式游戏的验收存档；本轮未修改或迁移存档。未修改安装游戏或 Workshop 文件。

### 原型依据

目标是验证预定义王国级无地头衔能否挂载原生圣职区并保留天朝政体。测试头衔为 `k_tca_clerical_probe`，人物为 `tca_clerical_probe_holder`，区域为 `tca_clerical_probe_region`，涵盖洪州与筠州（`c_hongzhou`、`c_yunzhou_2`）；1066 年直属 `h_china`，初始道学礼仪、天朝政体。没有给测试头衔加正式提刑标记。

本轮核对的本机版本为 1.20.0.4，参考入口均相对于安装目录 `game/`：

- `history/titles/ce3/00_ecclesiastical_titles.txt`：`d_et_toledo` 的头衔历史通过 `clerical_region = et_867_toledo_region` 挂载区域；测试使用历史挂区路径。原生动态创建圣职区接口固定公国等级。
- `common/scripted_effects/pam_effects.txt`：头衔作用域 `every_county_in_clerical_region`；人物 `superior` 可用于选择宗教互动收件人。
- `events/dlc/pam/pam_clergy_events.txt`：`.0051/.0052` 处理失配，使用文件内辅助效果 `pam_strip_personal_landed_titles_effect`。
- `gui/window_character.gui`：宗教上级头像使用 `CharacterWindow.GetCharacter.GetReligiousSuperior`，显示条件未限定教会政体；该区块的好感代码却使用 `GetLiege`，不能把头像下好感当作宗教上级好感的独立证据。
- `common/character_interactions/_character_interactions.info`：`superior` / `top_superior` 是宗教层级互动对象。
- `common/lease_contracts/_lease_contracts.info`、`00_theocracy_lease.txt`：圣职区租赁层级为寺庙承租人 → 圣职区持有者 → 信仰领袖；区域持有者按承租人领主首都确定，实际参与有教义、信仰及政体等条件。
- `common/character_interactions/pam_interactions.txt`：例如 `request_ecclesiastical_treasury_interaction` 要求发起人与收件人均具有 `government_is_ecclesiastical`，有宗教上级不等于所有宗教互动自动可用。
- 本模组 `tca_is_judicial_circuit_trigger` 排除无地类型头衔，因此原型没有进入正式提刑维护范围。

### 证据边界

### 已确认的有限结果

- 预定义王国级无地头衔可在初始状态挂载原生圣职区、覆盖指定两个县，并保留天朝政体。
- 本测试局日/月推进、一次完全退出后存档重载保持上述基础状态；修正诊断作用域后确认直属宋朝中央。
- 一次死亡交接采用功绩任命（用户界面观察），日志独立确认换人后基础状态与辖区保持。
- 原版未隔离的改宗触发失配剥离与换人；隔离 `.0051/.0052` 后，一次改宗及一天推进中原人物、天朝政体、中央直属及两县保持。
- 改宗存档再次重载后，测试官仍有教宗作为宗教上级、没有教会政体标记，并保留天朝领地继承法。
- 用户观察确认圣职区显示和竞争属于宗教玩法；这项来自用户游戏观察，未由诊断事件独立量化。

### 未验证且不再继续验证

独立官署住所生成、逐县扩区/移除、跨信仰长期稳定、实际寺庙税收与宗教互动权限、全部任命资格及调任/辞职边界均未验证。诊断 `.2` 的领地继承法检查不替代头衔任命界面检查。未找到可直接设置或清除任意人物 `superior` 的接口，但没有导出完整脚本文档，不能断言引擎绝无此接口。

结论是该路线不适合项目，而不是王国级圣职区无法加载；保留这些技术结果用于避免重复试验。

## 动态伯爵创建与通判方案

CK3 1.20.1的历史调查显示，`create_dynamic_title` 拒绝伯爵级并报告 `Tier must be greater than county`。动态失败的 [原始事件源码](tongpan_dynamic_county_probe_events.txt)保留在仓库中；重新验证时只在独立副本启用该源，核对实际加载错误与原断言，不能污染正式加载路径。

当前 [通判探针](../../events/tests/tca_tongpan_probe_test_events.txt)验证预定义无地伯爵与同级主管的分权，使用正式登记入口 `tca_tongpan_probe_test.1`，覆盖即时及七日后的关系。可运行 `python3 tools/run_game_tests.py --case tca_tongpan_probe_test.1 --timeout 600`。它与动态失败是两个不同场景；静态头衔的首府及 `delete_on_destroy` 应在定义中声明，不调用仅适用于动态对象的setter。

因此正式通判使用预定义官职加预留池，仍保持伯爵级及同僚隶属，不提高官阶规避问题。当前实现见[通判](../tongpan/README.md)；静态探针不覆盖真实死亡继任、长期治理、全部费用或保存重载。

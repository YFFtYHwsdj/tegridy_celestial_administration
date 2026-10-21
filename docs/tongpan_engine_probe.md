# 通判引擎可行性实验

## 当前结论（2026-10-15）

本机安装版本1.20.1（Crozier，已核对`launcher/launcher-settings.json`）中，`create_dynamic_title`拒绝伯爵级头衔。已暂停按原动态方案接入法律、自动生成及正式分权数值。不得将下面的预定义头衔诊断当成动态创建已修复，也不擅自将正式通判等级改为公爵。

预定义伯爵级无地头衔的同公国同僚分权已通过即时及七天后断言，实际隶属和法理关系保持。它区分了“创建接口限制”和“分权关系限制”。这只是debug专用夹具，不是正式官职，也不会在普通开局自动授予；路级／政事堂挂靠、真实死亡继任、治理与费用、保存重载均未由此验证。

## 动态创建失败

入口：`python3 tools/run_game_tests.py --case tca_tongpan_probe_test.1 --timeout 240`。

独立1066中国观察者局，只加载本模组与CLI适配模组。目录：`/private/var/folders/f0/dh90nqcx6rsgf1558f91wmz40000gn/T/tca-game-tests/run-ehx_4um3`。

实际执行1项／5断言，2通过、3失败，日志工具为 `NOT VERIFIED`。`terminal.json`确认观察者切换并到达summary，`verification_exit=1`、`runner_exit=1`。错误发生在加载解析及实际操作阶段：

```text
Error: create_dynamic_title effect [ Tier must be greater than county ]
Script location: file: events/tca_tongpan_probe_test_events.txt line: 53
Error: create_dynamic_title effect [ No tier set ]
Error: create_dynamic_title effect [ Not executing due to error during read ]
```

完整原生测试源（包含原失败断言）保存在 [动态实验历史源码](history/tongpan_dynamic_county_probe_events.txt)。因该effect在加载时就报错，历史源码放在游戏不加载的文档目录，不继续污染正式加载路径；恢复复现时应使用独立工作副本，将该原生源码放回原事件路径并按原登记入口运行，不修改正确预期断言。

该次还包含夹具问题：三个`give_noble_family_title`漏写新家族头衔作用域、普通公国主管没有保留实地县导致头衔准备失败，以及新脚本缺UTF-8 BOM。因此两项分权断言通过不证明合法的同僚分权已经成立。上述夹具问题在新的静态头衔诊断中修正；动态创建错误是独立的加载期限制，没有因此消失。

此前另一次沙箱运行 `run-reombhjm` 在Steam初始化前退出，无观察者、无用例执行，不计为引擎实验结果。随后在允许macOS图形会话访问的环境重试才取得上面的实际结果。

## 静态头衔诊断

原生源：`events/tests/tca_tongpan_probe_test_events.txt`；用例名：`tca_test_tongpan_static_peer_diarchy`。入口仍为`tca_tongpan_probe_test.1`，名称刻意与动态失败用例区分，不能将新场景通过写成旧动态场景从失败到通过。

- `common/landed_titles/tca_tongpan_probe_titles.txt`：仅一个预定义伯爵级无地测试头衔。
- `common/diarchies/diarchy_types/tca_tongpan_probe.txt`：仅由debug测试角色标记允许启动的分权类型；没有额外权限或数值。
- 三个新建人物，公国主管保留一个实地伯爵领；受监督主管与无地官职同为伯爵级且直属该公国主管。
- 原生调用`try_start_diarchy`、`set_diarch`；核对即时关系、天朝文官继承法，以及七天后分权与实际／法理关系。不会把通判改成伯爵主管的封臣来获得通过。
- 测试登记为串行延迟组最后一项；当前源码116项／579断言，其中通判诊断5断言。此前完整组115项／574断言的通过记录不覆盖本次新增内容。

### 夹具配置修复前

单项局`run-4mfxptpu`执行1项／5断言，全部断言通过，但`error.log`有静态头衔缺首府与纹章生成条件，以及`set_delete_on_destroy`用于非动态头衔的错误，日志核对为`NOT VERIFIED`，不计为通过。后续在静态定义补充首府及颜色，并删除仅适用于动态头衔的setter；`delete_on_destroy = no`仍在静态定义保留，原五项断言未放宽。

### 修复后完整回归

入口：`python3 tools/run_game_tests.py --timeout 360`。

独立1066中国观察者局：`/private/var/folders/f0/dh90nqcx6rsgf1558f91wmz40000gn/T/tca-game-tests/run-jwaqvqvg`。当前源实际执行116项／579断言，116 PASS、579 CHECK_PASS，零FAIL、CHECK_FAIL或PRECONDITION_FAIL，包含通判5断言和既有提刑回归。

`terminal.json`确认观察者、summary终止、`verification_exit=0`及`runner_exit=0`。测试约214.8秒结束；工具在汇总后终止自己启动的游戏进程（`process_exit=-9`），不是异常提前退出。`result.txt`为`OK: all current cases passed; no detected mod-related engine errors`。

人工核对同次完整`error.log`，无`tca_`记录；仍有原版背景错误（文件679行），不能声称整个游戏无错误。工具测试100项通过；8项原版覆盖、17项追加与1项辅助扩展的基线检查通过；差异空白、测试登记、UTF-8 BOM及文档链接检查通过。此次没有新增原版覆盖或修改基线。

没有界面或保存重载验收。实际文官继任仅检查法律存在，尚未测试死亡交接；七天内成立不代表长期稳定，也不证明原生互动会正确识别非直属分权关系。

## 继续实现所需的设计变更

建议改为预定义伯爵级无地官职，再按需授予、绑定、destroy及恢复。它保留伯爵等级、法理归属、实际隶属、专职、文官继任和分权的目标，但把运行时动态创建改为预定义对象的启用。可按辖区预定义或使用预留对象池，覆盖范围、数量及扩展模组兼容须随实现明确。

这会改变原规格的创建方式，待用户确认后再实施正式法律和生命周期；本次没有默默采用此方案。

## 已核对的实现依据

- 原版`common/defines/00_defines.txt`的`APPOINTMENT_MERIT_TIER = { 0 1 1 3 5 7 9 }`及`common/script_values/10_dlc_tgp_china_values.txt`的`merit_level_expected_county_value = 1`，均指向伯爵级文官最低功绩等级1。原版中文教程称九品至八品可任伯爵，不能擅自将其细分为“从九品”。
- 原版中文`localization/simp_chinese/titles_l_simp_chinese.yml`中，`e_minister_chancellor`的名称为“政事堂”；现有司法模块也按相应朝廷的宰相席位解析中央节点。正式挂靠仍须核对其持有者属于同一天朝政权。

目前没有正式通判法律、补位或治理／费用实现；不得报告第一版已完成。

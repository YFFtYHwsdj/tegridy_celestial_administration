# 开局官员资产

正式约定见[设计](../../docs/appointment/startup_officials_design.md)。本工具维护1066／1178宋朝提刑与通判，输出原生人物、独立家族、本地化、任职历史及有界初始化索引；不生成业务测试或覆盖原版。

## 使用

```sh
# 默认只读预览；原版参数指向game目录
python3 tools/build_startup_officials.py
python3 tools/build_startup_officials.py --check
# 明确应用配置差异；先检查归属，拒绝覆盖人工文件或手改过的生成文件
python3 tools/build_startup_officials.py --write
# 游戏地图更新：先人工审阅上游差异，再预览适用范围
python3 tools/build_startup_officials.py --refresh-catalog
python3 tools/build_startup_officials.py --refresh-catalog --write
# 仅重抽一个虚构人物；人物ID保持不变，人工人物禁止重抽
python3 tools/build_startup_officials.py --reroll 1066:c_tca_tongpan_beizhou --seed 42 --write
```

`config.json`拥有开局适用职位、人工任职选择、固定种子与10%世族概率；`generated_manifest.json`拥有生成文件摘要。不要手改生成文件或用刷新清单消除摘要冲突；人工人物放 `history/characters/tca_officials_authored.txt` 等人工文件，再在配置指定 `holder`。配置的 `source` 指向考证条目，`settings`明确游戏补足（起始品级、殿试与世族选择）。未指定holder的职位自动生成虚构人物。明确空缺用 `empty`与`reason`，不得同时指定holder。

源代码从原版历史推导宋朝实际辖属，结合经过审阅的两个开局军路设置；主头衔有歧义的多县主管直接报错。代码不模拟引擎任命与继承。引擎用正式trigger反向扫描实际适用辖区，对照配置索引，检查人员完整性。

原版开局回调与学者模板另有人工审阅摘要；发生变化先审阅，不自动改摘要。人工人物不剥夺原版实职，已知冲突保持虚构补齐：程濬在原版任棣州，晁宗恪在原版任河北等职；岭西为1066军路，不因考证有人而强制设置独立提刑。

随机按开局、官署和属性通道独立派生。增加职位不会重抽旧人，缺失的自产文件可重建，修改过的自产文件则拒绝写入。人物替换时，移除的自产角色若仍被外部脚本引用，工具拒绝清理；无人引用的失效自产文件随显式更新清理。

1066与1178共用每个官署唯一历史定义，后者无职位时清空历史持有人。历史日期只参与新局构建，不在游玩推进至1178时批量换人。旧存档不导入预配置名单。

家族身份与世族头衔独立。虚构人物各有单人家族，10%概率持世族，不要求有限样本恰好十分之一。预设选择固定；运行时补位也使用10%首次选择，维护不重抽、不撤销原有世族。两个已登记的世族创建入口覆盖只阻止明确选择无世族且仍专职、当前与首次均无世族者的自动创建。已有或后来继承的世族保留，转任其它实职后不延续限制。原版逻辑保留可核对快照，不覆盖on_action文件。

## 检查边界

工具回归覆盖稳定生成、缺失重建、人工保护、非法路径、冲突、空缺和清理引用。原生行为直接维护 `events/tests/tca_startup_officials_test_events.txt`，覆盖初始快照、家族两分支与跨季度保持世族选择；两个开局分别运行，未执行或引擎错误均不算通过。真实存档重载另行验收，不用普通等待冒充重载。

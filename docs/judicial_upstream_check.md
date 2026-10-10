# 囚禁权限与原版更新检查

普通囚禁不再覆盖 `imprison_interaction`。目前只覆盖
`imprison_neutral_is_valid_showing_failures_only_triggers_trigger`：先执行保留的原版检查，再限制司法官职使用普通拘捕。菜单入口可能仍可见，但不可用。

原版摄政拘捕通过 `intermediary` 与发起人的摄政身份识别，继续使用原来的规则。新增的请求批准拘捕和辖区拘捕直接调用 `tca_judicial_arrest_native_common_valid_trigger`，不受普通入口限制。

## 更新后检查

在 mod 目录执行：

```sh
python3 tools/check_judicial_upstream.py
```

脚本比较安装游戏中的原版 trigger、`tools/baselines/imprison_neutral_trigger.txt` 中已审阅的基线，以及 mod 中保留的原版检查。忽略注释和空白，保留条件、操作符及字符串的差异。发现变化时打印逐 token 差异，不自动修改任何文件。

- 退出码 0：三者一致。
- 退出码 1：存在差异，需要检查和同步。
- 退出码 2：文件缺失、读取失败或结构异常，不能确认一致。

安装路径不同时使用 `--game-dir /path/to/Crusader\ Kings\ III/game`。

同步时先审阅变化，再修改 mod 保留的原版检查和基线；基线必须保留原版 trigger 名称。不要只更新基线来消除提醒。

此检查只监测这个 trigger 的文本逻辑，不证明游戏中的行为兼容，也不检测其他 mod 的覆盖。游戏更新改变了调用路径、摄政作用域或其他囚禁脚本时，仍需单独验证。

## 游戏内验证

1. 普通观察使和提刑：原版囚禁入口不可用，官职拘捕互动可用。
2. 请求批准拘捕：审批可正常批准或否决。
3. 提刑直接拘捕：不被普通入口限制拦截。
4. 皇帝及刑部尚书：保留原版拘捕资格。
5. 摄政拘捕：有合法摄政身份时仍按原版审批和拘捕流程处理。

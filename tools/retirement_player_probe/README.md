# 独立玩家会话引导

仅用于[闲退接口验证](../../docs/appointment/retirement_verification.md)的实际玩家控制权检查。复用主模组 `tca_retirement_session.1` 及其5条原生断言，不复制玩法规则，不修改观察者框架的统计、运行标记或验收器。

## 优先使用统一CLI

统一CLI已集成末项人类阶段：`python3 tools/run_game_tests.py --case tca_retirement_session.1 --timeout 600`；默认全量同样执行。观察者先保存本局检查点，新进程使用 `-loadsave` 与 `-play=h_china` 建立真实人类席位，原生确认后续接唯一用例，最后由GUI回观察者。证据契约见[测试运行说明](../../docs/testing/README.md#真实玩家会话末阶段)。下文保留独立适配器的人工复现方式，不与统一CLI同时加载。此入口的实现接线与静态协议测试不等于引擎已验收。

## 加载与隔离

使用全新的可丢弃用户目录，仅加载主模组和本目录对应的工具适配器。**不同时加载CLI观察者适配器**；观察者中的 `play` 可能只切换观察视角，GUI的 `GetPlayer` 匹配不能证明人物由人类控制。

可用普通CLI的 `--prepare-only --case tca_retirement_session.1` 准备独立主模组快照和偏好；实际启动前，在该独立目录的 `dlc_load.json` 中将CLI适配器替换为本目录的独立副本及描述文件，并确认 `.mod` 的 `path` 指向本次副本而不是旧目录。保留原准备记录，并另记人类会话的实际加载列表、适配器源码散列、启动参数和进程归属；不能把替换后的运行称为原CLI观察者验收。

## 无教程基础存档

本机新开1066中国局会在进入游戏后打开中国教程窗口并把游戏暂停；当前自动化没有可靠的界面权限关闭该窗口。`pause`、`OnPause` 和 `tutorial.disable` 都不能替代对教程窗口的实际操作，因此不能把新开局卡在教程的进程当作玩家交接证据。

本轮采用的可复现路径是：先用独立观察者局生成一个可丢弃的1066基础存档。该局只加载主模组和一个临时的保存引导适配器，执行 `observe`、恢复暂停、推进数日后 `save <name>`；**不加载本目录的人类适配器，也不派发主模组业务测试**。确认 `console_success: Game saved to <name>` 后退出该局。

再用同一基础存档启动人类会话：

```text
<ck3可执行文件> -debug_mode -develop -skip -loadsave=<name>.ck3 -play=h_china -userdir=<独立目录>/
```

基础存档本身来自观察者，但加载后由 `-play=h_china` 建立真实玩家槽位；人类适配器只负责解除启动暂停、处理可见事件和启动主模组原生测试，不进入观察者。该路径仍未验证新开局教程窗口下的人工入口。

## 实际入口与证据

适配器在 `on_game_start_after_lobby` 把 `tca_cli_ready` 显式归零、写入 `tca_retirement_human_run = 1`，再触发引导事件；这样主模组的CLI保存重载界面不会在人类会话误启动，也满足变量必须由可执行脚本设置的契约。引导事件先由原生 `is_ai = no` 确认皇帝处于真实玩家槽位，才调用主模组原生测试；该前置失败必须记为未执行。

暂停由原生 `OnPause` 恢复；开局可见事件只选择实际存在且有效的首个选项，不改写事件暂停标记或日期。退休接口探针为hidden事件，这不替代正式退休选项的人工显示验收。

核对同次 `debug.log` 中唯一的 `INITIAL_PLAYER_CONFIRMED`、测试BEGIN、连续CHECK 1至5及最终PASS；任一CHECK_FAIL、缺结果、超时或未建立真实人类槽位都不能算通过。另审阅同次 `error.log`，至少不得出现 `tca_` 相关变量、GUI、`set_player_character`、`change_title_holder` 或 `change_liege` 错误。

5项断言的证据范围：

1. 接管前新人物为AI、失能且能执行正式候选决议。
2. `play`后同一人物 `is_ai = no`，且仍满足正式决议资格。
3. 执行正式候选决议后取得奉祠特质、退出候选、未获 `devoted`。
4. `set_player_character`后继承人为 `is_ai = no`、取得真实家门与庄园、不带退休特质；原人物为 `is_ai = yes`、不再持有非家门头衔、保留奉祠身份与官品。
5. GUI回观察者后原人物与继承人均为AI，排队的最终事件在5日后继续执行。

该结果证明玩家槽位、原人物状态和原生家门／庄园转交接口，不证明正式退休事件显示、完整玩家选择流程或旅行赶考入口。不得以观察者结果、GUI视角匹配或控制台 `play` 返回成功替代。

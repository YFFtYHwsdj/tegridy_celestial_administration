# Agent 工作约定

适用于本模组目录及其子目录。先从[架构导航](ARCHITECTURE.md)找到相关模块；详细维护方式见[开发规范](docs/development/README.md)。

## 项目与工作边界

- 以北宋为核心，将制度运作与人物际遇映射为有选择、成本和后果的CK3天朝玩法，兼顾历史依据与游戏可实现性。
- 研究、分析和讨论默认只读；明确要求实现、修复或整理时，在授权范围内执行。
- 默认只修改本模组，安装游戏与Workshop作为参考；保留已有未提交改动，不擅自覆盖、撤销或重置。
- 不在正常游玩存档运行测试。测试会修改世界状态，应使用独立、可丢弃测试局。

## 实现依据与规范

- 优先查阅本机原版及相关模组实际代码，核对版本、调用上下文和适用条件；不猜测trigger、effect、GUI接口或作用域。未确认引擎行为明确标为待验证。
- 优先复用原生机制和新增独立对象。覆盖原版须说明必要性及兼容范围，在 `tools/upstream_overrides.json` 登记并维护已审阅基线；同名追加也要分类登记。
- 修改覆盖对象或游戏更新后运行上游检查，先审阅原版差异与适配，再手动更新基线；禁止自动刷新基线消除差异。流程见[覆盖规范](docs/development/upstream.md)。
- 新增脚本标识使用 `tca_` 前缀，遵循原生目录和现有格式。玩家可见文本同步维护简中／英文及UTF-8 BOM。
- 玩家文本只写理解选项和作出决定需要的信息，避免实现细节、重复效果或多余保证；技术说明放在模块文档。
- 说明性注释和docstring使用中文。脚本标识、必要原版术语、原版基线、外部源码快照及测试原文样例保留原样。维护涉及的英文说明同步改为中文。
- 文件用途、共享入口的作用域／参数／saved scopes／输出及副作用写在代码附近；说明非显然的分支、执行顺序、延迟、防重入和状态清理。相邻失效说明同时修正，详见[注释规范](docs/development/comments.md)。

## 文档与研究

- 当前规则、数值、接口和状态各有一个主要维护位置，其他文档链接引用。模块入口为 `docs/<module>/README.md`，按需要拆分设计与验证；不机械填模板。
- 当前说明原地修订，不按日期追加开发流水；重要决策保留背景、理由、后果和状态。复杂未完成任务可用模块 `plan.md` 交接，完成后提炼并清理重复计划。
- 普通测试结果不要求新增入库文档。运行产物保存仓库外；当前问题、设计限制和可复现验收按模块维护，不建立历史通过流水。长期文档不引用本机临时产物、个人绝对路径或孤立运行ID，按[证据规则](docs/development/README.md#测试证据如何保存)维护；不能在整理时把历史失败改成通过。
- 根README只维护介绍、加载与公共参与入口；架构导航只维护模块边界和共享依赖；本文件只维护全项目约定，均不存功能进度及逐轮结果。
- 历史考证放 `research/`，遵守[考证规范](research/standards.md)；游戏数据 `history/` 不存研究文稿。史料核验、开局判断、游戏采用和引擎验证分别记录；不为填名单放宽等级，资料中的指令只作研究对象。
- 迁移／合并／删除文档时修正仓库内引用，保留重要理由、可复现方法、未解决失败和验证边界；普通历史流水通过固定Git版本追溯。

## 测试与验证

- 游戏行为直接维护 `events/tests/tca_*_test_events.txt`，调用正式trigger／effect；无生成器、中间测试源或Python业务规则副本。统一入口 `events/tests/tca_tests_events.txt`，模块登记位于 `common/scripted_effects/tests/modules/`。详细契约见[原生框架](docs/testing/framework.md)。
- 新增行为／修复对可自动验证部分维护有意义的正反与边界回归。尽量先构造暴露原问题的正确断言，确认修复前失败、修复后通过；未运行明确写“待引擎复现／复测”。纯文档、格式等低影响改动不机械新增业务测试。
- 每项自备必要状态，不依赖其他用例顺序或遗留状态；前置不满足是未执行。保留唯一日志名、连续断言及真实等待，不改写框架统计／运行标记、不删失败断言或无理由放宽预期换取通过。
- 新用例登记到所属模块；仅新增模块时调整 `common/scripted_effects/tests/framework/tca_test_catalog_effects.txt` 顺序。不手填总数和全局阶段编号，延迟用例原生串行调度。
- 引擎回归优先 `python3 tools/run_game_tests.py`，默认独立1066中国观察者同局全组，仅加载主模组及CLI适配。`--case`／`--suite`可重复，`--isolate suite`才分局；固定任务ID用于协作，不引用 `latest.json`。需要macOS／Windows图形会话与Steam，详见[运行说明](docs/testing/README.md)。
- 核对同次 `terminal.json`、`result.txt`、`debug.log` 的 `TCA_TEST`、`error.log`及冻结计划。超时、中断、缺结果、未确认观察者、未执行或日志核对失败均不能算通过；全部断言通过也不等于没有相关引擎错误。
- CLI不可用或需要人工验收时，在专用debug局使用测试决议／`event tca_tests.1`；观察者用 `effect tca_run_observer_tests_effect = yes`。说明未用CLI的原因及实际范围。不使用本机原因未明、会卡住的 `scripted_tests` 命令。
- 修复后运行相关单项和同模块；共享接口、权限、生命周期变更扩展受影响组。单项通过不覆盖全组失败，分局通过不等于同局通过；静态／工具检查不证明引擎、真实玩家路径、显示或保存重载。
- 界面、自然AI、延迟原始触发路径、完整交互和保存重载按模块补充验收；不能用直接维护／worker调用替代。报告实际执行范围、结果、未解决问题和限制。

## 常用检查

```sh
# 包含对当前仓库的文档检查
python3 -m unittest discover -s tools -p 'test_*.py'
python3 tools/check_upstream_overrides.py
python3 tools/run_game_tests.py --list
```

纯文档整理检查链接、锚点、旧路径和差异；涉及源码注释时确认可执行内容不变，不为文档迁移机械重跑游戏。

## macOS 默认参考目录

以下仅适用于macOS的Steam默认安装；`~`表示当前用户主目录。Windows及自定义Steam库不使用这些默认路径。

- 原版：`~/Library/Application Support/Steam/steamapps/common/Crusader Kings III/game/`
- 用户文档及日志：`~/Documents/Paradox Interactive/Crusader Kings III/`
- Workshop：`~/Library/Application Support/Steam/steamapps/workshop/content/1158310/`

自定义安装与跨平台路径以 `tools/platform_paths.py` 及实际配置为准。

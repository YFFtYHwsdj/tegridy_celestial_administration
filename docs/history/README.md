# 历史资料与旧文档溯源

当前规则从[架构导航](../../ARCHITECTURE.md)进入。此目录仅保留对后续维护仍有价值的已终止实验，不维护已完成任务清单或全部逐轮报告。

## 整理前固定版本

2026-10-21整理前全部受Git跟踪的文档位于提交 `c5070992c8f21be5c85cc5520d77f736a397feae`。整理开始时工作区干净，旧文档没有额外未提交内容。可在仓库中读取原文，例如：

```sh
git show c5070992c8f21be5c85cc5520d77f736a397feae:docs/test_runs/2026-10-21-exam-family-notification.md
git show c5070992c8f21be5c85cc5520d77f736a397feae:docs/test_framework_windows_integration.md
```

该版本包含原来的 `docs/test_runs/`、`docs/history/*_history.md`、平铺模块说明以及已完成的 `docs/superpowers/plans/`。原日期、运行ID、失败及历史源码保留在Git历史，不通过复制另一套完整历史手册延续维护。历史文档中的命令、旧生成步骤和“当前／待复测”仅指当时版本，不作为现行指令。

仍需处理的问题、复现入口与判断边界分别由对应模块维护；[实验结论](experiments.md)保留采用／放弃方案的理由。Git中的旧文字只证明当时记录了什么，不能替代未保存的日志、冻结源码或可复现测试。

## 保留的实验源码

[动态伯爵创建原始失败源码](tongpan_dynamic_county_probe_events.txt)包含会在加载期报错的effect，故保存在游戏不加载的目录，仅用于独立副本复现。不能将其复制回正常玩法加载目录，或用后来的静态头衔通过结果称动态接口已经修复。

未来只在重要旧方案仍影响维护决定时新增历史材料；当前行为原地维护，普通运行产物按[开发规范](../development/README.md)保存。

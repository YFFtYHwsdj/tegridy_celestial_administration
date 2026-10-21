# 架构与阅读入口

本模组通过原生法律、无地头衔、任命、契约、宫廷职位和互动扩展天朝制度。游戏实现位于 `common/`、`events/`、`gui/`、`localization/` 等原生目录；本页只维护模块边界和依赖，不登记功能进度或测试数量。

## 模块关系

- [官制与名称](docs/court/README.md)：官名选择、默认法律及旧法兼容；司法和通判制度使用独立法律，不由名称选择决定。
- [地方司法](docs/judicial/README.md)：提刑机构、路法理辖区、位望、分层拘捕、公职囚犯与详覆。拥有统一司法辖区和身份分档接口。
- [通判](docs/tongpan/README.md)：州级独立无地官职、绑定与原生任命、常设分权、治理加成和行动附费。复用官署生命周期思路，保持自己的资格、绑定与法律。
- [官署经费](docs/office_funding/README.md)：复用司法路和通判州的登记表，按辖区绑定付款、按官署保存待遇；[契约](docs/office_funding/contracts.md)拥有身份／功绩／俸禄边界，[调整互动](docs/office_funding/interactions.md)拥有授权与冷却。
- [科举](docs/examination/README.md)：知贡举宫廷职位与玩家皇帝代办事件链，复用原版考生来源、评分和及第状态；AI保留原版活动。
- [宗教与儒家统计](docs/religion/README.md)：区分宗教设计与已实现的Rite分布缓存；统计当前提供读取接口，尚未接入人物生成概率。

司法、通判的官职身份和待遇由经费／契约模块维护，不能在各模块复制另一套档位或付款关系。科举按正式官员身份排除在任行政官员；职位任用与行政头衔继任是不同入口。儒家统计按实际领主链聚合，不使用司法法理归属代替人口归属。

## 开发与验证

- [工作约定](AGENTS.md)：修改权限、原版依据及必须遵守的核心规范。
- [开发与文档维护](docs/development/README.md)：任务阅读顺序、文档分工、计划生命周期、证据保存和清理。
- [代码注释](docs/development/comments.md)：安全调用信息留在代码附近，跨文件流程由模块文档维护。
- [原版覆盖检查](docs/development/upstream.md)：`tools/upstream_overrides.json`及已审阅基线是覆盖清单的主要维护位置。
- [测试运行](docs/testing/README.md)与[原生框架](docs/testing/framework.md)：Python只编排启动、登记读取和日志检查，游戏行为直接由原生隐藏事件验证。
- [历史研究](research/README.md)：历史采用判断与游戏实现／引擎验证分别记录。

当前规则从模块入口读取；只有追溯设计或证据时再读[历史索引](docs/history/README.md)。新增普通功能不更新本页；模块边界、共享依赖或入口发生变化时才更新。

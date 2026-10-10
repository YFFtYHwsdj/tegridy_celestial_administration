# Tegridy的天朝行政重做

CK3 天朝行政体系重做 mod。已加入普通文官路的动态无地提刑官职创建、绑定、清理及恢复脚本；采用原版天朝文官领地继承法，另有仅 debug 可见的首任补位入口；首任按无地、功绩门槛与学识权重选任；无人合格时生成文官兜底，授予后沿用原版领地继承，不添加官职专属继承法。新流程仍待游戏验证。尚未接入刑事交互。

首个设计模块：路级提点刑狱公事，包含刑事权限、举刺官吏、领主交互和功绩任命。

设计规格：[提点刑狱公事 Spec v0.1](docs/song_judicial_title_spec.md)。

实现说明与原版/mod 写法分析：[提刑官职头衔生命周期](docs/judicial_title_lifecycle.md)。

## 本地加载

在 CK3 启动器中将“Tegridy的天朝行政重做”加入播放集并启用。当前声明的游戏版本为本机 1.20.0.4，不表示已完成兼容性或游戏内验证。

## 文件

- `descriptor.mod`：mod 包描述。
- `docs/song_judicial_title_spec.md`：设计与实现规格。
- 相邻的 `tegridy_celestial_administration.mod`：本地启动器描述，引用本目录。

首次任命实验与操作步骤：[提刑任命验证](docs/judicial_appointment_test.md)。

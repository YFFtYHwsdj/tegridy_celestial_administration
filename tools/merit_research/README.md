# 功绩升品数学研究

研究源码统一在此维护；之后的功绩机制、参数、生命周期与占职研究也直接在本目录新增或修订。它们是离线模型，既不生成原生游戏测试，也不代替正式trigger/effect的引擎回归。当前结论和待定事项由[官职任命文档](../../docs/appointment/README.md)维护。

## 目录与用途

- [baseline](baseline)：旧候选比例/机构吞吐/缺额方案、增长与资格敏感性。38组、456次100年演算。
- [buffers](buffers)：旧p/H方案的分带缓冲、独立上层压力、整数小池及死亡等待。80组、960次100年演算，另有最高带受控对照。
- [occupancy](occupancy)：四级竞争头衔、年龄健康、任职与迁任代理。160次80年动态及72次固定人口分配。
- [controller](controller)：当前待审的累计人数反馈候选。20情景、260次400年演算。
- [joint](joint/README.md)：四六目标下的60组员额换算审计、36次80年先导及76次120年留出；平衡目标尚未通过。
- [check_calibration.py](check_calibration.py)：复核共享校准源码及5120个逐年人口、职务与目标状态。
- [calibrate_joint.py](calibrate_joint.py)：沿用合成生涯，文武严格共用参数，对四带系数作定向校准；基准统一单位头衔入仕强度，旧偏载留作压力。
- [calibrate_split_reference.py](calibrate_split_reference.py)：旧文武分参对照的复算源码，保留研究依据，不属于当前机制。
- [analyze_joint.py](analyze_joint.py)：只读核对联合结果，补充逐年恢复、零额度及竞争挤占诊断。
- [bottleneck](bottleneck/README.md)：逐人拆分资格/功绩/竞争与前后期死亡，检验共同梯队储备的效果及总量约束。
- [budget](budget/README.md)：放宽逐带K≥J假设，在低总预算下比较共同梯队分配，独立验证结构、冲击与最快合格供给包络。
- [parameters](parameters/README.md)：当前逐带员额与逐参数校准，先处理不可辨识关系，再作同人物单因素、交互和独立资格/健康/收入敏感性。
- [parameter_trial.py](parameter_trial.py)：指定一组四带系数作定向验证；基准双种子与压力情景共20局，每局完成立即保存，配置和源码一致时可续跑。
- [income](income/README.md)：当前按真实来源系数分账的收入研究；取代统一终身增长的默认解释，实际税额、兵池价值和事件频率仍为显式外部输入。
- [coefficient_grid.py](coefficient_grid.py)：四带系数1.5至4、步长0.5的1296组合小规模筛选，保留最高带各层代表后用新种子作完整规模复核。
- [parameter_check.py](parameter_check.py)：共同k与四六比例选定后的固定配置小量核查，不搜索其余参数；12局及单一温度/反馈检查同时保留供给失败。
- [run.py](run.py)：冻结版本、隔离进程、按依赖执行及结果检查入口。

保留四组既有研究源码的计算内容和局部导入，不为迁移改写公式或刷新结果摘要。入口会将源码冻结到仓库外，使用既有相邻目录名；占职研究依赖缓冲模型及其封存结果，所以选择occupancy会先复算buffers。不同组隔离进程，避免study/model等局部模块同名串用。

## 复算

从仓库根目录执行；结果、源码冻结副本和每步日志写入新建的系统临时目录，终端会显示实际位置：

```sh
# 最新反馈方案，含研究检查
python3 tools/merit_research/run.py controller
# 员额审计、四六目标联合先导和独立种子验证（不重跑旧实验）
python3 tools/merit_research/run.py joint
# 年龄与占职研究，包含缓冲依赖的复算
python3 tools/merit_research/run.py occupancy
# 使用合成数据共享参数校准（16次先导、32次留出）
python3 tools/merit_research/calibrate_joint.py --output-dir <仓库外的新目录>
python3 tools/merit_research/check_calibration.py <该目录>
# 含新联合研究的完整复算
python3 tools/merit_research/run.py all
```

要持久保存，用`--output-dir <仓库外的新目录>`；目录必须为空。脚本不会覆盖旧结果。已有产物用以下方式核对当前库内源码及结果摘要，再运行对应研究检查：

```sh
python3 tools/merit_research/run.py controller \
  --check-only --output-dir <已有的仓库外产物根目录>
# 指定系数；研究使用持久目录，避免临时目录清理造成证据丢失
python3 tools/merit_research/parameter_trial.py --coefficients 1.5 2 3 1.5 \
  --output-dir <仓库外的持久新目录>
# 同一命令再次执行只补齐未完成局；全部完成后可只核对
python3 tools/merit_research/parameter_trial.py --coefficients 1.5 2 3 1.5 \
  --output-dir <该持久目录> --check-only
```

只冻结、不启动长演算可用`--prepare-only`。复核遇到源码变化会明确失败，不自动覆盖旧副本或把旧结果重新签成新版本；应保留旧产物并另起完整复算。仅复制了源码、缺结果、任一步非零退出都不算研究通过。

运行入口仅依赖Python标准库；controller另需[requirements.txt](requirements.txt)中的NumPy版本。当前研究使用Python 3.9及以上语法，随机结果还应结合Python/NumPy环境复核；相同种子不等于跨所有运行时严格逐字节相同。

## 后续维护

- 参数假设、来源和可复算方法写在所属研究说明及代码附近，解释性注释/docstring使用中文。
- 新模型在本目录建立独立子目录，并在run.py登记执行/检查顺序；复用已有模型的专用参数编排器可以提供独立CLI，但须冻结依赖、核对结果并在本页登记。有依赖时明确，不从个人临时路径导入源码。
- 模型检查位于各组checks.py等文件，随研究入口执行；正常工具测试只验证运行器的文件边界和失败处理，不自动跑长时参数研究。
- JSON结果、随机轨迹、日志、缓存和冻结副本不入库。长期文档引用库内方法与源码，不能把个人产物目录当公共证据。
- 正式业务必须仍由原生游戏脚本维护和验证。人工死亡率、资格比例、收入、槽位与评分不得自动转成游戏默认值。

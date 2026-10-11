# Tegridy的天朝行政重做

CK3 天朝行政体系重做 mod。中央、地方官制分别提供因便／宋制，仅改变官名，名称切换各收200威望。提刑及地方、中央司法审批由独立的地方司法制度法律控制，改革收2000威望和1000影响力、冷却十年。检测到东方王朝或礼法与治道时退出普通官名管理。1066、1178中国政权默认宋式名称并设提刑，其他天朝政权默认因便且不设提刑。1066 开局的 15 个文官路由头衔历史声明固定提刑机构与路的对应关系，维护优先使用这些预定义无地官职，其他启用司法制度的开局与新设辖区动态创建；已有有效绑定保留。固定与动态官职废置时只撤销任职，保留对象和所属路绑定，恢复复用原 ID。机构历史暂未填入考证人物，开局空缺仍走既有补位流程。官职直接沿用持有者的原版天朝文官继承法及任命类型（允许同级升迁、启用原版任命冷却）；维护自动移除旧版提刑专属法。交接后校验专职无地资格，空缺或不合格持有者由补位流程另选或生成文官，随后恢复所属路关系、名称、纹章和销毁标记。提供只读诊断与维护测试决议，另有季度/年度维护。2026-10-10 已通过本次测试存档的死亡交接、异常补位及现任稳定性核对；同级调任、保存后重载等场景仍待验证。已接入分层身份评分、州／路辖区拘捕、刑部→御史→宰相→皇帝审批与公职囚犯交接脚本；刑事模块尚待游戏内完整验收。

名称选择、独立司法制度及验收：[朝廷官制](docs/court_system.md)。当前已接入脚本，法律界面及改制行为尚待游戏内验证。

首个设计模块：路级提点刑狱公事，包含刑事权限、举刺官吏、领主交互和功绩任命。

设计规格：[提点刑狱公事 Spec v0.1](docs/song_judicial_title_spec.md)。

实现说明与原版/mod 写法分析：[提刑官职头衔生命周期](docs/judicial_title_lifecycle.md)。

1066 固定机构名单、历史人物补录与验收：[1066 固定提刑机构](docs/judicial_static_titles.md)。

## 本地加载

在 CK3 启动器中将“Tegridy的天朝行政重做”加入播放集并启用。当前声明的游戏版本为本机 1.20.0.4，不表示已完成兼容性或游戏内验证。

## 文件

- `descriptor.mod`：mod 包描述。
- `docs/song_judicial_title_spec.md`：设计与实现规格。
- 相邻的 `tegridy_celestial_administration.mod`：本地启动器描述，引用本目录。

首次任命实验与操作步骤：[提刑任命验证](docs/judicial_appointment_test.md)。

无地官员契约及验证说明：[官员义务、俸禄与预算](docs/official_contracts.md)。

分层权限与权重：[拘捕权限评分](docs/judicial_authority.md)。管辖包括本人及实际下属宫廷的成员与待招募宾客，提刑覆盖本路主官宫廷。伯爵级行政官职至少需要提刑许可，路主官本人须中央批准；成功后由发起者关押。

中央宋式称号按实际丞相、御史大夫官职头衔显示，不按地方官兼任的内阁席位改名。为避免额外兼容补丁，不覆盖内阁职位及首辅法律文本，接受卡片／法律名称与角色称号不一致。2026-10-11 已撤销此前为统一名称新增的覆盖并通过静态回归；界面待重启复测，总入口现有1组13项，详见[官制说明](docs/court_system.md)。

司法拘捕当前实现与验收：[司法拘捕及囚犯交接](docs/judicial_arrest.md)。AI 审批与后续拘捕均采用原生概率判定；合法理由+80。有效审批否决由请求者损失100威望、50影响力并产生关系后果；请求采用3个月全局、同目标1年冷却，明细沿用原生界面。

权限覆盖与原版漂移检查：[原版覆盖更新检查](docs/judicial_upstream_check.md)。运行 `python3 tools/scan_upstream_overrides.py` 可独立扫描原版与模组，检查覆盖登记是否遗漏；运行 `python3 tools/check_upstream_overrides.py` 可检查已审阅基线是否随原版更新发生变化。

开发工具包含原版覆盖检查、查漏扫描及其测试，另含本地化 BOM 检查。游戏行为的测试框架及使用方式见下方说明。

互动文本与作用域：[动态本地化](docs/judicial_localization.md)。

提刑同级调任的职位价值：[提刑重要性算法与验证](docs/judicial_prominence.md)。已实现独立公式，静态检查通过与游戏内验证分别记录在该文档中。

王国级圣职区验证已终止：宗教层级、共同显示与宗教竞争不适合用作天朝官职，测试文件及原版事件覆盖已移除。完整结果与原型源码见[验证记录及归档附录](docs/clerical_region_probe.md)。正式提刑仍使用原有公国方案。

## 测试框架

游戏内测试用 CK3 的 P 脚本表达前置条件、操作及预期结果，直接调用模组正式 trigger/effect。测试源位于 `tests/tca_*_tests.txt`，生成器将它们编译为隐藏事件并自动汇总到一个总入口，未来新增测试组沿用同一入口。Python 只负责生成及检查脚本，不重复模拟拘捕、评分或辖区等业务规则。

框架有两类检查：游戏内 P 脚本检查法律、权限、标记、迁移等实际引擎状态；`tools/test_*.py` 检查生成器及原版覆盖检查等开发工具。Python 工具测试不会计入游戏内通知。

目前登记3组59项、235个断言：13项官制、42项即时[司法法律回归](docs/judicial_law_tests.md)及4项延迟司法回归。新增法律限制、审批人入狱／换任、目标迁庭，以及自然次日维护、启闭和提刑死亡交接；20:04修正后59项及235断言全部通过，包含四项自然延迟回归；启动仍有已记录的命名作用域及机构名本地化错误。即时项后会显示等待通知，请取消暂停并推进至少八日，直到最终结果。运行后用 `python3 tools/check_test_run.py` 核对全部结果及相关引擎错误。框架说明见[统一测试文档](docs/mod_tests.md)，实际UI扣款及保存重载仍需另外验收。

### 游戏内运行

1. 在 CK3 启动选项加入 `-debug_mode`，启用本模组。使用专用测试新局或测试前存档，初始化完成后暂停；测试会修改世界状态，结束后不要保存为正常游玩进度。
2. 当前官制组使用 1066 中国场景，不加载东方王朝、礼法与治道等外部官名管理模组。其他测试组可以定义自己的场景要求。
3. 点击调试决议分类中的“调试：模组一键测试”，或在控制台输入一整行：

   ```text
   event tca_tests.1
   ```

4. 上方通知显示是否全部通过、通过及未通过数量。未通过包括断言失败、前置条件不满足的未执行，以及缺少完成结果的用例；不把未执行当作通过。
5. 在用户目录 `Crusader Kings III/logs/debug.log` 搜索本次运行的 `TCA_TEST`，核对每项 BEGIN、CHECK_PASS/CHECK_FAIL、PASS/FAIL/PRECONDITION_FAIL，并检查同次调用的 `error.log`。通知显示全部通过仍不能证明没有引擎脚本错误。

需要单项复测时，用生成文件中的事件编号，例如 `event tca_court_test.10`。单项只写日志；总入口才汇总并发通知。旧 `event tca_court_test.100` 保留为总入口别名。本机 `scripted_tests` 命令曾发生执行器锁等待，不用它运行这套测试。

### 编写或添加测试

在 `tests/` 新建 `tca_<模块>_tests.txt`，或向对应文件追加用例。各名称必须使用全项目唯一的 `tca_test_` 前缀，每个文件最多 99 项。结构是先 `name`，再一个前置 `assert`，随后一组或多组 `effect` 与 `expect`，至少包含一个 `expect`。

下面的示例检查实际行为：独立最高领主不应保留普通地方官名标记。它先注入残留标记，再调用正式维护效果检查清除结果；示例用于说明写法，不会因出现在本文中自动加入测试：

```pdx
tca_test_example_sovereign_name_cleanup = {
    name = "tca_test_example_sovereign_name_cleanup"
    assert = {
        title:h_china = {
            exists = holder
            holder = {
                is_alive = yes
                is_independent_ruler = yes
                government_has_flag = government_is_celestial
            }
        }
    }
    effect = {
        title:h_china.holder = {
            save_scope_as = tca_example_subject
            add_character_flag = tca_song_local_names
            tca_refresh_official_name_flags_effect = yes
        }
    }
    expect = {
        scope:tca_example_subject = {
            NOT = { has_character_flag = tca_song_local_names }
        }
    }
}
```

每项自行准备独立状态，直接调用正式实现，断言玩家需求或业务结果，不能依赖其他用例先执行。通过显式 title 等作用域定位对象；当前编译器不支持 `character_target`、`target` 等附加字段。不要改写 `tca_test_suite_*` 统计变量及 `tca_test_suite_running`、`tca_test_case_failed` 标记。新增用例尽量追加到文件末尾，保留已有单项编号。

修改测试源后，在模组目录运行：

```text
python3 tools/build_test_events.py
python3 tools/build_test_events.py --check
```

生成器自动发现所有 `tests/tca_*_tests.txt`，生成各组事件及总调度列表，数量由用例计算。保存生成文件，勿直接修改带生成标记的事件；重启游戏加载修改后再运行。各组命名规则及限制见[统一测试文档](docs/mod_tests.md)，已有用例见[官制测试](docs/court_system_engine_tests.md)及[司法法律测试](docs/judicial_law_tests.md)。

开发工具的 Python 测试在模组目录运行：

```text
python3 -m unittest discover -s tools -p 'test_*.py'
```

### 发现问题与修复验证

新增机制或改变可自动验证的行为时，补相应回归用例，优先覆盖有意义的正反条件和边界。发现缺陷后记录场景、触发步骤、实际与预期结果以及日志，先构造最小复现，尽量写出修复前能失败的正确预期，再修改实现。修复后确认该项通过，并运行相关模块及受影响的共享流程测试，保留用例防止回归。

不要通过删掉断言、放宽预期或把真实缺陷变成跳过来获得通过结果。如果问题表现为引擎错误，但现有状态断言已经通过，仍要检查错误日志并补相应复现步骤或检查；不能仅凭通知宣布修复完成。

无法由当前即时框架验证的界面、异步事件、概率行为和存档问题，在模块文档记录可复现的游戏内验收步骤及结果。不能运行时明确标为待复现/待复测；能运行时记录修复前后实际结果。汇报区分静态检查、工具测试、游戏内断言及完整行为验收，具体开发约定见 [AGENTS.md](AGENTS.md#测试开发约定)。

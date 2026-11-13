# 北疆原型验证与当前边界

本页维护[北方边疆局势](README.md)的可复现入口和未解决验证边界；玩法规则见[设计](design.md)，完整阶段门槛见[计划](plan.md)。阶段原型成功不等于正式局势或P0全部验收。

## 当前最小原型

当前定向引擎验收已确认：在不修改“无条件保护”政策或封臣可攻击状态的情况下，debug人物互动可以创建以地方领主为主防守者的单县战争；一位真实上级能延迟加入。原生保存重载后战争与原待支援事件自然续接，提前白和平后的待支援事件正常取消。保存前后均有观察者确认，所选范围断言和同次日志核对通过。此结论仅限以下原型路径。

debug下显式准备一名宋方县级军制地方官、一名西夏县级地方主官及其真实直属上级。西夏原本须采用“无条件保护”、不允许封臣被直接攻击；不满足则记前置未执行，不通过改法满足夹具。

原型互动`tca_frontier_probe_war_interaction`调用共用`tca_frontier_probe_start_effect`，以防守者首府县为唯一目标，使用脚本专用`tca_frontier_probe_county_cb`发起战争。开战后原生战争名单、目标和白和平结算继续由引擎处理。

支援固定等待30日，仅供保存落盘和技术验证，不是正式响应参数。原型零宣战费用、零停战期，不代表正式玩法成本。普通游戏隐藏；显式准备变量`tca_frontier_probe_target`限制互动对象，原型互动自动AI频率为0，本轮没有开放自然寻敌。

## 正式入口与副作用

- [原型资格](../../common/scripted_triggers/tca_frontier_probe_triggers.txt)：使用`scope:actor`与`scope:recipient`，确认显式准备、人物与土地状态，以及无其他在途原型请求。
- [开战与支援效果](../../common/scripted_effects/tca_frontier_probe_effects.txt)：保存实际战争引用，等待结束时从进攻者现有战争集合核验有效性；结束的战争不再读取其内部状态。
- [延迟事件](../../events/tca_frontier_probe_events.txt)：接收者为进攻者，携带原战争、地方防守者与支援上级上下文；上级死亡、改隶、已参战或战争结束时不追加援军。
- [人物互动](../../common/character_interactions/tca_frontier_probe_interactions.txt)、[CB](../../common/casus_belli_types/tca_frontier_probe_cb.txt)与[脚本专用组](../../common/casus_belli_groups/tca_frontier_probe_groups.txt)：不进入普通宣战AI搜索，不改全国保护政策。

原型不生成军队、不改国库、不借转实土来绕过保护。实际战争仍可能使AI动员、消耗军费或改变军事行为，测试世界不能转为正常游玩存档。

## 可复现的原生验收

用例：[tca_frontier_probe_test.1](../../events/tests/tca_frontier_probe_test_events.txt)，登记于[frontier_probe模块](../../common/scripted_effects/tests/modules/tca_test_modules_frontier_probe_effects.txt)。借用真实人物、发动战争并保存重载，故保持独占；K=4是框架配置，不表示本例与其他用例实际并发。

```sh
python3 tools/check_test_parallel.py
python3 tools/run_game_tests.py --suite frontier_probe --list
python3 tools/run_game_tests.py --suite frontier_probe --parallel 4 --timeout 420
```

同一用例核对：原保护状态、互动实际产生的主战双方及单县目标、上级没有立即参战、延迟后加入、原保护状态不变、实际保存重载后继续原战争、白和平结束，以及第二场提前结束后无迟到战争和待处理状态。断言和唯一日志名以源文件及冻结计划为准，不手填全局数量。

[专用检查点GUI](../../gui/tca_frontier_probe_checkpoint.gui)只在CLI就绪且用例明确设置阶段时执行：先在原生状态中转为保存阶段，再调用原生保存；运行器检查存档后以`-loadsave`启动续局。恢复阶段不重复保存或请求载入，独立恢复控件显式执行原生`observe`并恢复速度，不能沿用首进程的观察者确认；测试不重新开战、不重新安排支援。该GUI不是面向玩家的寇边窗口，不改框架统计和运行标记。

核对同次冻结计划、`terminal.json`、`result.txt`、`debug.log`、`error.log`和`reload_evidence.json`；保存重载必须有两次原生进程的观察者确认及检查点载入证据，只有恢复阶段变量或全部断言通过都不充分。

## 头衔兵士的实际集结

[tca_frontier_troops_test.1](../../events/tests/tca_frontier_troops_test_events.txt)单独选择已有头衔兵士的宋方县级地方官与其真实上级，由西夏地方领主通过同一原型互动进攻。与无条件保护探针分工：本例核对原生军队编成，不要求把宋朝保护政策改成另一档，也不以原先西夏部落县主官的私人兵士代替官署兵士。

```sh
python3 tools/run_game_tests.py --case tca_frontier_troops_test.1 --parallel 4 --timeout 240
```

等待地方防守和上级介入后，[现场保存控件](../../gui/tca_frontier_troops_capture.gui)保存仍在进行的战争。原型不创建、转移、补员或强制集结军团，由原生AI正常动员。脚本断言核对战争、上级加入和双方已集结；这些断言本身不证明军队包含哪支兵士，须另读同次原生现场存档。

存档核对方法：

1. 从用例保存的`tca_frontier_troops_defender`、`tca_frontier_troops_upper`人物作用域取得当次角色，并对应其官署头衔。
2. 在`armies.regiments`中定位`owning_title`属于这些官署的军团，记录其原生ID、兵种和`controlling_title`。
3. 经`armies.army_regiments`的来源`regiment`引用，核对军团确实进入兵力大于零的军队分队，而非只存在于可用列表。
4. 再核对`armies.armies`的分队清单，以及`units`的军队实际拥有人；不能只看到一个来源引用就算完成部署。
5. 对同次现场的全部相关军团交叉核对归属和编成。拆分军团可能合法共享来源，不能仅凭重复来源ID就判重复兵力。

当前现场核验已经确认：同州县级官署的既有头衔兵士进入地方主官的实际军队，关内上级官署的既有头衔兵士在上级加入后进入其实际军队；该样本的所属头衔、控制头衔与实际带兵人物一致，未发现相关军团重复编入。所选范围的原生断言、观察者确认和日志检查通过。

这修正了此前只凭“持有军团”和“已集结军队”两项独立记录不能判断编成的证据缺口；目前没有证据表明该原型需要另写官军调动机制。实际交战全过程、复杂征调和多级借兵仍不由本次单上级样本概括。

## 已知限制与未完成项

- 互动投递通过原生`run_interaction`核对，不等于真实玩家点击、自有GUI或自然AI已验收。
- 原型只针对显式准备的县级目标，未实现真实边境、阶段限制、费用、权限矩阵、和约、功绩或战后行政分配。
- 本轮采用白和平清理，不把它当作征服胜利转地通过；CB中的胜利事务须在P3—P4安全夹具中补验。
- 实际头衔兵士集结已由上述同次存档引用链补验；完整多级征调和实际战斗尚未覆盖，不再把正常官军集结列为已发现的技术问题。
- 死亡、改隶与重复加入已有执行前防护，但本轮未穷举这些生命周期场景。
- Situation双区域、完整自有GUI、互动AI选敌与战略评分仍是P0后续探针，不因本轮战争通路成功而视为完成。
- CLI需要能连接Steam的本机图形会话；启动失败或未确认观察者的运行没有业务验收意义。所有测试使用独立可丢弃局。

原始产物保存于仓库外，不在长期文档引用本机临时路径或孤立运行ID。后续修改需按影响重测，不能将当前最小通路的通过推广为完整P0、完整战斗全过程或寇边自然AI选敌验收。

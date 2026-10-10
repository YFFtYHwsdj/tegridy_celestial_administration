# 司法拘捕与公职囚犯交接

2026-10-10。本文说明当前脚本行为；完整制度目标见 `song_judicial_title_spec.md`。

## 当前实现

- 观察使使用 `tca_request_imprison_interaction` 请求提刑批准。否决终止请求，不当作目标拒捕；批准后继续原版式拘捕判定。成功后观察使关押，不登记为提刑公职囚犯。
- 提刑使用 `tca_judicial_imprison_interaction` 拘捕本路目标。成功后提刑关押，并在官职头衔的 `tca_judicial_prisoners` 列表登记；目标同时记录 `tca_judicial_prison_title`。
- 两种互动均以实际发起人的合法拘捕理由、牵制和相关原版后果为依据。批准不自动提供合法理由，也不豁免暴政。AI 发起人必须拥有拘捕理由。
- 辖区按实际头衔隶属与宫廷所属判断，排除观察使本人、中央大臣、其他提刑及外来宾客。多路兼任者的本宫廷按主要辖区归属。
- 有地可玩目标拒捕时，由观察使承担原版 `refused_liege_demand_war`。提刑发起的拒捕战争在实际俘获目标后延迟处理引渡；观察使发起的拘捕不登记引渡。男爵和普通无地目标沿用逃脱分支。
- 释放与囚犯死亡清理登记。维护流程将公职囚犯交给当前合格持有者，空缺时交观察使；撤销官职前转交并注销。死亡处理只转交登记属于该官职的囚犯，不转交私人囚犯。

## 实现入口与兼容影响

- `common/character_interactions/tca_judicial_arrest_interactions.txt`：两种互动、审批、资格、回复与 AI。
- `common/scripted_triggers/tca_judicial_arrest_triggers.txt`：官员身份、辖区与发送/回复时资格复查。
- `common/scripted_effects/tca_judicial_arrest_native_effects.txt`、`common/scripted_modifiers/tca_judicial_prison_modifiers.txt`：从本机原版拘捕流程改写的结果、拒捕与 AI 分数。
- `common/scripted_effects/tca_judicial_prison_effects.txt`、`common/on_action/tca_judicial_prison_on_actions.txt`、`events/tca_judicial_prison_events.txt`：登记、交接、延迟引渡。
- 仅覆盖原版 `imprison_neutral_is_valid_showing_failures_only_triggers_trigger`，保留原版检查并限制司法官员使用普通拘捕入口；合法摄政拘捕例外保留。其他 mod 覆盖同名 trigger 时存在加载顺序冲突。更新检查步骤见 `judicial_upstream_check.md`。

原版参考（本机 1.20.0.4）：`game/common/character_interactions/00_prison_interactions.txt` 的 `imprison_interaction`，`game/common/scripted_triggers/00_scripted_triggers.txt` 的 basic/advanced 囚禁资格，`game/common/scripted_effects/00_prison_effects.txt` 的暴政、合法收押与拒捕战争，以及 `game/common/on_action/prison_on_actions.txt` / `war_on_actions.txt` 的角色作用域。

## 本次审查与验证范围

静态检查：6 项 Python 单元测试通过；安装游戏权限 trigger、保存基线与 mod 副本一致；脚本括号、模组标识引用、中英拘捕本地化键及 BOM、Git 空白检查通过。不能据此确认引擎加载或游戏内结果。

既有日志显示无主头衔角色死亡时提刑身份检查发生 `primary_title` 切换失败，以及官职持有资格在迭代头衔时将 `prev.primary_title` 当成头衔作用域读取。此次为身份检查增加存在性守卫，资格检查与死亡交接改用明确保存的头衔作用域；死亡交接还要求囚犯确实具有公职登记。拘捕效果文件补齐 BOM。编辑后未重启或重载游戏，尚未验证新日志。

既有日志还显示原版 `tgp_chinese_naming_tier_trigger` 在 `scope:title`（头衔）下读取 `capital_county`，经官职任命调用 `on_rank_up` 时产生类型错误。这属于已有生命周期路径触发的原版脚本问题，本次未覆盖原版对象；是否影响官职称号需重载核对。

## 可复现游戏验收

1. 重启并加载启用本 mod 的天朝存档；检查新生成的 `error.log`，验证互动身份检查和无主头衔角色死亡不再产生上述作用域错误。
2. 观察使分别针对有合法理由与无合法理由的本路目标请求拘捕，测试人工/AI 提刑批准与否决：批准不保证成功；无理由批准仍有暴政；否决无拘捕、无拒捕战争。
3. 提刑主动拘捕成功后检查囚禁者与官职登记；请求拘捕成功后检查囚禁者为观察使且没有公职登记。跨路、宾客、中央大臣和官职持有者不能作为目标。
4. 测试提刑主动拘捕有地目标拒捕，确认战争针对观察使，战中俘获与战胜收押分别在次日转交提刑；白和平、战败、战争失效后清理待引渡标记。
5. 为提刑同时准备公职囚犯与私人囚犯，测试死亡、换任、空缺、撤销官职：只交接登记囚犯，保留软禁/地牢，不重复施加拘捕后果；释放、死亡后移除登记。
6. 发送后更换提刑、改变辖区或目标状态，确认回复时取消已失效拘捕；核对普通人物、皇帝、刑部尚书及合法摄政的原版入口，并在中英文检查通知和动态官衔。
7. 保存重载，复查官职绑定、囚犯登记及延迟引渡；记录其他 mod 同名覆盖和原版称号错误的影响。

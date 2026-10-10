# 司法互动的动态本地化

2026-10-10。本次只调整拘捕互动中英文文案，不改变司法权限或角色作用域。

## 原版写法与使用规则

- `[character.GetTitleAsName]`：读取角色当前官衔。纯文字标题使用 `GetTitleAsNameNoTooltip`。
- `[character.GetTitledFirstName]`：读取带官衔的人名，适合说明谁批准、关押或承担战争。通知标题使用 `GetTitledFirstNameNoTooltip`。
- `[character.GetShortUIName]`：按阅读者显示人名或“你”，用于上下文已经明确的后续指代。
- `[title.GetName]`：读取头衔当前名称，用于实际绑定的辖区或机构；`GetNameNoTierNoTooltip` 用于定义名称时避免附加等级和提示。

原版证据：`game/localization/simp_chinese/interactions/diarch_interactions_l_simp_chinese.yml:4` 使用 `GetTitledFirstName`，`:161` 使用 `GetTitleAsNameNoTooltip`，`:234` 使用 `GetTitleAsName`。`game/common/flavorization/11_tgp_china_flavorization.txt:223` 起按身份、政府等选择王国级官衔；`game/localization/simp_chinese/culture/culture_titles_l_simp_chinese.yml:1314` 是“观察使”的称号定义，而不是互动文案应重复写入的常量。

本 mod 的 `tca_celestial_duke_holder_*` 已接入原版 flavorization，`TCAJudicialHolderTitle` 根据当前主要头衔的标记返回 `tca_judicial_holder`。因此互动直接使用原版角色取名函数，不额外增加一套官衔选择器。`GetTitleAsName` 读取的是角色当前主要称号；不应用于人物兼任多个职位时指定次要官衔。当前提刑任职资格要求官职为主要头衔，符合这个使用条件。

## 本次调整

菜单动作名使用“请求批准拘捕”“辖区拘捕”，不依赖仅在 `redirect` 后取得的第三人作用域。说明、审批意愿与通知使用引擎标准互动角色 `secondary_recipient`（司法官员）、`intermediary`（审批人）、`secondary_actor`（辖区统治者），并沿司法官员主头衔的 `song_judicial_circuit` 读取辖区，动态显示官衔、人名及辖区名称。

官职名称本身仍在 `tca_judicial_holder`、`tca_judicial_title_name` 等身份定义中集中定义；这是制度名称的来源，不应删除。修改该身份定义或适用的 flavorization 后，互动文案应随之更新，无须逐条替换。

## 验证边界

已核对所用取名函数的本机原版用例，检查中英文键一致、表达式括号、UTF-8 BOM 和硬编码官衔残留。尚未验证引擎中的最终呈现，尤其是互动说明、第三人批准分解和通知标题是否都保留所需作用域。需要游戏内检查改名、换任及两种语言下的显示。此次本地化调整不代表此前拘捕实现已完成游戏验收。


## 首次游戏测试后的作用域修正

用户截图显示资格提示展开为“无的等级不是王国”和内部触发器名称。当前 `error.log` 确认 `tca_circuit`、`tca_commissioner`、`tca_governor`、`tca_authority` 在互动资格与提示求值时未定义；AI 模块另报 `Unknown modifier 'base'`。

修正后 `redirect` 只传递引擎文档列出的标准互动角色。检查与本地化直接读取这些角色；发送、否决、接受和拒捕效果开始时，才重新建立效果所需的自定义作用域。缺失角色时守卫检查阻止展开内部头衔条件，显示一个可读的资格提示。共用 AI scripted modifier 不再声明 `base`，基础值保留在各互动自己的 `ai_accept` / `ai_will_do` 中。

针对上述故障的静态回归检查通过；尚未重载游戏确认新的运行日志。旧日志中的错误不会因编辑文件消失。

## 提交前补充审查

补齐拘捕效果脚本 BOM，并为无主头衔角色的身份判断增加存在性守卫。官职持有资格及死亡交接改为明确保存头衔作用域，避免迭代中的 `prev.primary_title` 类型错误。审批不免除暴政，规格已同步。当前行为与完整待验收清单见 [司法拘捕说明](judicial_arrest.md)。

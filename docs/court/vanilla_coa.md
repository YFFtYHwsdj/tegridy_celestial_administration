# 原版随机纹章机制

本文记录 CK3 1.20.1.2（Crozier）的原版纹章配置，版本依据安装目录的 `launcher/launcher-settings.json`。仅核对原版文件，未启动游戏复现；不代表本模组已新增纹章机制。返回[官制名称与地方制度](README.md)。

下文路径以安装目录为根；`game/` 是游戏数据，`jomini/` 是引擎随附配置说明。行号仅用于本版本定位，游戏更新后应按对象名复核。

## 生成结构与上下文

随机纹章由条件筛选、带权重的候选列表和构图模板共同配置。整体模板决定布局，再从底纹、配色、图案列表中选取元素；具体元素也可以在模板中固定。并非所有纹章均随机生成，原版另有预设纹章和头衔动态切换规则。

`game/common/coat_of_arms/template_lists/coa_templates.txt:1` 定义 `coat_of_arms_template_lists`，其中 `all` 是通用模板列表。文件注释明确生成上下文：

- `scope:faith`、`scope:culture` 始终设置，分别是人物的信仰和文化。
- `scope:title` 是人物主头衔，可能不存在。
- 根作用域可能是人物；统治者设计器中人物尚未存在，应使用上述保存作用域。

候选项前的数字是权重，`special_selection` 用 `trigger` 限定条件。已见条件包括文化的 `has_coa_gfx`、信仰／宗教、主头衔的法理归属及政体标记。因此，风格入口不一定直接检查文化名称或文化传承，应复核实际纹章图形标记。

通用候选包含 `basic_charge_01`、`basic_charge_01b`、`basic_ordinary_01`、`basic_ordinary_01_inverted`，权重各为 3；条件候选另有十字、塔木加、日本家纹、中国印章等。配置存在未启用的注释候选，不能把它们计入实际生成池。

随附语法示例位于 `jomini/common/coat_of_arms/template_lists/readme.txt`。当前所读文件没有完整说明多个有效 `special_selection` 的合并、覆盖与嵌套优先关系；这些底层细节仍待引擎验证，不能仅凭局部权重推算最终概率。

## 模板与素材列表

主要维护位置：

- `game/common/coat_of_arms/coat_of_arms/01_random_templates.txt`：构图模板，固定或引用随机底纹、颜色和图案，设置位置、缩放、镜像及叠放。
- `game/common/coat_of_arms/template_lists/pattern_lists.txt`：底纹纹理候选及条件。
- `game/common/coat_of_arms/template_lists/color_lists.txt`：颜色候选及条件，包含 `normal_colors` 和 `metal_colors` 等列表。
- `game/common/coat_of_arms/template_lists/colored_emblem_lists.txt`：可着色图案候选及条件。
- `game/common/coat_of_arms/template_lists/textured_emblem_lists.txt`：纹理图案候选。
- `game/gfx/coat_of_arms/`：底纹及图案等实际素材。

例如 `01_random_templates.txt:23` 的 `basic_charge_01`：底纹引用 `basic_division`，两个底色引用 `normal_colors`，另两个颜色引用 `metal_colors`；中央图案引用 `charge`，使用后两个颜色，位置为 `{ 0.5 0.5 }`、缩放为 `{ 0.9 0.9 }`。随机变化受既定构图约束。

素材列表也有条件分支。例如 `pattern_lists.txt:21` 的 `basic_division` 包含纯色、竖分、斜分、横分；基督教条件下另列棋盘等候选。颜色和主体图案也有各自的权重与条件，并非选定整体模板后所有素材都等概率抽取。

## 中国文化组的印章

### 模板选择

`coa_templates.txt:631` 的入口条件是 `scope:culture = { has_coa_gfx = chinese_group_coa_gfx }`，分支内保留权重为 1 的 `chinese_seal_pictorial`，再根据 `has_recognizable_chinese_seal` 分流。

不能识别时，配置十种图像印章模板，每种权重 630：单图、边框、满边框、竖向组合、镜像以及分隔镜像等。

能识别时，配置三种简单姓氏模板，每种权重 5040：`chinese_seal_name`、`chinese_seal_frame_name`、`chinese_seal_frame_full_name`；另有十四种姓氏与图像组合模板，每种权重 1260。这里只记录配置权重，不换算最终命中率。

`01_random_templates.txt:9186` 起定义实际布局。例如 `chinese_seal_name` 使用纯色底纹、`normal_colors` 底色、`metal_colors` 字色，中央姓氏图案缩放为 `{ 0.7 0.7 }`；带框模板另叠加框纹。因此中国印章仍使用模板和配色列表，并未在这些模板中统一固定为朱白两色。

### 姓氏字样的来源

`colored_emblem_lists.txt:3634` 的 `chinese_seal_name` 按宗族的 `dynasty_has_base_name` 匹配预制 DDS 字样，不是即时把本地化姓氏渲染为篆字。

例如：

- `dynn_Wang_738B`、`dynn_Wang_738B_KO`、`dynn_Vuong_738B` 对应 `ce_seal_name_wang_738b.dds`。
- `dynn_Li_674E`、`dynn_I_674E`、`dynn_Ly_674E` 对应 `ce_seal_name_li_674e.dds`。
- 张、刘等姓氏同样登记相应名称键和贴图。

各匹配分支的字样权重为 100；列表还保留权重为 1 的 `ce_seal_name_chao_671d.dds`。结合尚未确认的条件列表选择细节，不能把名称匹配直接写成“绝对保证只生成对应字样”。

因此，仅新增或修改一个姓氏的显示文本，不会自动新增对应字样贴图和匹配规则。自定义宗族名、无匹配名称键，以及 `has_recognizable_chinese_seal` 对可识别性的完整判定范围，仍待引擎复现。

## 生成、复制与动态切换入口

原版脚本已使用以下入口，但完整参数及适用作用域仍应结合调用上下文核对：

- `generate_coa = yes`：请求生成纹章。例如 `game/common/scripted_effects/00_decisions_effects.txt:2943`、`:2953` 在特定家族支系命名分支中对新家族调用，原版注释说明用途是避免西式支系纹章。
- `generate_coa = factions`：指定专用生成列表，例如 `game/common/scripted_effects/00_faction_effects.txt:1775` 对新头衔调用。
- `set_coa`：指定预设纹章或复制已有对象的纹章。例如 `game/common/scripted_effects/10_dlc_tgp_scripted_effects.txt:4413` 使用 `set_coa = holder.house`。

不能据此推断所有家族支系都重新随机生成，或所有新头衔都必经同一列表；各类自动生成时机及默认行为仍有引擎部分。

头衔动态纹章由 `game/common/coat_of_arms/dynamic_definitions/` 维护。其 `_dynamic_definitions.info:1` 明确：对象名对应头衔，按顺序取第一项符合条件的 `item`，无匹配则回到该头衔默认纹章；`update_dynamic_coa = yes` 用于头衔作用域，相关条件变化时需要脚本在合适的回调中主动更新。这是按条件切换预设纹章，与随机模板选择分别维护。

## 验证边界与复核方式

本页结论来自原版配置及随附说明的静态阅读，未修改游戏或模组行为，未运行游戏测试。以下事项尚未验证：

- 随机种子、重复生成是否可能复用结果，以及条件列表的底层选择算法。
- 无预设纹章时各类对象的自动生成时机、文化／信仰变化后是否自动重生成。
- 中国姓氏可识别性、手动改名后的字样选择，以及缺少匹配时的实际回退。
- 各模板的实际显示、颜色对比、保存重载和组合加载表现。

后续如需实现或修复，应先核对更新后的原版对象及调用上下文；在独立、可丢弃测试局分别覆盖可识别姓氏、不可识别姓氏、非中国风格和家族支系路径，观察生成结果与保存重载。需要判断概率时，应先确认列表选择规则，再进行重复抽样；静态权重不作为实测频率。

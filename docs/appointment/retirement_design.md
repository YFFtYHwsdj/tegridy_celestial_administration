# 致仕与奉祠机制设计

本文件维护北宋“奉祠（祠禄官／提举宫观）”与“致仕（告老乞骸骨）”的机制设计规范。本模块与[官职任命](README.md)及[官署专职](../judicial/offices.md)共享候选超时机制，当前处于**设计完成、尚未落入可执行脚本**状态，**所有数值系数与加减分权重明确尚未最终拍板，留待后续平衡校准**。

---

## 一、历史制度依据与设计定位

### 1. 历史原貌：北宋祠禄官（奉祠）与告老致仕
* **奉祠（祠禄之制）**：宋真宗大中祥符年间始设宫观使副，神宗熙宁、元丰年间制度化推行名山宫观差遣（如主管洞霄宫、提举崇福宫等）。其本质为“备员养老、投闲养疾、避息党争”的带俸闲居职务，纯领转运司或朝廷国库之祠禄，不理州县刑政实务；大臣官阶与资历保留，朝局反转时可被召还起复。
* **致仕（告老乞骸骨）**：士大夫终老仕途的法定终局（礼制以七十为大限）。朝廷优礼老臣，定制赋予“致仕三恩”：
  1. **转官致仕（致仕赐阶）**：特旨加官一阶致仕（如工部侍郎致仕、正议大夫致仕）；
  2. **致仕荫补（恩荫子嗣）**：依官品格法，许荫子孙一人出仕为初阶官（如将仕郎、承务郎等，见《宋史·选举志·荫补》），系世家门第交接的核心法宝；
  3. **居乡优礼**：脱去职事，享有乡贤崇高声望。

### 2. 原版天朝机制痛点与补完目标
* **原版痛点与代码缺陷**：
  1. **出家荒谬**：原版退位决议（`renounce_noble_family_title_decision`）调用的底层效果（`10_dlc_tgp_japan_scripted_effects.txt:3867`）粗暴复用日本隐居入道逻辑，强制打上天主教/佛教修道者专属特质 `devoted`（堂堂儒家大臣退休变和尚），并附有官方待修注释 `# TODO TIT-74285`；
  2. **官职不卸**：若在任总督点击退位，原版代码判定 `is_governor = yes` 时只交出世家庄园，**大臣竟继续占着行省总督官位**，导致儿子当族长、老爹在外当大官的颠倒乱象；
  3. **AI 终身赖官**：原版对中过省试的中国 AI 文官写死 `factor = 0`，致仕律（`celestial_retirement_law`）沦为空设，八九十岁百岁老翁死占官僚大位；
  4. **缺乏半退休过渡**：辞官即彻底沦为无差遣白丁，既无退休俸禄，也无法体验幕后掌家的闲退阶段。
* **补完目标**：
  * 构建**“在任实职（总督/知州/监司/部臣） $\to$ 乞除奉祠（半退休带俸不切角色） $\to$ 乞骸骨（正式致仕加官恩荫传代）”**的完整官僚生命周期闭环。

---

## 二、底层脚本接口与技术实现方式

本设计全面复用原版原生安全接口，不暴力覆盖核心继承法文件：

1. **任官候选物理排除（`appointment_timeout`）**：
   * 原生所有地方总督（`celestial_governor.txt`）、中央尚书（`celestial_minister.txt`）及模组专职任命（`tca_official_appointments.txt`）均声明了 `cooldown = yes`；
   * 只要调用 `set_appointment_timeout = { years = 150 }`，引擎二进制底层 `NAdministrative::IsCandidateOnCooldown` 判定 `appointment_timeout_days > 0` 即可将角色物理排除出全国任何候选池；起复时调用 `clear_appointment_timeout = yes`。
2. **解卸官职安全清退（`force_step_down_landed_titles`）**：
   * 彻底废弃原版粗暴的世家剥离逻辑，在卸任实职与致仕时调用原版原生安全接口 `force_step_down_landed_titles = yes`，平稳将管辖州县与监司差遣交还朝廷重新铨选；若为中央六部尚书，追加调用 `fired_minister_position_effect = yes`。
3. **真实朝廷俸禄预算（`treasury_salary_budget`）**：
   * 区别于凭空产生金币的 `monthly_income`，特质挂载 `monthly_treasury_from_salary_budget_base`，直接切取朝廷国库预算池（`treasury_salary_budget`）转化为每月金币，随朝廷财政盈亏联动。
4. **老年病症经验条分级（Age-related Ailment Tracks / XP）**：
   * 原版老年特质（`infirm` 体弱、`withering_mind` 昏聩、`clouded_eyes` 昏花、`faltering_heart` 心衰、`fragile_bones` 骨脆）均带有 0–100 经验条（XP）；
   * 通过原生条件 `has_trait_xp = { trait = <name> value >= <X> }` 识别中度（XP $\ge 50$）与重度（XP $\ge 75$），精准驱动半休与全退决策。
5. **门荫免试资格复用（`tgp_nepotism_bypass_exams_modifier`）**：
   * 原版已有文化传统“荫庇”修饰符（`tgp_nepotism_bypass_exams_modifier`，使角色规避科举考试），致仕恩荫时直接赋予新接班人或未入仕亲子。

---

## 三、双轨退休机制具体内容与脚本调用

### 阶段一：半退休——乞除奉祠（`tca_petition_fengci_decision`）

* **定位**：官员精力不济、患病或厌烦政争时，退居二线在老家教养子弟；**绝不切换角色**。
* **准入条件（Trigger）**：
  * **资历门槛**：`merit_level >= 4`（六品 / Rank 6 以上，升朝官资历，排除初任选人）；
  * **生理/年龄门槛**（满足其一）：
    * 年满 60 岁；
    * 或身患老年病症（`has_trait_flag = age_related_ailment`，尤其在中度 XP $\ge 50$ 时）；
    * 或中风瘫痪（`has_trait = incapable`）。
* **执行效果（Effect）**：
  * 若在任差遣，调用 `force_step_down_landed_titles = yes` 卸下实职头衔；
  * 赋予专属特质 **`tca_trait_fengci`**（带有 `monthly_treasury_from_salary_budget_base` 国库俸禄基数，并挂载 `monthly_influence_mult = -0.50` 削减影响力获取）；
  * 执行 `set_appointment_timeout = { years = 150 }` 排除出任官候选；
  * **玩家继续扮演当前角色**，打理世家庄园、著述授徒、幕后经营宗族。

---

### 阶段二：全退休——乞骸骨（`tca_retire_decision`）

* **定位**：达到朝廷大限或大限将至，彻底脱下官袍告老还乡；**正式传代交接家族**。
* **准入条件（Trigger）**：
  * 成年世家领袖，有合格成年继承人；拥有六品以上官僚资历；
  * **法律与健康判定**（满足其一）：
    1. **法定致仕**：年龄达到帝国法律致仕律规定（调用 `tgp_is_above_retirement_age_trigger = { REALM_OWNER = root }`，如 70 岁）；
    2. **老病特恩以疾乞骸骨**：虽未达法定年龄，但心智衰竭/失明瘫痪（如 `has_trait = incapable` 或老年病症 XP $\ge 75$）。
* **执行效果（Effect）**：
  * **解职**：清退所有在任领地与省部差遣（`force_step_down_landed_titles = yes`）；
  * **退休特质**：赋予专属退休特质 **`tca_trait_retired`**（享有部分优厚退休金、增加家族威望、影响力增长归零），并设永久超时；**彻底剔除 `devoted` 僧侣特质**；
  * **致仕赐阶**：皇帝褒赏其一生功劳，官阶晋升一级（`change_merit_level = 1`，加官致仕）；
  * **致仕恩荫**：若达高阶（如 Merit $\ge 5$），特赐子孙一人初品仕籍（赋予继承人或次子 `tgp_nepotism_bypass_exams_modifier` 及初始 Merit）；
  * **世家传代**：将族长与宅邸头衔交还继承人，调用 `set_player_character = scope:new_player` 正式换代。

---

## 四、AI 行为意愿与评分模型（AI Score）

> [!NOTE]
> 以下权重与加减分仅作为逻辑倾向草案，**具体数值明确尚未正式拍板**，后续将根据实际测试局的官员寿命与空缺流转率校准。

### 1. 乞除奉祠 AI 意愿（`ai_will_do`）
* **核心倾向**：知足常乐、老病衰颓、避祸消灾。
* **加分项**：
  * 年龄阶梯（65 岁以上微增，70 岁以上显著增加）；
  * 老年病症中度加深（`infirm`、`clouded_eyes`、`faltering_heart` 等特质 XP $\ge 50$ 显著加分）；
  * 官场压力巨大（`stress_level >= 2`）；
  * 性格特质：`content`（知足不辱）、`lazy`（贪图闲散纯领钱）、`humble`（谦逊）、`temperate`（节制）；
  * 君臣关系恶劣（与领主好感度低，急流勇退以自保）。
* **减分项**：
  * 恋栈权势：`ambitious`（野心勃勃）、`arrogant`（傲慢）大幅减分，非病不退。

### 2. 乞骸骨正式致仕 AI 意愿（`ai_will_do`）
* **核心倾向**：遵从礼法大限、为子嗣铺路、身体崩溃交棒。
* **加分项**：
  * 彻底丧失能力：`incapable` 瘫痪或病症进入晚期（XP $\ge 75$）直接赋予绝对高分，必定致仕；
  * 已在奉祠状态：挂有 `tca_trait_fengci` 多年的高龄老臣，顺理成章转为正式告老；
  * 超龄阶梯：75 岁以上递增，80 岁以上高额加分（彻底杜绝百岁老妖把持世家）；
  * 继承人素质：成年继承人年富力强且能力优秀，老臣乐于交棒；
  * **子嗣缺官诱因**：若继承人尚未取得仕籍，老爹致仕可触发“致仕恩荫”送儿子入仕，大幅激发退位意愿。
* **减分项**：
  * 继承人品行败坏或有恶名罪行，老家主推迟交权；
  * `ambitious` 野心特质大幅抗拒彻底退位（但在瘫痪或 80 岁以上时该抗拒将被老病权重压制）。

---

## 五、验证边界与接续计划

1. **当前状态**：文档级系统设计完备，已核验原生接口契约；可执行脚本与本地化文本待后续统一排期。
2. **待验证接口**：
   * 非总督的世家族长挂载 `monthly_treasury_from_salary_budget_base` 时国库月度折算的稳定性；
   * `tgp_nepotism_bypass_exams_modifier` 在成人亲子身上的初任补官顺位表现；
   * AI 奉祠与致仕在 1066 年百年推演局中对全国官缺流转速度的真实影响。

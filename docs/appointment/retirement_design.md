# 致仕与奉祠机制设计

本文件维护北宋“奉祠（祠禄官／提举宫观）”与“致仕（告老乞骸骨）”的机制设计规范。本模块与[官职任命](README.md)及[官署专职](../judicial/offices.md)共享候选超时机制，当前处于**设计完成、尚未落入可执行脚本**状态。

---

## 一、历史制度依据与设计定位

### 1. 历史原貌：北宋祠禄官（奉祠）
* **缘起与定制**：宋真宗大中祥符年间置玉清昭应宫等宫观使副，神宗熙宁、元丰年间正式推行制度化“祠禄之制”（如主管洞霄宫、提举崇福宫等名山宫观差遣）。
* **制度实质**：
  * **备员养老、投闲养疾**：大夫年及六十、筋力不逮、或患风眩目疾而不耐剧邑案牍者，朝廷给以宫观名号，居乡奉祠。
  * **纯食其禄，不预政事**：按月/年支领转运司或朝廷国库拨发之祠禄钱米，不承担知州、通判等治民断狱之责。
  * **政争出局的体面缓冲与起复枢纽**：大臣在朝堂新旧党争中求去或罢执政，朝廷优礼老臣，特许除宫观差遣分司西京。在祠期间保留散官阶与资历，遇新帝即位或政局反转，随时可下诏“起复”重返朝堂。
  * **终极归宿**：年满七十或真正病危，再上表“乞骸骨”，以加官一阶或高阶散官正式致仕。

### 2. 原版天朝机制痛点与补完目标
* **原版痛点**：
  1. 原版退位决议（`renounce_noble_family_title_decision`）强制切换角色给继承人，玩家无法体验老臣退居幕后的半退休阶段；
  2. 辞去官职决议（`renounce_governorship_decision`）在天朝功绩制下不发退休抚恤，官员瞬间失去所有官俸收入；
  3. 缺乏士大夫“带俸闲居、著述教子、幕后掌家”的渐进式退休生态。
* **补完目标**：
  * 构建**“在任实职（总督/知州/部臣） $\to$ 乞除奉祠（半退休带俸不切角色） $\to$ 乞骸骨（正式致仕传代）”**的完整官僚生命周期闭环。

---

## 二、原版底层机制与接口基线

原版行政制与天朝官僚底层已提供现成接口，无需破坏性覆盖原生继承法文件：

1. **法定致仕年龄（`celestial_retirement_law`）**：
   * 原版包含 0–5 级致仕律（50/60/70/80/90/无固定）。超龄者在地方及中央任命评分中按超龄年岁倒扣候选分（`tgp_is_above_retirement_age_trigger`）。
2. **任官候选硬排除（`appointment_timeout`）**：
   * 原版所有地方总督（`celestial_governor.txt`）、中央尚书（`celestial_minister.txt`）及模组专职任命（`tca_official_appointments.txt`）均声明了 `cooldown = yes`。
   * 引擎底层 `NAdministrative::IsCandidateOnCooldown` 判定角色的 `appointment_timeout_days > 0` 即物理排除出候选池。
   * 原版谢绝任命决议（`tgp_refuse_appointments_decision`）通过 `set_appointment_timeout = { years = 150 }` 实现伪永久排除，恢复时调用 `clear_appointment_timeout = yes`。
3. **真实朝廷俸禄预算（`treasury_salary_budget`）**：
   * 区别于凭空产生金币的 `monthly_income`，天朝官僚使用帝国国库俸禄预算系统。
   * 皇帝行政法通过 `treasury_salary_budget_allocation` 划拨国库预算池；
   * 官员通过底层修饰符 `monthly_treasury_from_salary_budget_base` 切取国库资金按月转化为个人金币（`gold`）。

---

## 三、“奉祠”特质与决议设计规范

### 1. 准入门槛（决议条件：`tca_petition_fengci_decision`）
* **品阶/资历门槛**：**`merit_level >= 4`（六品 / Rank 6 以上）**。
  * **历史依据**：宋代排斥底层“选人”请祠，必须是脱离选人序列、具有磨勘转官资历的“升朝官/京朝官”。六品正好涵盖通判、中下等知州及寺监丞郎。
* **生理/年龄门槛**（满足其一）：
  * 年龄 $\ge 60$ 岁；
  * 或身患原版老年病症特质群（`has_trait_flag = age_related_ailment`，涵盖 `infirm` 体弱、`withering_mind` 昏聩、`clouded_eyes` 昏花、`faltering_heart` 心力衰竭、`fragile_bones` 骨脆，以及 `incapable` 瘫痪）。
* **差遣经历**：
  * 当前在任总督、通判、提刑或中央尚书，或因已有六品资历曾实任外藩/京朝官。

### 2. 核心特质：`tca_trait_fengci`（奉祠 / 提举宫观）
* **真实国库俸禄**：
  * 赋予 `monthly_treasury_from_salary_budget_base = 0.2`（或与品阶联动），直接从朝廷俸禄预算池按月支领真金白银。若朝廷国库亏空，其俸禄同步受影响。
* **行政与政治限制**：
  * 决议触发时若在任实职，自动交卸当前差遣头衔；
  * 执行 `set_appointment_timeout = { years = 150 desc = appointment_timeout_desc_fengci }`，全域排除出官僚候选池；
  * `monthly_influence_mult = -0.50`（退居二线，大幅减少月度影响力获取）。
* **操作延续性（不切换角色）**：
  * **绝不触发** `set_player_character`。玩家继续扮演该角色打理世家庄园、培养儿孙、经营联姻与私产。

### 3. 后续流转机制（生命周期出口）
* **分支 A：起复出仕（预留）**：
  * 遇朝局变动、新帝登基或政治反转，朝廷可下诏除特质并 `clear_appointment_timeout = yes`，重返仕途。
* **分支 B：乞骸骨正式致仕（待完善）**：
  * 年老（如 70 岁以上）或角色行将就木，可触发正式致仕决议：
  * 赐予荣誉致仕头衔/散官称谓；
  * 此时交卸世家族长并传代给合法继承人（`set_player_character = scope:new_player`）；
  * 给予家族后代一次性“致仕恩荫”入仕功绩点或加分。

---

## 四、验证边界与开发状态

1. **当前状态**：纯文档设计与接口核验，**未修改可执行脚本、未新增 trait 或 decision 文件**。
2. **待验证项**：
   * `monthly_treasury_from_salary_budget_base` 挂载在非知州总督的世家族长身上时，底层国库金币月度结算账目的实际转化表现；
   * `set_appointment_timeout` 与本模组专职官署继承法（通判、提刑）的联动稳定性；
   * AI 官员在符合 60 岁/病症门槛时的主动请祠权重配置。

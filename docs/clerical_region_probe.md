# 王国级圣职区验证记录（已终止并归档）

## 当前结论与加载状态

2026-10-10 结束验证，放弃将原生圣职区作为天朝提点刑狱司头衔的实现路线。测试只证明若干技术组合可以运行，不代表该机制适合天朝行政玩法。

用户在游戏中观察到：宗教圣职区与其他宗教的圣职区共同显示，并参与宗教间竞争。结合本轮已验证的宗教上级关系，以及原版圣职区的租赁、宗教互动和失配处理链，圣职区与宗教绑定过深。强行挪作天朝官职需要持续干预宗教机制，也会影响天朝自身可能采用的宗教玩法。因此不继续做正式迁移或进一步隔离实验。

已移除本次测试的头衔、人物与头衔历史、区域定义、两个事件文件及中英本地化，共 8 个文件。特别是对 `pam_clergy_events.0051/.0052` 的测试覆盖已移除，模组不再由该原型覆盖这两个原版事件。完整最终源码保存在本文附录的代码块中，文档不会作为游戏脚本加载。正式提刑仍沿用既有公国方案。

清理在磁盘上完成；已经运行的游戏进程需完全退出后重新启动才会重新加载。历史测试存档包含原型对象，不作为清理后正式游戏的验收存档；本轮未修改或迁移存档。未修改安装游戏或 Workshop 文件。

## 原型设计与原版依据

目标是验证预定义王国级无地头衔能否挂载原生圣职区并保留天朝政体。测试头衔为 `k_tca_clerical_probe`，人物为 `tca_clerical_probe_holder`，区域为 `tca_clerical_probe_region`，涵盖洪州与筠州（`c_hongzhou`、`c_yunzhou_2`）；1066 年直属 `h_china`，初始道学礼仪、天朝政体。没有给测试头衔加正式提刑标记。

本轮核对的本机版本为 1.20.0.4，参考入口均相对于安装目录 `game/`：

- `history/titles/ce3/00_ecclesiastical_titles.txt`：`d_et_toledo` 的头衔历史通过 `clerical_region = et_867_toledo_region` 挂载区域；测试使用历史挂区路径。原生动态创建圣职区接口固定公国等级。
- `common/scripted_effects/pam_effects.txt`：头衔作用域 `every_county_in_clerical_region`；人物 `superior` 可用于选择宗教互动收件人。
- `events/dlc/pam/pam_clergy_events.txt`：`.0051/.0052` 处理失配，使用文件内辅助效果 `pam_strip_personal_landed_titles_effect`。
- `gui/window_character.gui`：宗教上级头像使用 `CharacterWindow.GetCharacter.GetReligiousSuperior`，显示条件未限定教会政体；该区块的好感代码却使用 `GetLiege`，不能把头像下好感当作宗教上级好感的独立证据。
- `common/character_interactions/_character_interactions.info`：`superior` / `top_superior` 是宗教层级互动对象。
- `common/lease_contracts/_lease_contracts.info`、`00_theocracy_lease.txt`：圣职区租赁层级为寺庙承租人 → 圣职区持有者 → 信仰领袖；区域持有者按承租人领主首都确定，实际参与有教义、信仰及政体等条件。
- `common/character_interactions/pam_interactions.txt`：例如 `request_ecclesiastical_treasury_interaction` 要求发起人与收件人均具有 `government_is_ecclesiastical`，有宗教上级不等于所有宗教互动自动可用。
- 本模组 `tca_is_judicial_circuit_trigger` 排除无地类型头衔，因此原型没有进入正式提刑维护范围。

## 验证结果与证据边界

### 已确认的有限结果

- 预定义王国级无地头衔可在初始状态挂载原生圣职区、覆盖指定两个县，并保留天朝政体。
- 本测试局日/月推进、一次完全退出后存档重载保持上述基础状态；修正诊断作用域后确认直属宋朝中央。
- 一次死亡交接采用功绩任命（用户界面观察），日志独立确认换人后基础状态与辖区保持。
- 原版未隔离的改宗触发失配剥离与换人；隔离 `.0051/.0052` 后，一次改宗及一天推进中原人物、天朝政体、中央直属及两县保持。
- 改宗存档再次重载后，测试官仍有教宗作为宗教上级、没有教会政体标记，并保留天朝领地继承法。
- 用户观察确认圣职区显示和竞争属于宗教玩法；这项来自用户游戏观察，未由诊断事件独立量化。

### 未验证且不再继续验证

独立官署住所生成、逐县扩区/移除、跨信仰长期稳定、实际寺庙税收与宗教互动权限、全部任命资格及调任/辞职边界均未验证。诊断 `.2` 的领地继承法检查不替代头衔任命界面检查。未找到可直接设置或清除任意人物 `superior` 的接口，但没有导出完整脚本文档，不能断言引擎绝无此接口。

结论是该路线不适合项目，而不是王国级圣职区无法加载；保留这些技术结果用于避免重复试验。

## 历史测试过程（不再作为待办）

以下时间均来自 2026-10-10 当轮日志。日志为游戏用户目录 `logs/debug.log`、`logs/game.log`、`logs/error.log`；诊断标识为 `TCA_CLERICAL_PROBE`。

1. **21:03:48 初始挂载**：REGION、KINGDOM、LANDLESS、HOLDER、HONGZHOU、YUNZHOU、EXCLUDED_FROM_CIRCUITS、CELESTIAL 全部 YES，COUNTY_ENTRY 两条。截图日期 1066.9.15，区域地图着色且官员为天朝政体。初版 CENTRAL_LIEGE 在头衔作用域误用人物 liege，NO 无效；随后改为 `holder.liege = title:h_china.holder`。
2. **21:06:38、21:06:55 日/月推进**：用户完成推进 1 天和 1 个月，两轮基础项仍 YES、县条目两条。游戏尚未加载诊断修正，CENTRAL_LIEGE 仍有旧版作用域错误。事件没有比较人物身份或县礼仪，不能证明期间未换人或传播。
3. **21:09:31 完全退出重启、读档**：所有基础项 YES，包括 CENTRAL_LIEGE，县条目两条。用户反馈未遇到宗教失配；截图有天朝庄园入口（庙昌），不能据此确认独立官署或圣职住所。
4. **21:13:26、21:13:41 死亡交接**：旧任历史人物 32188（tca_clerical_probe_holder）更换为王安石 32398（han_7436）；诊断全部 YES、两县保持。功绩任命依据为用户界面观察；未覆盖全部任命边界。
5. **21:15:08–21:15:32 未隔离改宗**：执行天主教改宗后，日志记录 `on_clerical_region_faith_mismatch` → `.0052` → `pam_strip_personal_landed_titles_effect`，同时报告 old_rite 未设置。21:15:13 新任为 67568（Xu_980A），并非王安石。两轮基础区域项 YES，但 CELESTIAL=NO；截图显示天主教、罗马礼、神职人员任命法。失败是剥离旧任并神职接任，不能直接归因为同一人物被引擎强制改政体。
6. **失配隔离原型**：复制本机 `.0051/.0052`，设置 `id_override_priority = 1`，在事件级 trigger 排除测试头衔，保留其他条件、选项和效果。覆盖原版两个事件会与其他模组的同 ID 覆盖竞争；从未视为正式实现。
7. **21:18:21、21:18:24 隔离重试证据不足**：仍 CELESTIAL=NO，其余基础项 YES；截图旧官成为冒险者并采用营地继承制。日志没有新覆盖加载证据，不能证明隔离有效后仍失败。检查发现 `.0051` 排除误加到背景 trigger，已移至事件级 trigger；诊断加入 VERSION=2。
8. **21:24:35 版本 2**：基线全部 YES，但启动日志报原版 file-local 辅助效果不能在覆盖文件调用。本轮不能证明覆盖正确。将辅助效果完整复制为文件内 `tca_probe_strip_personal_landed_titles_effect`，两个覆盖事件改用该名称，诊断升为版本 3。
9. **21:28:21、21:28:46 版本 3 改宗隔离**：全部基础项 YES、每组县条目两条；game.log 在改宗前后打开同一人物 32188。结合用户完成步骤与截图，确认改宗及一天推进后保留原人物、天朝政体、中央直属和两县。未再检出 file-local 调用错误或 `.0051/.0052` 失配处理调用；不代表全部宗教处理关闭。截图同时显示天主教、罗马礼、天朝政体、“上级”和“领主”。
10. **21:54:52 宗教层级诊断**：完全退出重启、读档后 `.2` 完整运行。人物仍为 32188；superior 是教宗国 `k_papal_state` 持有者 30490（历史 ID 2008，Alexander_regnal 达·巴焦）。SUPERIOR=YES、SUPERIOR_IS_LIEGE=NO、SUPERIOR_IS_HOF=YES、SUPERIOR_IS_RITE_HEAD=YES、ECCLESIASTICAL_FLAG=NO、CELESTIAL_REALM_LAW=YES。没有相关作用域或加载错误。该事件没有重新检查区域县数或政体精确类型。

两个手动诊断事件出现 orphaned 提示，与没有自动调用的测试用途一致；其他模组日志错误未在本轮处理。历史复现顺序为：启用原型后新开 1066 宋朝 → 暂停运行 `.1` → 日/月推进 → 完全退出重启读档 → 独立测试分支死亡交接 → 改宗失配 → 加载隔离版本 3 后从改宗前基线重试 → 保存改宗局、重启读档运行 `.2`。这一顺序仅为历史记录，不要求恢复原型或继续执行。

## 清理检查

归档后逐文件从附录还原字节并校验 SHA-256，确认与删除前完全一致；本地化 BOM 状态一并保留。检查模组加载目录中不存在本原型标识或对两个原版失配事件的测试覆盖，README 已改为终止验证与归档入口。执行 `git diff --check`。这属于文件归档及静态清理检查，未进行清理后引擎启动或游戏内回归验证。

## 附录：移除的原型文件完整源码

以下 8 个文件是清理前最终版本。路径为原模组相对路径；正文保留原始内容，代码块不含文件开头的 UTF-8 BOM，BOM 状态单独注明。所有文件使用 LF 换行且以换行结尾。需要核对归档时，将代码块正文以 UTF-8 编码，并按记录补上 BOM，即可计算对应 SHA-256。仅供查阅，不应把这些文件重新加入正式模组加载目录。

### `common/landed_titles/tca_clerical_probe.txt`

编码：UTF-8；BOM：有；字节数：234。

SHA-256：`4b0e6fef862172dd9b2333ad92113bfe1613be62f2bcb96635eaf8c050f29cc7`

```text
# Temporary validation fixture. No linkage to production judicial maintenance.
k_tca_clerical_probe = {
 color = { 120 180 220 }
 capital = c_hongzhou
 landless = yes
 no_automatic_claims = yes
 always_follows_primary_heir = yes
}
```

### `history/characters/tca_clerical_probe.txt`

编码：UTF-8；BOM：有；字节数：214。

SHA-256：`7e6674ff7ac0a8afdd37442f9b2fcc45be541d0acb464ec65361995ea5776297`

```text
tca_clerical_probe_holder = {
 name = tca_clerical_probe_holder_name
 dynasty = zhao_8D99_41
 culture = han
 rite = daoxue
 trait = education_learning_3
 1020.1.1 = { birth = yes }
 1100.1.1 = { death = yes }
}
```

### `history/titles/tca_clerical_probe.txt`

编码：UTF-8；BOM：有；字节数：184。

SHA-256：`2aacd51f6a4a872c88452bb4c92f7b52353fa59f17237fa701c45c9f9761545f`

```text
k_tca_clerical_probe = {
 1066.1.1 = {
  liege = h_china
  holder = tca_clerical_probe_holder
  government = celestial_government
  clerical_region = tca_clerical_probe_region
 }
}
```

### `map_data/geographical_regions/tca_clerical_probe.txt`

编码：UTF-8；BOM：有；字节数：74。

SHA-256：`ccf0ffe988e51146a6f7c9452445f2dba32a1e35bec96ab1b0b150632832d865`

```text
tca_clerical_probe_region = {
 counties = { c_hongzhou c_yunzhou_2 }
}
```

### `events/tca_clerical_probe_events.txt`

编码：UTF-8；BOM：有；字节数：5439。

SHA-256：`3578bcbd271bc983b64a784d52fdb6a2a17b8a320e95060fb1166d5f3bd773b5`

```text
namespace = tca_clerical_probe

# Manual, read-only diagnostics. Never scheduled by production on_actions.
tca_clerical_probe.1 = {
    type = character_event
    hidden = yes
    immediate = {
        debug_log = "TCA_CLERICAL_PROBE BEGIN"
        debug_log = "TCA_CLERICAL_PROBE DIAGNOSTIC_VERSION=3"
        title:k_tca_clerical_probe = {
            if = {
                limit = { has_clerical_region = yes }
                debug_log = "TCA_CLERICAL_PROBE REGION=YES"
            }
            else = {
                debug_log = "TCA_CLERICAL_PROBE REGION=NO"
            }
            if = {
                limit = { tier = tier_kingdom }
                debug_log = "TCA_CLERICAL_PROBE KINGDOM=YES"
            }
            else = {
                debug_log = "TCA_CLERICAL_PROBE KINGDOM=NO"
            }
            if = {
                limit = { is_landless_type_title = yes }
                debug_log = "TCA_CLERICAL_PROBE LANDLESS=YES"
            }
            else = {
                debug_log = "TCA_CLERICAL_PROBE LANDLESS=NO"
            }
            if = {
                limit = { exists = holder }
                debug_log = "TCA_CLERICAL_PROBE HOLDER=YES"
            }
            else = {
                debug_log = "TCA_CLERICAL_PROBE HOLDER=NO"
            }
            if = {
                limit = { exists = holder holder.liege = title:h_china.holder }
                debug_log = "TCA_CLERICAL_PROBE CENTRAL_LIEGE=YES"
            }
            else = {
                debug_log = "TCA_CLERICAL_PROBE CENTRAL_LIEGE=NO"
            }
            if = {
                limit = { any_county_in_clerical_region = { this = title:c_hongzhou } }
                debug_log = "TCA_CLERICAL_PROBE HONGZHOU=YES"
            }
            else = {
                debug_log = "TCA_CLERICAL_PROBE HONGZHOU=NO"
            }
            if = {
                limit = { any_county_in_clerical_region = { this = title:c_yunzhou_2 } }
                debug_log = "TCA_CLERICAL_PROBE YUNZHOU=YES"
            }
            else = {
                debug_log = "TCA_CLERICAL_PROBE YUNZHOU=NO"
            }
            if = {
                limit = { tca_is_judicial_circuit_trigger = no }
                debug_log = "TCA_CLERICAL_PROBE EXCLUDED_FROM_CIRCUITS=YES"
            }
            else = {
                debug_log = "TCA_CLERICAL_PROBE EXCLUDED_FROM_CIRCUITS=NO"
            }
            if = {
                limit = { exists = holder }
                holder = {
                    if = {
                        limit = { has_government = celestial_government }
                        debug_log = "TCA_CLERICAL_PROBE CELESTIAL=YES"
                    }
                    else = { debug_log = "TCA_CLERICAL_PROBE CELESTIAL=NO" }
                }
            }
            every_county_in_clerical_region = {
                debug_log = "TCA_CLERICAL_PROBE COUNTY_ENTRY"
            }
        }
        debug_log = "TCA_CLERICAL_PROBE END"
    }
}

# Manual religious hierarchy diagnostics; no state changes.
tca_clerical_probe.2 = {
    type = character_event
    hidden = yes
    immediate = {
        debug_log = "TCA_CLERICAL_PROBE HIERARCHY_BEGIN VERSION=1"
        title:k_tca_clerical_probe = {
            if = {
                limit = { exists = holder }
                holder = {
                    debug_log_scopes = yes
                    if = {
                        limit = { exists = superior }
                        debug_log = "TCA_CLERICAL_PROBE SUPERIOR=YES"
                        superior = { debug_log_scopes = yes }
                        if = {
                            limit = { superior = liege }
                            debug_log = "TCA_CLERICAL_PROBE SUPERIOR_IS_LIEGE=YES"
                        }
                        else = { debug_log = "TCA_CLERICAL_PROBE SUPERIOR_IS_LIEGE=NO" }
                        if = {
                            limit = { exists = faith.religious_head superior = faith.religious_head }
                            debug_log = "TCA_CLERICAL_PROBE SUPERIOR_IS_HOF=YES"
                        }
                        else = { debug_log = "TCA_CLERICAL_PROBE SUPERIOR_IS_HOF=NO" }
                        if = {
                            limit = { exists = rite.head_of_rite superior = rite.head_of_rite }
                            debug_log = "TCA_CLERICAL_PROBE SUPERIOR_IS_RITE_HEAD=YES"
                        }
                        else = { debug_log = "TCA_CLERICAL_PROBE SUPERIOR_IS_RITE_HEAD=NO" }
                    }
                    else = { debug_log = "TCA_CLERICAL_PROBE SUPERIOR=NO" }
                    if = {
                        limit = { government_has_flag = government_is_ecclesiastical }
                        debug_log = "TCA_CLERICAL_PROBE ECCLESIASTICAL_FLAG=YES"
                    }
                    else = { debug_log = "TCA_CLERICAL_PROBE ECCLESIASTICAL_FLAG=NO" }
                    if = {
                        limit = { has_realm_law = celestial_appointment_succession_law }
                        debug_log = "TCA_CLERICAL_PROBE CELESTIAL_REALM_LAW=YES"
                    }
                    else = { debug_log = "TCA_CLERICAL_PROBE CELESTIAL_REALM_LAW=NO" }
                }
            }
            else = { debug_log = "TCA_CLERICAL_PROBE HIERARCHY_HOLDER=NO" }
        }
        debug_log = "TCA_CLERICAL_PROBE HIERARCHY_END"
    }
}
```

### `events/tca_clerical_probe_mismatch_overrides.txt`

编码：UTF-8；BOM：有；字节数：7481。

SHA-256：`8273d28bb49c0ce2b609723d585175d82f8864097cab4a1a4f6c6455a6ec5654`

```text
namespace = pam_clergy_events

# Original file-local helper copied unchanged under an independent local identifier.
scripted_effect tca_probe_strip_personal_landed_titles_effect = {
	if = {
		limit = {
			any_held_title = {
				tier >= tier_county
				has_clerical_region = no
			}
		}
		create_title_and_vassal_change = {
			type = revoked
			save_scope_as = pam_strip_land_change
			add_claim_on_loss = no
		}

		if = {
			limit = { scope:reason ?= flag:character_converted }
			if = {
				limit = {
					primary_heir = {
						rite ?= root.var:old_rite
						OR = {
							is_ruler = no
							government_has_flag = government_is_theocracy
						}
					}
				}
				primary_heir ?= { save_scope_as = heir }
			}
			else_if = {
				limit = {
					player_heir = {
						rite ?= root.var:old_rite
						OR = {
							is_ruler = no
							government_has_flag = government_is_theocracy
						}
					}
				}
				player_heir ?= { save_scope_as = heir }
			}
			# final fallback, I don't think we need this...
			else = {
				create_character = {
					template = monk_character_template
					employer = root
					save_scope_as = heir
				}
			}
		}
		else = {
			if = {
				limit = { liege != this }
				liege ?= { save_scope_as = heir }
			}
			else_if = {
				limit = { exists = primary_heir }
				primary_heir ?= { save_scope_as = heir }
			}
			else_if = {
				limit = { exists = player_heir }
				player_heir ?= { save_scope_as = heir }
			}
			# final fallback, I don't think we need this...
			else = {
				create_character = {
					template = monk_character_template
					employer = root
					save_scope_as = heir
				}
			}
		}
		if = {
			limit = { scope:reason ?= flag:character_converted }
			scope:heir = {
				set_character_rite = root.var:old_rite
			}
		}
		every_held_title = {
			limit = {
				tier >= tier_county
				trigger_if = {
					limit = {
						scope:reason != flag:character_converted
					}
					has_clerical_region = no
				}
			}
			change_title_holder_include_vassals = {
				holder = scope:heir
				change = scope:pam_strip_land_change
			}
		}
		resolve_title_and_vassal_change = scope:pam_strip_land_change
		if = {
			limit = { scope:reason = flag:character_converted }
			scope:heir = {
				change_government = faith.faith_theocratic_goverment_type
				rite = { force_refresh_head_of_rite = yes }
				if = {
					limit = { should_use_theocratic_elective_succession_law_trigger = yes }
					add_realm_law_skip_effects = theocratic_elective_succession_law
				}
			}
		}
	}
}

# Validation-only overrides of vanilla 1.20.0.4 events. All other titles retain original behavior.

pam_clergy_events.0051 = {
	id_override_priority = 1
	theme = faith
	type = character_event
	title = pam_clergy_events.0051.t
	desc = pam_clergy_events.0051.desc

	override_background = {
		trigger = {
 religion = religion:christianity_religion }
		reference = pam_gothic_cathedral_interior
	}
	override_background = {
		reference = temple
	}

	trigger = {
		# Only the temporary secular fixture bypasses religion mismatch handling.
		NOT = { scope:title = title:k_tca_clerical_probe }
		is_ai = no
		faith = { has_doctrine_parameter = has_clerical_regions }
		scope:county.faith = { has_doctrine_parameter = has_clerical_regions }
		faith != scope:county.faith
		scope:reason = flag:county_converted
	}

	immediate = {
		faith = { save_scope_as = old_faith }
		scope:county.faith = { save_scope_as = new_faith }
		scope:county.rite = { save_scope_as = new_rite }
		scope:new_faith.religion = { save_scope_as = new_religion }
		pam_find_translation_clerical_region_effect = {
			EXCLUDE_RULER_REALM = no
			EXCLUDED_RULER = root
		}
		# Pope / Head of Faith, else Head of Rite — your current religious superior
		if = {
			limit = {
				exists = faith.religious_head
				faith.religious_head != root
			}
			faith.religious_head = { save_scope_as = religious_superior }
		}
		else_if = {
			limit = {
				exists = rite.head_of_rite
				rite.head_of_rite != root
			}
			rite.head_of_rite = { save_scope_as = religious_superior }
		}
	}

	left_portrait = {
		character = root
		triggered_animation = {
			trigger = { religion = religion:christianity_religion }
			animation = acknowledging_crozier
		}
		animation = personality_rational
		camera = camera_event_left
	}

	right_portrait = {
		trigger = { exists = scope:religious_superior }
		character = scope:religious_superior
		animation = worry
		camera = camera_event_right
	}

	# A — Stay: convert and keep this Clerical Region
	option = {
		name = pam_clergy_events.0051.a
		custom_tooltip = pam_clergy_events.0051.a.keep_see_tt

		# Fulfillment cost before convert (still on old Faith's fulfillment type)
		if = {
			limit = { has_spiritual_fulfillment_type = christian_fulfillment }
			if = {
				limit = { scope:old_faith.religion = scope:new_faith.religion }
				change_spiritual_fulfillment = major_spiritual_fulfillment_loss
			}
			else = {
				change_spiritual_fulfillment = massive_spiritual_fulfillment_loss
			}
		}

		# Devotion / piety / stress / convert modifiers — tooltips come from this effect
		convert_to_rite_with_consequences_effect = { RITE = scope:new_rite }

		# Liege of the capital's new Faith is glad you followed
		if = {
			limit = {
				liege ?= {
					faith = scope:new_faith
					this != root
				}
			}
			liege = {
				add_opinion = {
					target = root
					modifier = pious_opinion
					opinion = 30
				}
			}
		}
	}

	# B — Take nearest same-Faith Clerical Region
	option = {
		name = pam_clergy_events.0051.b
		trigger = { exists = scope:translation_see }
		custom_tooltip = pam_clergy_events.0051.b.tt

		create_title_and_vassal_change = {
			type = granted
			save_scope_as = pam_translation_change
			add_claim_on_loss = no
		}
		scope:translation_see = {
			change_title_holder = {
				holder = root
				change = scope:pam_translation_change
			}
		}
		resolve_title_and_vassal_change = scope:pam_translation_change

		destroy_title = scope:title
		tca_probe_strip_personal_landed_titles_effect = yes
	}

	# C — Accept game over (landless offer comes from normal systems if available)
	option = {
		name = pam_clergy_events.0051.c
		add_internal_flag = dangerous
		custom_tooltip = pam_clergy_events.0051.c.tt

		tca_probe_strip_personal_landed_titles_effect = yes
		destroy_title = scope:title
		hidden_effect = {
			if = {
				limit = { has_dlc_feature = roads_to_power }
				create_landless_adventurer_title_effect = {
					REASON = flag:wanderer
					FLAVOR_CHAR = root
				}
			}
		}
	}
}

pam_clergy_events.0052 = {
	id_override_priority = 1
	theme = christian
	type = character_event
	title = pam_clergy_events.0052.t
	desc = pam_clergy_events.0052.desc

	trigger = {
		# Only the temporary secular fixture bypasses religion mismatch handling.
		NOT = { scope:title = title:k_tca_clerical_probe }
		OR = {
			is_ai = yes
			scope:reason != flag:county_converted
		}
	}

	left_portrait = {
		character = root
		animation = acknowledging_crozier
		camera = camera_event_left
	}

	option = {
		name = pam_clergy_events.0052.a
		add_internal_flag = dangerous
		custom_tooltip = pam_clergy_events.0051.c.tt

		tca_probe_strip_personal_landed_titles_effect = yes
		if = {
			limit = { scope:reason != flag:character_converted }
			destroy_title = scope:title
		}
		hidden_effect = {
			if = {
				limit = { has_dlc_feature = roads_to_power }
				create_landless_adventurer_title_effect = {
					REASON = flag:wanderer
					FLAVOR_CHAR = root
				}
			}
		}
	}
}
```

### `localization/english/tca_clerical_probe_l_english.yml`

编码：UTF-8；BOM：有；字节数：169。

SHA-256：`0a31b881440c20614aa46f9acfd787e61af917f29a2610ebc56c545bc7aa1fb5`

```yaml
l_english:
 k_tca_clerical_probe:0 "Jiangxi Judicial Region (Test)"
 k_tca_clerical_probe_adj:0 "Jiangxi Judicial"
 tca_clerical_probe_holder_name:0 "Probe Official"
```

### `localization/simp_chinese/tca_clerical_probe_l_simp_chinese.yml`

编码：UTF-8；BOM：有；字节数：171。

SHA-256：`b7d193a91ef37c2cb74ac6d106a7162e39ba2b77aaaffcb4e8f0218d79c87452`

```yaml
l_simp_chinese:
 k_tca_clerical_probe:0 "江西提刑辖区（测试）"
 k_tca_clerical_probe_adj:0 "江西提刑"
 tca_clerical_probe_holder_name:0 "辖区测试官"
```

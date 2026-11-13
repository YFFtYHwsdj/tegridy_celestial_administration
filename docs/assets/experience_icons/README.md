# 官僚经验特质图标原图

本目录保存已选定的三张透明 PNG 原图，按原生 `traits` 分类，文件名与正式特质标识一致。规则、接线与验收边界由[官僚经验模块](../../experience/README.md)维护。

- 吏事历练：`traits/tca_clerical_experience.png`，簿册与墨笔。
- 兵事历练：`traits/tca_military_experience.png`，军鼓与令旗。
- 朝事历练：`traits/tca_central_experience.png`，笏板与奏牍。

三张图稿参照原版特质图标的粗糙青绿色底板、手绘器物及厚重阴影制作，底板外部保留透明；同一特质的三级名称共用一张图。牧守保持原版图标，不另存副本。

原图为 1254×1254 RGBA PNG，不从游戏 DDS 反向放大。输出时保持完整构图和留白，用 `sips` 等比缩至 120×120，再以 Pillow 编码为同名 RGBA DDS，放入 `gfx/interface/icons/traits/`。输出后重新读取，核对尺寸、透明度与缩放 PNG 的像素一致性，并目视检查小尺寸辨识度。

尺寸、像素和接线检查不代表已完成游戏内显示验收；仍需核对人物特质列表、悬浮提示及不同界面缩放下的显示。

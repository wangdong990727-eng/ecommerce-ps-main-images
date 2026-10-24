---
name: ecommerce-ps-main-images
description: 按本品实拍制作严格复刻详情、参考改版、新主图、局部返修与同版多色SKU；保护清晰母版，交付原生可编辑PSD、独立模特场景素材和精简交付报告。
metadata:
  version: "2026.10.24-r5.4"
---

# 电商主图、SKU与详情增量制作

沿用原有严格复刻能力，不把生成成功、文件可打开或技术检查通过当成商品通过或用户采用。

## 先确定本次意图

|意图|执行方式|
|---|---|
|严格复刻 strict_replica|按[原有严格流程](references/strict-workflow.md)保留参考顺序、模块、比例、文字断行、字级及视觉手法；仅改有依据的商品事实、品牌及必要受保护素材|
|参考改版 adapt|只在用户授权范围内改构图、文案或设计；读[策划](references/content-planning.md)|
|新主图设计 new_main_design|使用new_design基础模式，范围限定main；无参考时才自行策划，不套用别款视觉|
|局部返修 local_retouch|继承原项目模式与最新手改/采用版本；限定变化部位，读[母版保护与返修](references/master-retouch.md)|
|多色共用模板 shared_color_template|继承原版式，在一个PSD中按色建立完整原生图层组，每次只显示一组；读[多色PSD](references/shared-psd.md)|

先读已有参考、实拍、参数、用户反馈及现有PSD；能确定的资料不重复索要。内部预检、抄字、检查与返修不逐项请求人工批准；事实冲突、必要实拍缺失、新费用或改变用户范围才集中询问。意图与基础mode分开记录，兼容既有schema 5，不强行迁移旧工程。

## 按需读取与执行

1. 新电脑读[执行适配](references/executor-adapter.md)，重新探测PS、字体、工具和依赖。没有生图能力就按[生成闭环](references/generation-loop.md)标ASSET_REQUIRED，完成其他可做部分；不自动安装无关环境。
2. 实拍决定外形、颜色、材质、包边与连接；同行只提供构图/版式。读[商品核对](references/product-profiles.md)，按机位选择局部编辑、自然合成或AI穿戴；任何路线都不保证成功，均需看图核对。
3. 严格复刻先量取与锁版；新设计/授权改版先策划。主图落实主体比例、字级、间距、留白和装饰。浅底深字、轻斜体、细线只是可选手法，不推广到所有商品。
4. 用[项目记录](references/project-record.md)和[分项状态模板](templates/revision-record.example.json)分别记录人物、商品、佩戴比例、文案、排版、色款；用户采用继续以user_approval为唯一依据。人物/商品已过后，排字不得重新生成。
5. 功能图标另读[统一图标与语义](references/icon-system.md)：参考提取、SVG统一参数、AI候选和素材检索分开，功能与许可先核对；图标广告字仍留PS文字层。PS依照[原生执行](references/photoshop-workflow.md)与[布局格式](references/layout-schema.md)：中文原生文字，人物/商品嵌入智能对象；蒙版、背景、效果能分则分，未拆部分准确披露，不冒称全可编辑。
6. 整体、商品局部与约200px缩略图均要看；实际交付路径重开PSD，逐色切换导出，在测试副本中改字和换图。完整详情仍看整条顺序及接缝，不能以缩略图替代。读[验收](references/acceptance-delivery.md)。
7. 按[精简交付与素材复用](references/delivery-handoff.md)交上架图、PSD、独立模特/场景素材、许可允许的字体和一份报告。制作过程、对比记录、上架清单和单独使用说明不放商品交付包；核对完成后按范围清理任务临时过程文件。

新增工具仅处理重复易错动作：asset_workflow.py用于快照/保护区像素差异/缩略图；psd_variants.py编译原生多色合并和按图层ID逐色导出任务。脚本不判断人物、商品、风格或用户采用。命令及边界见各引用页。

## 版本与边界

旧合格资产、用户手改文件、原图及清晰母版受保护；不从旧稿覆盖新稿。参数、颜色及具体排版只写入本项目，示例见[耳罩项目](examples/earmuff-project.md)。

技能更新不等于授权发布商品、投放、改价或新增付费服务。Git仓库只管理通用技能、脚本、测试与匿名化示例，不放商品工程、用户素材、账号或密钥；按[Git升级与回滚](references/git-versioning.md)使用明确版本。

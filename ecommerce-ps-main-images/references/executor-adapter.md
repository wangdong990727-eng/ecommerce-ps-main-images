# Codex、WorkBuddy、DeepSeek Harness 共用执行

业务规则与数据格式共用；不要复制三套提示词分支。宿主名称不证明有图片编辑或PS自动化能力。已装Photoshop与能由当前助手执行Photoshop也是两件事。

## 能力预检

`project_tools.py preflight --out <路径>`只读探测本机Python/Pillow、桌面和PS候选。它不代表PS已运行，也不能检测会话中的生图工具。助手还需分别记录：

|能力|如何验证|缺失时仍可做什么|
|---|---|---|
|读取/看本地图|实际打开指定原图和局部|能读目录但不能看图时只列清单，不假称视觉核验|
|PS执行|运行本包smoke_test并读取COMPLETE/ERROR，重开输出|编译JSX、整理待运行工程；用户可在PS脚本菜单执行|
|字体|查询app.fonts，实际文案试排|使用许可明确的近似字体并记录差异|
|图片生成/编辑|发现当前实际工具，核对参考图/编辑能力、额度和回传文件|已有实拍制作；缺图按generation-loop输出任务包|
|报告/打包|打开离线HTML，检查相对路径与复制哈希|继续保存项目工程与缺项清单|

只使用已授权工具和账号，不猜API地址、模型标识、密钥或费用。没有生图就不伪造调用；另一个助手的内置生图工具不一定在这里存在。通用包不内置云服务、登录态或凭据。

Python标准库用于项目记录/报告/布局编译，长图拼接需Pillow，Windows COM自动化只在实际有pywin32等能力时使用；缺依赖先明确哪一步需要，不自动批量安装环境。Windows使用已验证的解释器完整路径，避免包装器指到失效环境。PS JSX按UTF-8 BOM保存；PowerShell含中文脚本用UTF-8 BOM或从UTF-8数据文件读取，不使用bash heredoc。

## 安装和避免旧版覆盖

本包的 `ecommerce-ps-main-images/` 是技能根，里面必须直接有SKILL.md及其references/scripts/templates。不能只复制SKILL.md；不能多嵌套一层同名目录。安装前备份目标旧版到技能搜索路径之外；不要在可发现目录留两个同name版本。仅修改用户本次授权的技能，不覆盖宿主全局设置或其他技能。

- Codex：使用当前实际技能根目录（以会话技能目录或CODEX_HOME配置为准），开启新聊天后核对读到版本 `2026.10.17-r5.3`。`agents/openai.yaml`只是Codex界面元数据，其他宿主无需依赖它。
- WorkBuddy：官方说明支持“添加技能→上传技能”导入本地技能包；可导入本包纯技能ZIP。项目级使用时官方项目说明列出 `.codebuddy/skills/`。若目标版本UI不同，先检查本机入口，不能假装已安装。来源：[技能](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)、[项目](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project)。
- DeepSeek Harness：官方源码文档列出项目 `.dsh/skills/`、`.agents/skills/`及用户/自定义技能源；推荐本次测试放项目 `.dsh/skills/ecommerce-ps-main-images/`，确认宿主已启用本地技能与skill加载能力。项目源优先于用户源，要查同名旧技能。来源：[官方技能子系统](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md)。

这些入口文档于2026-10-13核对；格式/目录适配不是目标电脑已实测。目标端先读当前SKILL.md版本，再跑PS小样。若不能自动发现，可直接要求助手读取解压后的SKILL.md及相对引用并按其执行；这能读取规则，不代表已安装到技能目录。

## 接力与恢复

移动整个项目工程：project-state、布局、素材、生成任务包、PS/导出、检查证据一起带走。知识库同步或技能ZIP不会自动携带商品PSD/照片。项目数据用相对路径；新机器重新探测PS/字体/桌面，不沿用上一台盘符。

启动续接先读 `next_action`、issues、现有文件与各页版本；核对文件实际存在和生成状态，不依据旧助手一句“已完成”。保留通过素材，只执行未完成或受反馈影响的阶段。同一PS只有一个写入任务。

最终明确区分：技能可读取、脚本校验通过、本机PS运行通过、某商品视觉验收通过、另一宿主整套实测通过。没有对应证据就写未测，不因JSON有效或说明可读声称“所有软件稳定复刻”。

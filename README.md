# 电商主图与详情复刻技能 R5.4

技能名：`ecommerce-ps-main-images`。关键词：复刻详情、电商主图、SKU、同版多色、局部返修、可编辑PSD。

本仓库只管理通用技能、脚本、测试和匿名化示例。商品原图、模特照片、PSD工程、店铺资料、凭据不入库。私有仓库需给目标电脑对应GitHub账号/连接器访问权，不能在GitHub公共搜索中找到，也不表示已进入公共技能市场。

## 直接发给另一台电脑AI

> 请从 https://github.com/wangdong990727-eng/ecommerce-ps-main-images 安装技能 ecommerce-ps-main-images，仓库内路径 ecommerce-ps-main-images，版本ref使用r5.4。先确认你的GitHub账号/连接器能访问这个私有仓库，读取该ref下的SKILL.md并核对2026.10.24-r5.4；检测实际技能根目录，备份搜索路径内旧同名技能，再只安装本技能，不覆盖其他技能或商品文件。安装后验证文件、Python/PS/字体/工具能力，不自动安装无关环境；实际PS与商品测试未做就标未测。下一轮用 $ecommerce-ps-main-images 调用。缺访问权请明确提示，不索要明文密码或Token。

Codex若具备skill-installer，使用其安装脚本，参数为：

```text
--repo wangdong990727-eng/ecommerce-ps-main-images --path ecommerce-ps-main-images --ref r5.4
```

该安装器不覆盖已有同名目录；由目标助手先备份旧版。其他AI不一定有此安装器，可使用其已授权的Git/仓库连接器读取同一ref并完整复制技能目录，不能只复制SKILL.md。使用用户当前真实技能根目录，不沿用源电脑盘符。

## 本地安装、检查

取得完整仓库/ZIP后，可使用本包transfer_tools.py。`verify`校验发布清单；`install --skills-root ...`仅演练，增加`--apply`才安装，旧不同版本需显式`--replace`才移出搜索路径备份。联接/符号链接目标不自动替换，先核查。

```text
python transfer_tools.py verify
python transfer_tools.py install --skills-root "目标机实际skills根目录"
python transfer_tools.py install --skills-root "目标机实际skills根目录" --apply
python transfer_tools.py selftest --output "目标机新测试输出目录"
python -m unittest discover -s tests -v
```

Python建议3.10以上；标准库可完成项目记录和编译，保护区检查、缩略图及测试另需Pillow。PS自动执行可选pywin32，手动运行JSX不需要；生图、PS、字体和账号由目标机实际检测，不内置模型或额度，不批量安装依赖。

可选真实PS技术回归（会启动/连接PS，仅使用本次新建合成测试文件，不用商品素材）：
`python tests/ps_regression.py --output "新PS测试目录"`。不要把无PS的selftest当PS实跑或真实商品通过。

## 工作与交付

保留严格复刻；另外明确参考改版、新主图、局部返修、多色共用模板。多色组在同一PSD图层面板上下排列，每次仅一组可见。中文原生文字，人物/商品嵌入智能对象，模特场景素材独立交出；合成未拆区域准确说明。

商品只交：上架图片、做图源文件、模特与场景素材、许可允许再分发的字体、一份完整交付报告。不交过程对比、上架清单或单独使用说明；内部检查后仅清理本次自建临时过程，不删除原图、用户手改、清晰母版、采用素材或历史项目。

图标按参考提取/统一SVG/AI候选/素材检索分路线，功能必须有事实依据；SVG不自动保证版权，示例不证明商品有防水、机洗等性能。具体见技能references/icon-system.md。

## 升级与回滚

以远端明确版本ref或提交为准：r5.4为本次更新，r5.3保存此前已安装基线。升级前备份本机旧版和手改，安装指定新ref；回滚时安装r5.3或恢复备份，商品工程不跟着回退。安装后下一轮读出版本再测试。发布后不移动已有版本ref，修正另发新版本。

修改清单见CHANGELOG.md，验证与限制见VALIDATION.md。仓库私有使用；公开许可和公开可见性由所有者另行确定。

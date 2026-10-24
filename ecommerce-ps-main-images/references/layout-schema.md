# 可执行布局 JSON（1.0）

此格式将**已量取的版式**编译为 Photoshop JSX，不能识别参考、自动抠图、自动生成模特或保证视觉一致。每个文件代表一张图或一个完整连续画布；内容从本次参考填写，示例不是默认设计。项目记录 schema 5 与布局 schema 1.0 是不同格式。

## 执行

```text
python scripts/render_layout.py templates/layout-spec.example.json --out demo-skeleton.jsx --skeleton --output-dir demo-skeleton
python scripts/render_layout.py templates/layout-spec.example.json --out demo-full.jsx --output-dir demo-full
```

在技能根运行，python替换为可用解释器。编译得到的JSX已嵌入函数库；在Photoshop执行。`.status.json` 的 complete 表示保存、重开和原生图层计数检查通过；`.layers.json`保存实际文字、字体、边界、智能对象和蒙版信息，`visual_review`仍为not_run。运行后必须实际打开JPG看图。每轮用新job_id或输出目录，禁止覆盖现有成品。

Windows已具备pywin32时执行示例：`python scripts/run_photoshop.py demo-full.jsx --status demo-full/REFERENCE_PAGE_01_V01.status.json`。缺少该可选能力时不自动安装，使用现有PS控制或脚本菜单运行同一个JSX。

`--skeleton`用占位色框替代image，可在图片未生成时检查文字和框；它不证明实际人物轮廓、裁切、去背或透视合格。

## 顶层

- `schema_version`: 字符串 `"1.0"`。
- `job_id`: 字母开头的英文字母/数字/下划线/连字符，最长80字符，作为输出文件名。
- `canvas`: `{width,height,resolution:72,background:"#FFFFFF"}`，像素正整数，单边最大30000。更大原生长版须用另经验证的PSB流程，不强迫压缩参考。
- `reference`（可选）: `{path,size:[w,h]}`，用于追溯，文件应真实存在，不会自动渲染进输出。
- `layers`: 从底到顶的对象数组，ID唯一。显式保存所有坐标，不能从上一页猜新一页。

所有颜色为 `#RRGGBB`，位置/尺寸/字号/行距为像素；透明度0–100。素材路径相对**布局JSON所在目录**，不相对项目根；布局移机后需要保留相对结构。编译会解析为本机路径，跨机应重新编译JSX。

## 支持的对象

|type|必须字段|可选字段|
|---|---|---|
|`text`|id,text,font,size,color；position或box二选一|align,leading,tracking,rotation,opacity,stroke,shadow,name|
|`image`|id,source,box,fit|mask_box,rotation,opacity,stroke,shadow,name|
|`rect`|id,box,color|rotation,opacity,stroke,shadow,name|

`box=[x,y,width,height]`。文本 `position=[x,baselineY]` 用于点文字，位置是文字基线；文本box用于段落文字，位置是框起点，可能自动换行，必须查看成图排除溢出。text保留原换行 `\n`；font为PS实际PostScript名，缺失时报错不偷换字体。align为left/center/right，tracking为Photoshop字距单位（千分之一em），leading为像素；不提供leading时使用自动行距，严格复刻通常应填写测量值。

`rotation`为绕对象中心的角度。文字旋转与字体本身斜体不同，需分别选font和rotation。`fit=contain`等比完整放入框，`cover`等比填满后裁切。所有image都有轴对齐矩形图层蒙版，默认框为box；mask_box可单独指定裁切边界。旋转图片内容后蒙版保持轴对齐；倾斜照片边框、人物出框或不规则轮廓需要另建相应PS蒙版/组件，不能用该矩形蒙版代替。

`stroke={color,size,position}`，position为outside/inside/center；`shadow={color,opacity,angle,distance,blur,spread?}`，原生图层效果可编辑。阴影需实看，不能仅根据字段存在声称效果相同。

## 特殊技巧怎么处理

编译器对未支持的type/字段明确报错；不得删掉参考技巧使它“能运行”。圆角、曲线、手绘图标、双描边、复杂蒙版、反射、文字变形等在PS原生对象或经验证的独立组件中完成，并保存到页的PSD及检查记录。可把组件作为嵌入对象复用，但文字正文仍须原生可改。

出现新技巧时，先做最小可检查组件，验证再批量使用。需要的PS动作可以在本次项目JSX中补充；不要每页临时换一种视觉近似。当前编译器只是共用基础执行层，不是全部参考效果的自动还原器。

可执行的项目组件入口：`render_layout.py ... --components components.jsxinc`。文件由本次任务编写/审核，定义 `EC_afterLayout(document,spec)`，在排版后、保存前调用；编译时嵌入JSX，不依赖跨机绝对路径或运行时include。用于圆角、原创图标等项目技巧。组件只操作传入的任务文档，正文文字仍列在layout中；不要使用未知第三方组件或绕过商品检查。移机时重新编译同一layout并带上同一components文件。

R5.2的layers证据在build_sources记录布局、组件、编译器和函数库SHA-256；用于追溯实际编译输入，不证明组件视觉正确。文字证据另记录横纵缩放、伪粗体与伪斜体，检查是否发生未记录的变形；默认文字从100%横纵缩放开始，不继承PS字符面板的压缩设置。

## 源文件与证据

输出目录有PSD/JPG配对、status及layers JSON。逐层证据读图层ID，不通过激活图层遍历。创建的文档保存后关闭，用户已有文档及偏好保留；失败只清理任务自建临时文档，保留已经写出的文件便于定位。错误后先读stage和message，不盲目重跑整个批次。

套版先另存，原生改字和智能对象替换后检查字体、框、蒙版、颜色和对应JPG；替换内容不会自动证明新产品轮廓适配旧蒙版。

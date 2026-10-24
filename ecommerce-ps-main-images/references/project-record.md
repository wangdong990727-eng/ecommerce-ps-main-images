# 项目记录与离线对照（schema 5）

每个任务在项目根保存 `project-state.json`。所有材料/证据路径相对该根目录，不用机器盘符、URL、`..` 或逃出根目录的目录联接。同行参考、产品事实、结果图片是不同角色。脚本不会生成图片、重写验收状态或凭文件存在认定产品画对。

## 命令

从技能根目录运行，`python` 可替换为本机已经存在的 Python 可执行文件：

```text
python scripts/project_tools.py preflight --out "项目目录/environment.json"
python scripts/project_tools.py init "项目目录"
python scripts/project_tools.py check "项目目录" --stage plan --json-out "项目目录/evidence/plan-check.json"
python scripts/project_tools.py check "项目目录" --stage review --json-out "项目目录/evidence/review-check.json"
python scripts/project_tools.py report "项目目录" --out "项目目录/review.html"
python scripts/project_tools.py check "项目目录" --stage delivery --json-out "项目目录/evidence/delivery-check.json"
```

`init` 不覆盖已有记录，新建的空模板刻意不能通过检查。`check` 通过返回 0，未通过返回 1，命令/文件错误返回 2。审阅阶段检查失败仍应生成报告供用户检查，不能因此藏起问题或拒绝提交待审稿。`report` 返回 0 只表示报告已生成，输出另有 `review_check_passed`，不等于自检通过。

`preflight` 只读取 OS/Python/Pillow、桌面路径、常见 Photoshop 安装目录和Windows App Paths注册信息；输出报告是唯一写入。不会启动软件、安装依赖、访问网络、探测密钥/账号。候选路径不等于 Photoshop 已验证可用；未注册的自定义路径需另行发现。生图能力固定为 `not_tested`，必须在执行环境另做可观察的小样。

Python 标准库即可运行；Pillow 可选。无 Pillow 时会明确提示，仍可读取常见 PNG/JPEG/GIF/BMP/PSD 尺寸，特殊格式无法检查时不猜测。不因为缺少 Pillow 自动安装依赖。

## 顶层字段

| 字段 | 规则 |
|---|---|
| `schema_version` | 固定 `5` |
| `mode` | `strict_replica` / `adapt` / `new_design` |
| `product_profile` | `{type:"earmuff"或"glove"或"other", fact_sources:[本品实拍/确认参数等相对文件], notes:[]}`；至少一份事实来源 |
| `status` | `planning` / `in_progress` / `pending_review` / `approved` / `manual_handoff` / `delivered` / `blocked` |
| `scope` | `{kinds:["main","sku","detail"中本次实际范围], expected_page_ids:[本次全部页面ID]}`；非空且与 pages 完全一致 |
| `references` | `[{id,kind,path}]`，ID 唯一，kind 为 main/sku/detail，文件必须存在；每个参考至少被一页使用，可一张长图映射多页或一页映射多张参考 |
| `pages` | 非空，逐页按下一节填写；页面 ID 唯一 |
| `assets` | 轻量数组，例如 `[{id,role:"product_original",path,source,note}]`；不要把生成图标成实拍 |
| `generation_jobs` | 轻量数组，例如 `[{id,page_ids,attempt,prompt_path,inputs,output,status,defects,decision}]`；保留失败尝试，标明是否计费已获授权；本脚本不执行生成 |
| `next_action` | 明确下一步；即使完成，也写归档/人工后续状态 |
| `issues` | 未解决的项目问题数组，无则 `[]`；正式交付前清空，并把解决过程保存为证据 |

`assets` / `generation_jobs` 为跨软件接力记录。新素材按[回归验收](regression-acceptance.md)记录ASSET_REQUIRED/READY/REJECTED、实际检查结果、来源、证据与哈希，page.asset_ids关联依赖；旧无状态记录仅保留历史兼容，不能视为新图通过。`references`必须是本次完整参考集，不能为通过检查偷偷删掉未完成参考。范围减少先保存用户改变范围的证据。

## 单页示例

路径仅为格式示例，必须替换成真实文件；不要复制示例后宣称已核验。

```json
{
  "id": "detail-01",
  "kind": "detail",
  "reference_ids": ["peer-detail-01"],
  "layout": "layouts/detail-01.json",
  "preview": "",
  "psd": "",
  "copy": [
    {
      "id": "title-01",
      "reference_text": "同行逐字原文\n包括原换行",
      "final_text": "同行逐字原文\n包括原换行",
      "change_reason": "",
      "fact_sources": []
    }
  ],
  "checks": {
    "layout": {"status": "not_run", "evidence": [], "issues": []},
    "product": {"status": "not_run", "evidence": [], "issues": []},
    "copy": {"status": "not_run", "evidence": [], "issues": []},
    "technical": {"status": "not_run", "evidence": [], "issues": []}
  },
  "user_approval": {"status": "pending", "version": "", "evidence": []},
  "version": "R1"
}
```

- `layout` 指向实际存在的单页版式 JSON。使用本包schema 1.0时，脚本还会对照原生text对象的ID/文字与copy账本，防止账本和实际排版脱节；完整字段校验仍由render_layout负责。其他组件需要实际PS检查。
- `preview` / `psd` 在 plan 阶段可空；填了路径就必须存在，避免陈旧路径混进记录。review 必须有可读取宽高的预览；delivery 必须有相同画布尺寸、PSD/PSB 文件头可识别的配对源文件。文件头检查不能代替 Photoshop 重新打开、图层与导出核验。
- `copy` 逐条包括文案与换行，无文字页才可 `[]`。逐字不变保留空 `change_reason`。改变一字也要写原因；strict_replica 的改动另需非空 `fact_sources` 文件作为必要事实依据。脚本不替你判断改动理由是否成立。
- `checks` 四项不能缺。status 用 `not_run/pass/fail/blocked`；每项 pass 必须有非空、存在的证据文件且无未解决 issues。fail/blocked 必须写问题。证据应写明**页 ID、当前版本、检查点、观察结果**，附截图/对照图；不能把同一份空泛“已检查”文本复制给所有检查。版式看并排叠加，产品看实拍逐点，文案看 OCR/原生文字，技术看 PSD 重新打开与原生图层。
- `user_approval` 只能由真实用户针对当前版本的明确反馈更新；保存原话/截图/聊天节选为证据。`approved` 还要求四项自检通过；`manual_handoff` 只表示用户接手修改，不能通过正式 delivery。生成报告不写审批。
- 结果变更后递增 `version`，受影响检查重置 not_run，`user_approval` 重置 pending。旧批准版本与新版本不符会报错；证据文件内容真实性仍需执行者检查。

## 三道记录检查

1. **plan**：非空范围和页集、全部参考覆盖、产品事实材料、版式文件、逐字文案差异原因、四项检查槽位均齐全。不要求已生图。记录为 pass/approved 的项即使在此阶段也不能缺证据。
2. **review**：上述检查，加每页结果存在、四项检查均 pass 且有证据。未通过的稿仍可提交报告，但须称“待审/待修”，不能声称自检通过。
3. **delivery**：上述检查，加 PSD/PSB 配对、导出尺寸一致、当前版本明确 approved、审批证据存在、无项目遗留问题。manual_handoff 可打人工修补包，不能标正式可上架。

new_design 的页可无 reference_ids；strict_replica/adapt 不可。脚本允许同一长参考映射多个结果页，不用数量相等冒充内容覆盖：参考内每段是否都做到了，仍要完整拼接和逐页视觉核验。

references中的详情参考按已核对的阅读次序排列；严格复刻会检查pages中的详情映射不能倒序。切片重组允许同一参考重复映射，仍不能先把后面的主题合并进前面再跳回去。若本次还有没有对应参考的新设计产物，在用户授权后单独用new_design项目记录，不用假参考填空。

## 离线报告

`report` 输出一个 HTML 和同名 `.assets` 目录，复制用于显示的参考/结果图片及证据，并保存项目记录快照。一起拷贝即可在另一台机器双击，不依赖网络服务或 fetch。PSD 源文件仍随完整项目文件夹交付，报告不重复复制大 PSD。

每页展示参考和结果并排、文案差异、四项证据、审批状态；叠加滑块调整结果透明度。两图按同宽等比缩放且顶部对齐，宽高比不同会明示，绝不把结果强行拉伸成参考。多参考逐个对照，不把九宫格代替完整页面验收。

HTML 文本和属性转义；材料 URL 仅来自项目内复制文件。脚本不执行项目 JSON 中的命令。每次改稿重新生成报告，避免审阅旧快照。


## R5.4增量

R5.4兼容补充：顶层workflow.operation可为strict_replica/adapt/new_main_design/local_retouch/shared_color_template；原mode仍仅三种并按入口表映射。模板task-plan.json新增workflow。page.review_axes记录person/product/wear_scale/copy/layout/color六维及版本证据；第七维用户采用只用既有user_approval，不复制第二份批准。新增模板revision-record.example.json用于格式示例，不自动批准。旧project_tools.py仍只检查既有四项checks；新增六维与母版/保护区/色组需实际核查，旧脚本PASS不证明新维度通过。制作期间保留必要检查，商品交付目录与完成后过程清理以delivery-handoff.md为准。

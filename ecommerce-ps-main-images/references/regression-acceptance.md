# 商品回归与恢复（R5增量）

不重复测试哈希未变且已有可靠证据的代码。至少选一张真实手套详情、一组真实后戴式耳罩素材与对应SKU页，以及一次缺生图暂停/回填恢复。生成或保存失败只修对应对象，保留通过的文件。

回归结果使用 `PASS/PARTIAL/FAIL`，素材流程另用 `ASSET_REQUIRED/READY/REJECTED`，用户批准另记pending/approved，三者不可混为一谈。

## 每个回归必须留下

`regression-results.json`中的每项：`id,result,executed,input_files,output_files,checks,failures`。checks分别检查参考映射、布局/文字、商品、图片边缘/背景、原生编辑、PSD/JPG/数据重开、重复执行保护、恢复。每个检查为PASS/PARTIAL/FAIL及证据路径；未做或缺输入记PARTIAL并说明。

每个failure含 `file,reason,minimal_fix`。关键商品结构错记FAIL；已有部分真实输出但穿戴素材缺失等未完成项使整体为PARTIAL。全部实际检查通过才是PASS。PASS是本次样例通过，不代表所有款式、全套或用户视觉验收。

手套锁定指型/拇指、掌背、拼色、缝线、本品标志及腕口；细节以原始实拍和可追溯抠图核对。后戴式耳罩锁定后脑连接路径、耳包轮廓/尺度、毛绒、贴耳位置；头顶头箍图片不能回填，不用同行佩戴图证明本品。图片去背要保持原像素，蒙版修边而非重画商品。

## 缺图任务与恢复

新任务的共享素材用下面格式；page的 `asset_ids` 指向素材ID，三个产物可以共享同一份合格图片。

```json
{
  "id": "rear-wear-01",
  "path": "assets/rear-wear-01.png",
  "state": "ASSET_REQUIRED",
  "review_result": "PARTIAL",
  "source_paths": ["product/rear-earmuff.jpg"],
  "reason": "当前没有本品正确后戴的合格穿戴图，生图工具不可用",
  "evidence": [],
  "sha256": "",
  "request": {
    "prompt_path": "generation/rear-wear-01/prompt.txt",
    "reference_paths": ["product/rear-earmuff.jpg", "references/page-01.jpg"],
    "save_path": "assets/rear-wear-01.png"
  }
}
```

先保存独立提示词、参考职责和回填位置；项目保留版式和通过页，不将占位版记通过。回来的素材先逐图看真实商品/穿戴/边缘，保存具体检查证据，再运行：

```text
python scripts/project_tools.py asset-return 项目 rear-wear-01 --evidence evidence/rear-wear-01-review.md --review PASS
```

此命令不自动判断图片真假；PASS必须来自实际看图。它校验文件存在、来源和证据，记录哈希及状态快照，只撤销依赖页面的相关检查/批准，给下一动作；**不自动重写PSD/JPG**。相同素材、哈希和证据重复回填为no-op。回填后按原锁版替换素材、重验对应页；其他通过页不重做。

`check --stage review/delivery`会拒绝依赖ASSET_REQUIRED/REJECTED的页面，以及核验后被修改的素材。失败候选用FAIL回填为REJECTED，部分可用候选记PARTIAL，不放进正式包。

本次回归记录随交付包提供；下一台电脑重新检查工具/字体及可写路径，用相对工程和原事实素材恢复，不沿用本机盘符。

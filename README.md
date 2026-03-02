# HTML 图片分辨率统计

从大量 HTML 中解析 `<img>` 的宽高（优先 `data-file-width`/`data-file-height`，否则 `width`/`height`），统计分辨率分布。

## 用法

```bash
pip install -r requirements.txt
```

**小批量验证（建议先跑 10 个文件确认结果）：**
```bash
python stats_resolution.py --html-dir html --limit 10
```

**全量统计（5000 个文件）：**
```bash
python stats_resolution.py --html-dir html
```

若 HTML 在 `data` 目录：`--html-dir data`。  
`--top N` 控制打印前 N 个分辨率，默认 50。

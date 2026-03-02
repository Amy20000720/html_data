# -*- coding: utf-8 -*-
"""
从 HTML 文件中统计 img 标签中的图片分辨率分布。
分辨率优先取 data-file-width/height（原始），否则取 width/height。
"""
import argparse
import re
from pathlib import Path
from collections import Counter

from bs4 import BeautifulSoup
from tqdm import tqdm


def _parse_dim(val) -> int | None:
    if val is None:
        return None
    s = str(val).strip()
    m = re.match(r"^(\d+)", s)
    return int(m.group(1)) if m else None


def parse_img_resolutions(html_path: Path) -> list[tuple[int, int]]:
    """解析单个 HTML 中所有 img 的分辨率，返回 [(w,h), ...]。"""
    try:
        text = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    soup = BeautifulSoup(text, "html.parser")
    result = []
    for img in soup.find_all("img"):
        w, h = _get_resolution(img)
        if w and h and w > 0 and h > 0:
            result.append((int(w), int(h)))
    return result


def _get_resolution(img) -> tuple[int | None, int | None]:
    """优先 data-file-width/height，否则 width/height。"""
    w = _parse_dim(img.get("data-file-width")) or _parse_dim(img.get("width"))
    h = _parse_dim(img.get("data-file-height")) or _parse_dim(img.get("height"))
    return (w, h)


def collect_html_files(html_dir: Path) -> list[Path]:
    """递归收集 html_dir 下所有 .html 文件。"""
    return sorted(html_dir.rglob("*.html"))


def run_stats(html_dir: Path, limit: int | None, progress: bool = True) -> Counter:
    """统计目录下 HTML 中图片分辨率分布。limit 为 None 表示不限制。"""
    files = collect_html_files(html_dir)
    if limit is not None:
        files = files[:limit]
    if not files:
        return Counter()
    counter: Counter = Counter()
    iterator = tqdm(files, desc="HTML", unit="file", disable=not progress)
    for fp in iterator:
        for w, h in parse_img_resolutions(fp):
            counter[(w, h)] += 1
    return counter


def print_distribution(counter: Counter, top_n: int = 50):
    """打印分辨率分布（按出现次数降序，前 top_n）。"""
    if not counter:
        print("No resolution data.")
        return
    total = sum(counter.values())
    print(f"\nTotal image refs: {total}  |  Distinct resolutions: {len(counter)}\nTop {top_n}:")
    print("-" * 50)
    for (w, h), cnt in counter.most_common(top_n):
        pct = 100.0 * cnt / total
        print(f"  {w} x {h}  ->  {cnt}  ({pct:.2f}%)")


def write_report_md(counter: Counter, report_path: Path, top_table: int = 50, top_chart: int = 20):
    """生成 MD 报告：表格 + Mermaid 图。"""
    if not counter:
        report_path.write_text("# Resolution Report\n\nNo data.\n", encoding="utf-8")
        return
    total = sum(counter.values())
    rows = counter.most_common(top_table)
    lines = [
        "# HTML 图片分辨率统计报告",
        "",
        f"- **总图片引用数**: {total}",
        f"- **不同分辨率数**: {len(counter)}",
        "",
        "## 分辨率分布表",
        "",
        "| 分辨率 (宽×高) | 出现次数 | 占比 |",
        "|----------------|----------|------|",
    ]
    for (w, h), cnt in rows:
        pct = 100.0 * cnt / total
        lines.append(f"| {w} × {h} | {cnt} | {pct:.2f}% |")
    lines.extend(["", "## 分布图（前 {} 项）".format(top_chart), ""])

    # Mermaid 柱状图（取前 top_chart 项）
    chart_items = counter.most_common(top_chart)
    labels = [f"{w}×{h}" for (w, h), _ in chart_items]
    values = [c for _, c in chart_items]
    # Mermaid 对标签中特殊字符敏感，用引号包起来
    labels_escaped = [f'"{s}"' for s in labels]
    lines.append("```mermaid")
    lines.append("xychart-beta")
    lines.append('    title "Resolution distribution (top {})"'.format(top_chart))
    lines.append("    x-axis " + ", ".join(labels_escaped))
    lines.append('    y-axis "Count" 0 --> ' + str(max(values) + 1))
    lines.append("    bar " + str(values))
    lines.append("```")
    lines.append("")

    # Mermaid 饼图（前 10 项，其余归为 Other）
    pie_n = min(10, len(chart_items))
    pie_items = chart_items[:pie_n]
    other_cnt = total - sum(c for _, c in pie_items)
    lines.append("## 占比饼图（前 {} 项）".format(pie_n))
    lines.append("")
    lines.append("```mermaid")
    lines.append("pie title Resolution share (top {})".format(pie_n))
    for (w, h), cnt in pie_items:
        pct = 100.0 * cnt / total
        lines.append('    "{}" : {}'.format(f"{w}×{h}", cnt))
    if other_cnt > 0:
        lines.append('    "Other" : {}'.format(other_cnt))
    lines.append("```")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="统计 HTML 内图片分辨率分布")
    p.add_argument("--html-dir", type=Path, default=Path("html"),
                   help="HTML 所在目录，默认 html")
    p.add_argument("--limit", type=int, default=None,
                   help="仅处理前 N 个文件，用于小批量验证（如 10）")
    p.add_argument("--top", type=int, default=50, help="打印前 N 个分辨率，默认 50")
    p.add_argument("--no-progress", action="store_true", help="不显示进度条")
    p.add_argument("--report", type=Path, default=None, metavar="FILE.md",
                   help="输出 MD 报告（含表格与 Mermaid 图）")
    args = p.parse_args()
    if not args.html_dir.is_dir():
        print(f"Dir not found: {args.html_dir}")
        return 1
    counter = run_stats(args.html_dir, limit=args.limit, progress=not args.no_progress)
    print_distribution(counter, top_n=args.top)
    if args.report is not None:
        write_report_md(counter, args.report, top_table=args.top, top_chart=min(20, args.top))
        print("Report written: {}".format(args.report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

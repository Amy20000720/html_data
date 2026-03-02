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


def main():
    p = argparse.ArgumentParser(description="统计 HTML 内图片分辨率分布")
    p.add_argument("--html-dir", type=Path, default=Path("html"),
                   help="HTML 所在目录，默认 html")
    p.add_argument("--limit", type=int, default=None,
                   help="仅处理前 N 个文件，用于小批量验证（如 10）")
    p.add_argument("--top", type=int, default=50, help="打印前 N 个分辨率，默认 50")
    p.add_argument("--no-progress", action="store_true", help="不显示进度条")
    args = p.parse_args()
    if not args.html_dir.is_dir():
        print(f"Dir not found: {args.html_dir}")
        return 1
    counter = run_stats(args.html_dir, limit=args.limit, progress=not args.no_progress)
    print_distribution(counter, top_n=args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

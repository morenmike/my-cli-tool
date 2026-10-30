"""filestats — inspect a directory: group files by extension, sum sizes,
and list the largest files. Pure Python standard library, cross-platform.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

NO_EXTENSION = "[no ext]"


@dataclass
class ExtensionStat:
    count: int = 0
    bytes_total: int = 0


@dataclass
class ScanResult:
    extensions: Dict[str, ExtensionStat] = field(default_factory=dict)
    files: List[dict] = field(default_factory=list)
    total_files: int = 0
    total_bytes: int = 0
    scanned_dirs: int = 0


def human_size(num_bytes: float) -> str:
    """Convert a byte count into a readable string, e.g. 2048 -> '2.0 KB'."""
    if num_bytes < 0:
        raise ValueError("byte count cannot be negative")
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} {units[-1]}"


def _extension(path: Path) -> str:
    suffix = path.suffix.lower()
    if not suffix:
        return NO_EXTENSION
    # Strip the leading dot, e.g. ".py" -> "py"
    return suffix[1:]


def _is_hidden(path: Path, root: Path) -> bool:
    """Treat any path component starting with a dot as hidden (Unix-style).
    On Windows a leading-dot name is still honored as a convention."""
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts
    return any(part.startswith(".") for part in rel_parts)


def scan_directory(
    root: Path,
    recursive: bool = True,
    max_depth: Optional[int] = None,
    skip_hidden: bool = False,
) -> ScanResult:
    """Walk *root* and collect per-extension statistics.

    Symlinks to directories are NOT followed to avoid cycles.
    """
    result = ScanResult()
    root = root.expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    # depth 0 == root itself
    def walk(current: Path, depth: int) -> None:
        result.scanned_dirs += 1
        try:
            entries = list(current.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if skip_hidden and _is_hidden(entry, root):
                continue
            if entry.is_symlink():
                # Skip symlinks entirely: do not follow dir links, do not
                # count file links as separate files.
                continue
            if entry.is_dir():
                if recursive and (max_depth is None or depth < max_depth):
                    walk(entry, depth + 1)
                continue
            if not entry.is_file():
                continue
            try:
                size = entry.stat().st_size
            except OSError:
                continue

            ext = _extension(entry)
            stat = result.extensions.setdefault(ext, ExtensionStat())
            stat.count += 1
            stat.bytes_total += size

            result.files.append(
                {"path": str(entry), "bytes": size, "extension": ext}
            )
            result.total_files += 1
            result.total_bytes += size

    walk(root, 0)
    return result


def _format_table(result: ScanResult, sort_by: str, top: int, root: Path) -> str:
    rows: List[tuple] = list(result.extensions.items())
    if sort_by == "count":
        rows.sort(key=lambda item: item[1].count, reverse=True)
    else:
        rows.sort(key=lambda item: item[1].bytes_total, reverse=True)

    lines: List[str] = []
    lines.append(f"Directory: {root}")
    lines.append(f"Total files: {result.total_files}  |  Total size: {human_size(result.total_bytes)}")
    lines.append("")
    header = f"{'Extension':<16}{'Count':>10}{'Size':>14}"
    lines.append(header)
    lines.append("-" * len(header))
    for ext, stat in rows[:top]:
        lines.append(f"{ext:<16}{stat.count:>10}{human_size(stat.bytes_total):>14}")

    largest = sorted(result.files, key=lambda f: f["bytes"], reverse=True)[:top]
    if largest:
        lines.append("")
        lines.append(f"Largest files (top {len(largest)}):")
        for f in largest:
            lines.append(f"  {human_size(f['bytes']):>12}  {f['path']}")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filestats",
        description="Group files in a directory by extension, sum their sizes, "
        "and list the largest files.",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="do not descend into subdirectories",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        metavar="N",
        help="maximum recursion depth (0 = root only)",
    )
    parser.add_argument(
        "--skip-hidden",
        action="store_true",
        help="skip files and directories whose name starts with a dot",
    )
    parser.add_argument(
        "--sort",
        choices=["size", "count"],
        default="size",
        help="sort extension groups by total size or file count (default: size)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="show only the top N extension groups and largest files (default: 10)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable JSON instead of the text table",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        result = scan_directory(
            Path(args.directory),
            recursive=not args.no_recursive,
            max_depth=args.max_depth,
            skip_hidden=args.skip_hidden,
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        payload = {
            "root": str(Path(args.directory).expanduser().resolve()),
            "total_files": result.total_files,
            "total_bytes": result.total_bytes,
            "extensions": {
                ext: {"count": s.count, "bytes": s.bytes_total}
                for ext, s in sorted(
                    result.extensions.items(),
                    key=lambda kv: kv[1].bytes_total,
                    reverse=True,
                )
            },
            "largest_files": sorted(
                result.files, key=lambda f: f["bytes"], reverse=True
            )[: args.top],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    root_path = Path(args.directory).expanduser().resolve()
    print(_format_table(result, sort_by=args.sort, top=args.top, root=root_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

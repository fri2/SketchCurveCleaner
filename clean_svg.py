#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-only
#
# clean_svg.py - pre-clean straight line geometry before importing SVG into Fusion 360.
# Copyright (C) 2026 RICHARD Francois

"""
Pre-clean simple straight-line SVG geometry before import into Fusion 360.

Supported input elements:
- <line>
- <polyline>
- <polygon>
- <path> containing only M, L, H, V and Z/z commands

Unsupported paths, curves, transforms and styled complex elements are preserved
unchanged. The script removes supported straight-line elements and creates one
new group containing merged non-overlapping <line> elements.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET

Point = Tuple[float, float]
Segment = Tuple[Point, Point]

NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
TOKEN_RE = re.compile(r"[MmLlHhVvZz]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def parse_float(value: Optional[str]) -> Optional[float]:
    """Parse an SVG numeric attribute, ignoring simple units when possible."""
    if value is None:
        return None
    match = NUMBER_RE.search(value.strip())
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def local_name(tag: str) -> str:
    """Return an XML tag without namespace."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def has_transform(element: ET.Element) -> bool:
    """Return True when an element has a transform attribute."""
    return bool(element.get("transform"))


def parse_points_attribute(value: str) -> List[Point]:
    """Parse a polyline/polygon points attribute."""
    numbers = [float(x) for x in NUMBER_RE.findall(value or "")]
    return [(numbers[i], numbers[i + 1]) for i in range(0, len(numbers) - 1, 2)]


def segments_from_points(points: Sequence[Point], close: bool) -> List[Segment]:
    """Create consecutive segments from points."""
    segments: List[Segment] = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
    if close and len(points) > 2:
        segments.append((points[-1], points[0]))
    return segments


def is_number_token(token: str) -> bool:
    """Return True when a path token is numeric."""
    return bool(NUMBER_RE.fullmatch(token))


def parse_simple_path(d: str) -> Optional[List[Segment]]:
    """Parse a path containing only M/L/H/V/Z commands."""
    tokens = TOKEN_RE.findall(d or "")
    if not tokens:
        return []

    segments: List[Segment] = []
    i = 0
    cmd: Optional[str] = None
    current: Point = (0.0, 0.0)
    subpath_start: Optional[Point] = None

    def need_number(index: int) -> Optional[float]:
        if index >= len(tokens) or not is_number_token(tokens[index]):
            return None
        return float(tokens[index])

    while i < len(tokens):
        token = tokens[i]

        if re.fullmatch(r"[A-Za-z]", token):
            if token not in "MmLlHhVvZz":
                return None
            cmd = token
            i += 1
        elif cmd is None:
            return None

        if cmd in ("Z", "z"):
            if subpath_start is not None and current != subpath_start:
                segments.append((current, subpath_start))
                current = subpath_start
            cmd = None
            continue

        if cmd in ("M", "m"):
            x = need_number(i)
            y = need_number(i + 1)
            if x is None or y is None:
                return None
            i += 2
            current = (current[0] + x, current[1] + y) if cmd == "m" else (x, y)
            subpath_start = current
            cmd = "l" if cmd == "m" else "L"
            continue

        if cmd in ("L", "l"):
            x = need_number(i)
            y = need_number(i + 1)
            if x is None or y is None:
                return None
            i += 2
            target = (current[0] + x, current[1] + y) if cmd == "l" else (x, y)
            segments.append((current, target))
            current = target
            continue

        if cmd in ("H", "h"):
            x = need_number(i)
            if x is None:
                return None
            i += 1
            target = (current[0] + x, current[1]) if cmd == "h" else (x, current[1])
            segments.append((current, target))
            current = target
            continue

        if cmd in ("V", "v"):
            y = need_number(i)
            if y is None:
                return None
            i += 1
            target = (current[0], current[1] + y) if cmd == "v" else (current[0], y)
            segments.append((current, target))
            current = target
            continue

    return segments


def quant(value: float, tolerance: float) -> int:
    """Quantize a scalar value."""
    return int(round(value / tolerance))


def point_distance(a: Point, b: Point) -> float:
    """Euclidean distance between two SVG points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def canonical_line_key(a: Point, b: Point, tolerance: float) -> Optional[Tuple[int, int, int]]:
    """Return a support-line key for collinear segment grouping."""
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    length = math.hypot(dx, dy)
    if length <= tolerance:
        return None

    ux = dx / length
    uy = dy / length

    if ux < 0 or (abs(ux) <= 1e-12 and uy < 0):
        ux = -ux
        uy = -uy

    nx = -uy
    ny = ux
    offset = a[0] * nx + a[1] * ny

    return (quant(ux, tolerance), quant(uy, tolerance), quant(offset, tolerance))


def project(point: Point, key: Tuple[int, int, int], tolerance: float) -> float:
    """Project a point on the quantized line direction."""
    ux = key[0] * tolerance
    uy = key[1] * tolerance
    length = math.hypot(ux, uy)
    if length <= 1e-12:
        return point[0]
    ux /= length
    uy /= length
    return point[0] * ux + point[1] * uy


def point_from_projection(t: float, key: Tuple[int, int, int], tolerance: float) -> Point:
    """Reconstruct a point from projection and support-line key."""
    ux = key[0] * tolerance
    uy = key[1] * tolerance
    offset = key[2] * tolerance
    length = math.hypot(ux, uy)
    if length <= 1e-12:
        return (t, 0.0)
    ux /= length
    uy /= length
    nx = -uy
    ny = ux
    return (t * ux + offset * nx, t * uy + offset * ny)


def merge_segments(segments: Iterable[Segment], tolerance: float) -> List[Segment]:
    """Remove zero-length segments and merge overlapping collinear segments."""
    groups: Dict[Tuple[int, int, int], List[Tuple[float, float]]] = {}

    for a, b in segments:
        if point_distance(a, b) <= tolerance:
            continue

        key = canonical_line_key(a, b, tolerance)
        if key is None:
            continue

        t1 = project(a, key, tolerance)
        t2 = project(b, key, tolerance)
        if t2 < t1:
            t1, t2 = t2, t1

        groups.setdefault(key, []).append((t1, t2))

    result: List[Segment] = []

    for key, intervals in groups.items():
        intervals.sort()
        merged: List[List[float]] = []

        for t1, t2 in intervals:
            if not merged:
                merged.append([t1, t2])
                continue

            last = merged[-1]
            if t1 <= last[1] + tolerance:
                last[1] = max(last[1], t2)
            else:
                merged.append([t1, t2])

        for t1, t2 in merged:
            a = point_from_projection(t1, key, tolerance)
            b = point_from_projection(t2, key, tolerance)
            if point_distance(a, b) > tolerance:
                result.append((a, b))

    return result


def collect_supported_segments(root: ET.Element) -> Tuple[List[Segment], List[ET.Element]]:
    """Collect simple straight-line elements and elements to remove."""
    segments: List[Segment] = []
    removable: List[ET.Element] = []

    for elem in list(root.iter()):
        name = local_name(elem.tag)

        if has_transform(elem):
            continue

        if name == "line":
            x1 = parse_float(elem.get("x1"))
            y1 = parse_float(elem.get("y1"))
            x2 = parse_float(elem.get("x2"))
            y2 = parse_float(elem.get("y2"))
            if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
                segments.append(((x1, y1), (x2, y2)))
                removable.append(elem)
            continue

        if name in ("polyline", "polygon"):
            points = parse_points_attribute(elem.get("points", ""))
            if len(points) >= 2:
                segments.extend(segments_from_points(points, close=(name == "polygon")))
                removable.append(elem)
            continue

        if name == "path":
            parsed = parse_simple_path(elem.get("d", ""))
            if parsed is not None:
                segments.extend(parsed)
                removable.append(elem)
            continue

    return segments, removable


def remove_elements(root: ET.Element, elements: Sequence[ET.Element]) -> None:
    """Remove elements from their parent nodes."""
    parent_map = {child: parent for parent in root.iter() for child in parent}
    for elem in elements:
        parent = parent_map.get(elem)
        if parent is not None:
            try:
                parent.remove(elem)
            except ValueError:
                pass


def add_cleaned_group(root: ET.Element, segments: Sequence[Segment]) -> None:
    """Append a group containing cleaned line elements."""
    group = ET.Element("g", {
        "id": "cleaned_line_segments",
        "fill": "none",
        "stroke": "black",
        "stroke-width": "0.1",
    })

    for a, b in segments:
        ET.SubElement(group, "line", {
            "x1": f"{a[0]:.6f}",
            "y1": f"{a[1]:.6f}",
            "x2": f"{b[0]:.6f}",
            "y2": f"{b[1]:.6f}",
        })

    root.append(group)


def clean_svg(input_path: Path, output_path: Path, tolerance: float) -> Tuple[int, int]:
    """Clean a SVG file and write the output file."""
    tree = ET.parse(input_path)
    root = tree.getroot()

    segments, removable = collect_supported_segments(root)
    merged = merge_segments(segments, tolerance)

    remove_elements(root, removable)
    add_cleaned_group(root, merged)

    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return (len(segments), len(merged))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Pre-clean simple straight-line SVG geometry before Fusion 360 import."
    )
    parser.add_argument("input_svg", type=Path, help="Input SVG file")
    parser.add_argument("-o", "--output", type=Path, help="Output SVG file")
    parser.add_argument(
        "-t",
        "--tolerance",
        type=float,
        default=0.01,
        help="Tolerance in SVG user units. Default: 0.01",
    )

    args = parser.parse_args(argv)

    if not args.input_svg.exists():
        print(f"Input file not found: {args.input_svg}", file=sys.stderr)
        return 2

    output = args.output
    if output is None:
        output = args.input_svg.with_name(args.input_svg.stem + "_cleaned.svg")

    before, after = clean_svg(args.input_svg, output, max(args.tolerance, 1e-9))

    print(f"Input segments processed : {before}")
    print(f"Output segments written   : {after}")
    print(f"Output SVG                : {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

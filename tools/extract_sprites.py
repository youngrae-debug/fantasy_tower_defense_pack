#!/usr/bin/env python3
"""Extract rogue turnarounds and item icons from a reference sheet.

Deterministic workflow:
1) Read bounding boxes from config.
2) Try auto-detection inside each search rect based on sampled background color.
3) If auto-detection cannot find a valid component, fallback to config bbox.
4) Remove background connected to crop edges and export padded transparent PNGs.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
from PIL import Image

Rect = Tuple[int, int, int, int]


def clamp_rect(rect: Rect, width: int, height: int) -> Rect:
    x0, y0, x1, y1 = rect
    return max(0, x0), max(0, y0), min(width, x1), min(height, y1)


def parse_rect(values: Iterable[int]) -> Rect:
    x0, y0, x1, y1 = map(int, values)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"Invalid rect {values}")
    return x0, y0, x1, y1


def sample_background_color(rgb: np.ndarray, margin: int) -> np.ndarray:
    h, w, _ = rgb.shape
    m = max(1, min(margin, w // 6, h // 6))
    patches = [
        rgb[:m, :m, :],
        rgb[:m, -m:, :],
        rgb[-m:, :m, :],
        rgb[-m:, -m:, :],
    ]
    stacked = np.concatenate([p.reshape(-1, 3) for p in patches], axis=0)
    return np.array([median(stacked[:, i]) for i in range(3)], dtype=np.float32)


def dist_to_bg(rgb: np.ndarray, bg: np.ndarray) -> np.ndarray:
    delta = rgb.astype(np.float32) - bg.reshape(1, 1, 3)
    return np.sqrt(np.sum(delta * delta, axis=2))


def largest_component_bbox(mask: np.ndarray, min_area: int) -> Optional[Rect]:
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    best_area = 0
    best_bbox = None

    for y in range(h):
        for x in range(w):
            if visited[y, x] or not mask[y, x]:
                continue
            q = deque([(x, y)])
            visited[y, x] = True
            area = 0
            min_x = max_x = x
            min_y = max_y = y

            while q:
                cx, cy = q.popleft()
                area += 1
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)

                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx] and mask[ny, nx]:
                        visited[ny, nx] = True
                        q.append((nx, ny))

            if area >= min_area and area > best_area:
                best_area = area
                best_bbox = (min_x, min_y, max_x + 1, max_y + 1)

    return best_bbox


def detect_bbox_in_search(
    rgb: np.ndarray,
    search_rect: Rect,
    bg: np.ndarray,
    bg_tol: float,
    min_area: int,
) -> Optional[Rect]:
    x0, y0, x1, y1 = search_rect
    region = rgb[y0:y1, x0:x1, :]
    if region.size == 0:
        return None
    fg_mask = dist_to_bg(region, bg) > bg_tol
    comp = largest_component_bbox(fg_mask, min_area=min_area)
    if comp is None:
        return None
    rx0, ry0, rx1, ry1 = comp
    return x0 + rx0, y0 + ry0, x0 + rx1, y0 + ry1


def edge_connected_bg_mask(rgb: np.ndarray, bg: np.ndarray, tol: float) -> np.ndarray:
    h, w, _ = rgb.shape
    near_bg = dist_to_bg(rgb, bg) <= tol
    visited = np.zeros((h, w), dtype=bool)
    q = deque()

    for x in range(w):
        if near_bg[0, x]:
            q.append((x, 0))
            visited[0, x] = True
        if near_bg[h - 1, x] and not visited[h - 1, x]:
            q.append((x, h - 1))
            visited[h - 1, x] = True

    for y in range(h):
        if near_bg[y, 0] and not visited[y, 0]:
            q.append((0, y))
            visited[y, 0] = True
        if near_bg[y, w - 1] and not visited[y, w - 1]:
            q.append((w - 1, y))
            visited[y, w - 1] = True

    while q:
        cx, cy = q.popleft()
        for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx] and near_bg[ny, nx]:
                visited[ny, nx] = True
                q.append((nx, ny))

    return visited


def trim_alpha_bbox(alpha: np.ndarray) -> Optional[Rect]:
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def add_padding(rect: Rect, padding: int, width: int, height: int) -> Rect:
    x0, y0, x1, y1 = rect
    return clamp_rect((x0 - padding, y0 - padding, x1 + padding, y1 + padding), width, height)


def export_sprite(
    src_rgb: np.ndarray,
    rect: Rect,
    bg: np.ndarray,
    cfg_alpha: Dict[str, float],
    padding: int,
    out_path: Path,
) -> None:
    h, w, _ = src_rgb.shape
    x0, y0, x1, y1 = add_padding(rect, padding, w, h)
    crop = src_rgb[y0:y1, x0:x1, :].copy()

    bg_mask = edge_connected_bg_mask(crop, bg, tol=cfg_alpha["edge_expand_tolerance"])
    alpha = np.where(bg_mask, 0, 255).astype(np.uint8)

    tight = trim_alpha_bbox(alpha)
    if tight is None:
        raise RuntimeError(f"Crop became empty after background removal: {out_path}")

    tx0, ty0, tx1, ty1 = tight
    crop = crop[ty0:ty1, tx0:tx1, :]
    alpha = alpha[ty0:ty1, tx0:tx1]

    rgba = np.dstack([crop, alpha])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode="RGBA").save(out_path)


def run(config_path: Path, dry_run: bool = False) -> None:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    source = Path(cfg["source_image"])
    if not source.exists():
        raise FileNotFoundError(f"Source image not found: {source}")

    image = Image.open(source).convert("RGB")
    rgb = np.array(image)
    h, w, _ = rgb.shape

    alpha_cfg = cfg["alpha"]
    bg = sample_background_color(rgb, margin=int(alpha_cfg["bg_sample_margin"]))
    bg_tol = float(alpha_cfg["bg_color_tolerance"])
    default_padding = int(cfg.get("default_padding", 12))

    print(f"[info] source={source} size={w}x{h} bg_sample={bg.tolist()}")

    for item in cfg["outputs"]:
        name = item["name"]
        bbox = clamp_rect(parse_rect(item["bbox"]), w, h)
        search_rect = parse_rect(item.get("search_rect", item["bbox"]))
        search_rect = clamp_rect(search_rect, w, h)
        min_area = int(item.get("min_area", 400))
        padding = int(item.get("padding", default_padding))
        out_path = Path(item["output"])

        detected = detect_bbox_in_search(rgb, search_rect, bg, bg_tol=bg_tol, min_area=min_area)
        chosen = detected if detected is not None else bbox
        mode = "auto" if detected is not None else "fallback"

        print(f"[item] {name}: mode={mode} rect={chosen} output={out_path}")
        if not dry_run:
            export_sprite(rgb, chosen, bg=bg, cfg_alpha=alpha_cfg, padding=padding, out_path=out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract sprites from a turnaround reference sheet")
    parser.add_argument(
        "--config",
        default="tools/extract_config.json",
        help="Path to extraction config JSON",
    )
    parser.add_argument("--dry-run", action="store_true", help="Resolve boxes without writing files")
    args = parser.parse_args()

    run(Path(args.config), dry_run=args.dry_run)


if __name__ == "__main__":
    main()

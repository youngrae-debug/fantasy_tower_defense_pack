#!/usr/bin/env python3
"""Extract character turnarounds/items from a reference sheet.

Supports two config styles:
1) explicit `outputs` entries (legacy)
2) `character_form` (new): auto-build front/side/back outputs from a 3-pose sheet
"""

from __future__ import annotations

import argparse
import json
from collections import deque
import struct
import zlib
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, Optional, Tuple

Rect = Tuple[int, int, int, int]
np = None
Image = None


def _read_png_rgb8(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Only PNG is supported in fallback mode: {path}")

    i = 8
    width = height = None
    bit_depth = color_type = interlace = None
    idat_parts: list[bytes] = []

    while i < len(data):
        length = struct.unpack(">I", data[i : i + 4])[0]
        ctype = data[i + 4 : i + 8]
        chunk = data[i + 8 : i + 8 + length]
        i += length + 12

        if ctype == b"IHDR":
            width, height, bit_depth, color_type, _cm, _fm, interlace = struct.unpack(">IIBBBBB", chunk)
        elif ctype == b"IDAT":
            idat_parts.append(chunk)
        elif ctype == b"IEND":
            break

    if width is None or height is None:
        raise ValueError(f"Invalid PNG (no IHDR): {path}")
    if bit_depth != 8 or color_type != 2 or interlace != 0:
        raise ValueError(
            "Fallback mode supports only non-interlaced PNG RGB8 (color_type=2, bit_depth=8)"
        )

    raw = zlib.decompress(b"".join(idat_parts))
    bpp = 3
    stride = width * bpp
    expected = (stride + 1) * height
    if len(raw) != expected:
        raise ValueError("Unexpected decompressed PNG size")

    out = bytearray(height * stride)
    prev = bytes(stride)
    src_i = 0
    dst_i = 0

    for _ in range(height):
        f = raw[src_i]
        src_i += 1
        cur = bytearray(raw[src_i : src_i + stride])
        src_i += stride

        if f == 1:
            for x in range(stride):
                left = cur[x - bpp] if x >= bpp else 0
                cur[x] = (cur[x] + left) & 0xFF
        elif f == 2:
            for x in range(stride):
                cur[x] = (cur[x] + prev[x]) & 0xFF
        elif f == 3:
            for x in range(stride):
                left = cur[x - bpp] if x >= bpp else 0
                cur[x] = (cur[x] + ((left + prev[x]) // 2)) & 0xFF
        elif f == 4:
            for x in range(stride):
                a = cur[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                cur[x] = (cur[x] + pr) & 0xFF
        elif f != 0:
            raise ValueError(f"Unsupported PNG filter type: {f}")

        out[dst_i : dst_i + stride] = cur
        prev = bytes(cur)
        dst_i += stride

    return width, height, bytes(out)


def _write_png_rgb8(path: Path, width: int, height: int, rgb: bytes) -> None:
    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        start = y * stride
        raw.extend(rgb[start : start + stride])

    def chunk(name: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + name
            + payload
            + struct.pack(">I", zlib.crc32(name + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), level=9)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def _crop_rgb(rgb: bytes, src_w: int, rect: Rect) -> tuple[int, int, bytes]:
    x0, y0, x1, y1 = rect
    out_w, out_h = x1 - x0, y1 - y0
    src_stride = src_w * 3
    out = bytearray(out_w * out_h * 3)
    o = 0
    for y in range(y0, y1):
        start = y * src_stride + x0 * 3
        end = start + out_w * 3
        row = rgb[start:end]
        out[o : o + len(row)] = row
        o += len(row)
    return out_w, out_h, bytes(out)


def run_fallback_without_numpy_pillow(
    config_path: Path,
    cfg: Dict[str, object],
    source: Path,
    dry_run: bool = False,
    rebuild_outputs: bool = False,
    write_config: bool = False,
) -> None:
    width, height, rgb = _read_png_rgb8(source)
    outputs = resolve_outputs(
        cfg,
        width,
        height,
        config_path,
        rebuild_outputs=rebuild_outputs,
        write_config=write_config,
    )

    print("[warn] numpy/pillow not available; using fallback crop mode (RGB PNG only, no bg-removal/refine)")
    for item in outputs:
        rect = clamp_rect(parse_rect(item["bbox"]), width, height)
        out_path = Path(item["output"])
        out_w, out_h, cropped = _crop_rgb(rgb, width, rect)
        if not dry_run:
            _write_png_rgb8(out_path, out_w, out_h, cropped)
        print(f"[item] {item['name']}: mode=fallback-crop rect={rect} output={out_path}")




def resolve_outputs(
    cfg: Dict[str, object],
    width: int,
    height: int,
    config_path: Path,
    rebuild_outputs: bool = False,
    write_config: bool = False,
) -> list[Dict[str, object]]:
    existing = list(cfg.get("outputs", []))
    has_form = bool(cfg.get("character_form"))

    if has_form and (rebuild_outputs or not existing):
        outputs = build_outputs_from_character_form(cfg, width, height)
        if write_config:
            cfg["outputs"] = outputs
            config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"[info] outputs rebuilt from character_form and saved ({len(outputs)} items)")
        else:
            print(f"[info] outputs rebuilt from character_form in-memory ({len(outputs)} items)")
        return outputs

    if existing:
        print(f"[info] using preconfigured outputs from config ({len(existing)} items)")
    return existing
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
    patches = [rgb[:m, :m, :], rgb[:m, -m:, :], rgb[-m:, :m, :], rgb[-m:, -m:, :]]
    stacked = np.concatenate([p.reshape(-1, 3) for p in patches], axis=0)
    return np.array([median(stacked[:, i]) for i in range(3)], dtype=np.float32)


def dist_to_bg(rgb: np.ndarray, bg: np.ndarray) -> np.ndarray:
    delta = rgb.astype(np.float32) - bg.reshape(1, 1, 3)
    return np.sqrt(np.sum(delta * delta, axis=2))


def extract_components(mask: np.ndarray, min_area: int) -> list[tuple[Rect, int]]:
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    out: list[tuple[Rect, int]] = []

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
                min_x, max_x = min(min_x, cx), max(max_x, cx)
                min_y, max_y = min(min_y, cy), max(max_y, cy)
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx] and mask[ny, nx]:
                        visited[ny, nx] = True
                        q.append((nx, ny))
            if area >= min_area:
                out.append(((min_x, min_y, max_x + 1, max_y + 1), area))
    return out


def rect_iou(a: Rect, b: Rect) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    area_a = max(0, ax1 - ax0) * max(0, ay1 - ay0)
    area_b = max(0, bx1 - bx0) * max(0, by1 - by0)
    union = area_a + area_b - inter
    return (inter / union) if union > 0 else 0.0


def rect_center_distance(a: Rect, b: Rect) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    acx, acy = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0
    bcx, bcy = (bx0 + bx1) / 2.0, (by0 + by1) / 2.0
    return ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5


def choose_component(components: list[tuple[Rect, int]], expected_rect: Optional[Rect]) -> Optional[Rect]:
    if not components:
        return None
    if expected_rect is None:
        return max(components, key=lambda c: c[1])[0]

    best = None
    best_score = -1e18
    for rect, area in components:
        score = (rect_iou(rect, expected_rect) * 15000.0) - (rect_center_distance(rect, expected_rect) * 8.0) + float(area)
        if score > best_score:
            best_score = score
            best = rect
    return best


def detect_bbox_in_search(
    rgb: np.ndarray,
    search_rect: Rect,
    bg: np.ndarray,
    bg_tol: float,
    min_area: int,
    expected_rect: Optional[Rect],
) -> Optional[Rect]:
    x0, y0, x1, y1 = search_rect
    region = rgb[y0:y1, x0:x1, :]
    if region.size == 0:
        return None
    fg_mask = dist_to_bg(region, bg) > bg_tol
    comps = extract_components(fg_mask, min_area=min_area)
    expected_local = None
    if expected_rect is not None:
        ex0, ey0, ex1, ey1 = expected_rect
        expected_local = (ex0 - x0, ey0 - y0, ex1 - x0, ey1 - y0)
    chosen = choose_component(comps, expected_local)
    if chosen is None:
        return None
    rx0, ry0, rx1, ry1 = chosen
    return x0 + rx0, y0 + ry0, x0 + rx1, y0 + ry1


def add_padding(rect: Rect, padding: int, width: int, height: int) -> Rect:
    x0, y0, x1, y1 = rect
    return clamp_rect((x0 - padding, y0 - padding, x1 + padding, y1 + padding), width, height)




def apply_bbox_adjustments(base_bbox: list[int], adjust: list[int]) -> list[int]:
    if len(adjust) != 4:
        raise ValueError("bbox_adjust_px must have 4 integers: [left, top, right, bottom]")
    return [
        int(base_bbox[0] + adjust[0]),
        int(base_bbox[1] + adjust[1]),
        int(base_bbox[2] + adjust[2]),
        int(base_bbox[3] + adjust[3]),
    ]

def component_mask_from_crop(crop: np.ndarray, bg: np.ndarray, expected_rect_in_crop: Rect, min_area: int, fg_tol: float) -> np.ndarray:
    fg_mask = dist_to_bg(crop, bg) > fg_tol
    comps = extract_components(fg_mask, min_area=max(20, min_area // 8))
    chosen = choose_component(comps, expected_rect_in_crop)
    if chosen is None:
        return fg_mask

    x0, y0, x1, y1 = chosen
    keep = np.zeros_like(fg_mask, dtype=bool)
    keep[y0:y1, x0:x1] = fg_mask[y0:y1, x0:x1]
    return keep


def feather_alpha(mask: np.ndarray, soft_px: int) -> np.ndarray:
    alpha = np.where(mask, 255, 0).astype(np.uint8)
    if soft_px <= 0:
        return alpha
    a = alpha.astype(np.float32)
    for _ in range(soft_px):
        p = np.pad(a, 1, mode="edge")
        a = (p[1:-1, 1:-1] * 4 + p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 8.0
        a[mask] = 255.0
    return np.clip(a, 0, 255).astype(np.uint8)


def trim_alpha_bbox(alpha: np.ndarray) -> Optional[Rect]:
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def export_sprite(src_rgb: np.ndarray, rect: Rect, bg: np.ndarray, cfg_alpha: Dict[str, float], padding: int, out_path: Path, remove_background: bool = True) -> None:
    h, w, _ = src_rgb.shape
    x0, y0, x1, y1 = add_padding(rect, padding, w, h)
    crop = src_rgb[y0:y1, x0:x1, :].copy()

    if remove_background:
        expected = (rect[0] - x0, rect[1] - y0, rect[2] - x0, rect[3] - y0)
        keep_mask = component_mask_from_crop(
            crop,
            bg=bg,
            expected_rect_in_crop=expected,
            min_area=int(cfg_alpha.get("component_min_area", 80)),
            fg_tol=float(cfg_alpha.get("target_component_tolerance", cfg_alpha["bg_color_tolerance"])),
        )
        alpha = feather_alpha(keep_mask, soft_px=int(cfg_alpha.get("edge_feather_px", 1)))
    else:
        alpha = np.full((crop.shape[0], crop.shape[1]), 255, dtype=np.uint8)

    tight = trim_alpha_bbox(alpha)
    if tight is None:
        raise RuntimeError(f"Crop became empty after background removal: {out_path}")

    tx0, ty0, tx1, ty1 = tight
    rgba = np.dstack([crop[ty0:ty1, tx0:tx1, :], alpha[ty0:ty1, tx0:tx1]])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode="RGBA").save(out_path)


def refine_bbox_near_rect(rgb: np.ndarray, base_rect: Rect, bg: np.ndarray, bg_tol: float, refine_margin: int) -> Rect:
    h, w, _ = rgb.shape
    sx0, sy0, sx1, sy1 = add_padding(base_rect, refine_margin, w, h)
    search = rgb[sy0:sy1, sx0:sx1, :]
    fg_mask = dist_to_bg(search, bg) > bg_tol
    comps = extract_components(fg_mask, min_area=20)
    local = (base_rect[0] - sx0, base_rect[1] - sy0, base_rect[2] - sx0, base_rect[3] - sy0)
    chosen = choose_component(comps, local)
    if chosen is None:
        return base_rect
    tx0, ty0, tx1, ty1 = chosen
    return clamp_rect((sx0 + tx0, sy0 + ty0, sx0 + tx1, sy0 + ty1), w, h)


def guess_source_from_reference(source: Path) -> Optional[Path]:
    if source.exists():
        return source
    ref_dir = source.parent
    if not ref_dir.exists():
        return None
    candidates = sorted([p for p in ref_dir.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}])
    return candidates[0] if candidates else None


def build_outputs_from_character_form(cfg: Dict[str, object], width: int, height: int) -> list[Dict[str, object]]:
    form = cfg.get("character_form")
    if not form:
        return list(cfg.get("outputs", []))

    package_name = form.get("package_name", cfg.get("package_name", "Rogue2DKit"))
    character_name = form.get("character_name", "Knight")
    order = list(form.get("order", ["front", "side", "back"]))
    if len(order) != 3:
        raise ValueError("character_form.order must have exactly 3 entries")

    split_ratios = form.get("split_ratios", [0.3333, 0.6666])
    if len(split_ratios) != 2:
        raise ValueError("character_form.split_ratios must have 2 float values")

    r1, r2 = float(split_ratios[0]), float(split_ratios[1])
    x1, x2 = int(width * r1), int(width * r2)

    y_ratio = form.get("y_ratio", [0.08, 0.95])
    y0, y1 = int(height * float(y_ratio[0])), int(height * float(y_ratio[1]))

    section_margin = int(form.get("section_margin_px", 24))
    padding = int(form.get("padding", cfg.get("default_padding", 12)))
    min_area = int(form.get("min_area", 7000))
    remove_background = bool(form.get("remove_background", cfg.get("remove_background", True)))
    use_detected_bbox = bool(form.get("use_detected_bbox", True))
    use_refine = bool(form.get("use_refine", True))
    pose_overrides = form.get("pose_overrides", {})

    sections = [(0, x1), (x1, x2), (x2, width)]
    outputs: list[Dict[str, object]] = []

    for idx, pose in enumerate(order):
        sx0, sx1 = sections[idx]
        bbox = [sx0 + section_margin, y0 + section_margin, sx1 - section_margin, y1 - section_margin]
        override = pose_overrides.get(pose, {}) if isinstance(pose_overrides, dict) else {}
        bbox_adjust = override.get("bbox_adjust_px", [0, 0, 0, 0])
        bbox = apply_bbox_adjustments(bbox, bbox_adjust)
        search = [sx0, y0, sx1, y1]
        outputs.append(
            {
                "name": f"{character_name.lower()}_{pose}",
                "kind": "character",
                "output": f"Assets/{package_name}/Art/Sprites/Characters/{character_name}/Turnaround/{character_name.lower()}_{pose}.png",
                "bbox": bbox,
                "search_rect": search,
                "padding": padding,
                "min_area": min_area,
                "min_iou_with_bbox": float(form.get("min_iou_with_bbox", 0.25)),
                "max_center_shift": float(form.get("max_center_shift", 160.0)),
                "refine_margin": int(form.get("refine_margin", 16)),
                "remove_background": bool(override.get("remove_background", remove_background)),
                "use_detected_bbox": bool(override.get("use_detected_bbox", use_detected_bbox)),
                "use_refine": bool(override.get("use_refine", use_refine)),
            }
        )

    return outputs


def print_dry_run_without_image(cfg: Dict[str, object]) -> None:
    print("[warn] source image not found; running config-only dry-run")
    if cfg.get("character_form") and not cfg.get("outputs"):
        print("[info] character_form detected but outputs are empty; add source image (or prefill outputs) to resolve boxes")
    outputs = cfg.get("outputs", [])
    for item in outputs:
        print(f"[item] {item['name']}: mode=fallback(no-image) rect={tuple(item['bbox'])} output={item['output']}")


def run(config_path: Path, dry_run: bool = False, rebuild_outputs: bool = False, write_config: bool = False) -> None:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    configured_source = Path(cfg["source_image"])
    source = guess_source_from_reference(configured_source)

    if source is None:
        if dry_run:
            print_dry_run_without_image(cfg)
            return
        raise FileNotFoundError(f"Source image not found: {configured_source}")

    if source != configured_source:
        print(f"[warn] configured source missing: {configured_source}")
        print(f"[info] using detected reference image instead: {source}")

    global np, Image
    try:
        import numpy as np  # type: ignore[no-redef]
        from PIL import Image  # type: ignore[no-redef]
    except ModuleNotFoundError:
        if dry_run:
            print("[warn] numpy/pillow not installed; running fallback export path in dry-run")
        run_fallback_without_numpy_pillow(
            config_path,
            cfg,
            source,
            dry_run=dry_run,
            rebuild_outputs=rebuild_outputs,
            write_config=write_config,
        )
        return

    image = Image.open(source).convert("RGB")
    rgb = np.array(image)
    h, w, _ = rgb.shape

    alpha_cfg = cfg["alpha"]
    bg = sample_background_color(rgb, margin=int(alpha_cfg["bg_sample_margin"]))
    bg_tol = float(alpha_cfg["bg_color_tolerance"])

    outputs = resolve_outputs(
        cfg,
        w,
        h,
        config_path,
        rebuild_outputs=rebuild_outputs,
        write_config=write_config,
    )

    print(f"[info] source={source} size={w}x{h} bg_sample={bg.tolist()}")

    for item in outputs:
        name = item["name"]
        bbox = clamp_rect(parse_rect(item["bbox"]), w, h)
        search_rect = clamp_rect(parse_rect(item.get("search_rect", item["bbox"])), w, h)
        min_area = int(item.get("min_area", 400))
        padding = int(item.get("padding", cfg.get("default_padding", 12)))
        min_iou = float(item.get("min_iou_with_bbox", 0.30))
        max_center_shift = float(item.get("max_center_shift", 140.0))
        refine_margin = int(item.get("refine_margin", 24))
        out_path = Path(item["output"])

        use_detected_bbox = bool(item.get("use_detected_bbox", True))
        use_refine = bool(item.get("use_refine", True))

        if use_detected_bbox:
            detected = detect_bbox_in_search(rgb, search_rect, bg, bg_tol, min_area, expected_rect=bbox)
            if detected is not None:
                iou = rect_iou(detected, bbox)
                center_shift = rect_center_distance(detected, bbox)
                if iou < min_iou or center_shift > max_center_shift:
                    chosen = bbox
                    mode = "fallback(validated)"
                else:
                    chosen = detected
                    mode = f"auto(iou={iou:.3f},shift={center_shift:.1f})"
            else:
                chosen = bbox
                mode = "fallback"
        else:
            chosen = bbox
            mode = "manual(bbox)"

        if use_refine:
            chosen = refine_bbox_near_rect(rgb, chosen, bg, bg_tol, refine_margin)
        print(f"[item] {name}: mode={mode} rect={chosen} output={out_path}")
        if not dry_run:
            export_sprite(rgb, chosen, bg, alpha_cfg, padding, out_path, remove_background=bool(item.get("remove_background", True)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract sprites from a turnaround reference sheet")
    parser.add_argument("--config", default="tools/extract_config.json", help="Path to extraction config JSON")
    parser.add_argument("--dry-run", action="store_true", help="Resolve boxes without writing files")
    parser.add_argument(
        "--rebuild-outputs-from-form",
        action="store_true",
        help="Rebuild outputs from character_form in-memory (does not modify config unless --write-config is set)",
    )
    parser.add_argument(
        "--write-config",
        action="store_true",
        help="When rebuilding outputs, persist rebuilt outputs back to config file",
    )
    args = parser.parse_args()
    run(
        Path(args.config),
        dry_run=args.dry_run,
        rebuild_outputs=args.rebuild_outputs_from_form,
        write_config=args.write_config,
    )


if __name__ == "__main__":
    main()

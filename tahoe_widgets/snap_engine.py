"""Tính toán đường gióng thông minh (Smart Guides) và lực hít (Magnetic Snap) khi kéo widget."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class GuideLine:
    orientation: str  # "v" | "h"
    pos: int          # x cho "v", y cho "h"
    start: int        # y1 cho "v", x1 cho "h"
    end: int          # y2 cho "v", x2 cho "h"


@dataclass(frozen=True)
class GapBadge:
    orientation: str  # "v" (khoảng cách dọc) | "h" (khoảng cách ngang)
    x1: int
    y1: int
    x2: int
    y2: int
    label: str


@dataclass(frozen=True)
class SnapResult:
    x: int
    y: int
    guides: tuple[GuideLine, ...] = ()
    badges: tuple[GapBadge, ...] = ()


def _ranges_overlap(a1: int, a2: int, b1: int, b2: int, padding: int = 80) -> bool:
    return (a2 + padding) >= b1 and (b2 + padding) >= a1


def compute_snap(
    moving: Rect,
    others: list[Rect],
    screen: Rect,
    threshold: int = 10,
    edge_margin: int = 24,
    card_gap: int = 14,
) -> SnapResult:
    """Tính tọa độ đã hít cùng các đường gióng và nhãn khoảng cách hiển thị."""
    # (distance, snapped_coord, priority)
    x_candidates: list[tuple[int, int]] = []
    y_candidates: list[tuple[int, int]] = []

    # 1. Lề màn hình & tâm màn hình
    x_candidates.append((abs(moving.x - (screen.x + edge_margin)), screen.x + edge_margin))
    right_snap_x = screen.x + screen.w - edge_margin - moving.w
    x_candidates.append((abs(moving.x - right_snap_x), right_snap_x))
    center_snap_x = screen.x + (screen.w - moving.w) // 2
    x_candidates.append((abs(moving.x - center_snap_x), center_snap_x))

    y_candidates.append((abs(moving.y - (screen.y + edge_margin)), screen.y + edge_margin))
    bottom_snap_y = screen.y + screen.h - edge_margin - moving.h
    y_candidates.append((abs(moving.y - bottom_snap_y), bottom_snap_y))
    center_snap_y = screen.y + (screen.h - moving.h) // 2
    y_candidates.append((abs(moving.y - center_snap_y), center_snap_y))

    # 2. Thẳng hàng & khoảng cách chuẩn với các widget khác
    for o in others:
        # Căn thẳng X: mép trái, mép phải, tâm ngang
        x_candidates.append((abs(moving.x - o.x), o.x))
        x_candidates.append((abs(moving.x - (o.x + o.w - moving.w)), o.x + o.w - moving.w))
        x_candidates.append((abs(moving.x - (o.x + (o.w - moving.w) // 2)), o.x + (o.w - moving.w) // 2))

        # Khoảng cách ngang chuẩn card_gap
        if _ranges_overlap(moving.y, moving.y + moving.h, o.y, o.y + o.h):
            x_candidates.append((abs(moving.x - (o.x + o.w + card_gap)), o.x + o.w + card_gap))
            x_candidates.append((abs(moving.x - (o.x - card_gap - moving.w)), o.x - card_gap - moving.w))

        # Căn thẳng Y: mép trên, mép dưới, tâm dọc
        y_candidates.append((abs(moving.y - o.y), o.y))
        y_candidates.append((abs(moving.y - (o.y + o.h - moving.h)), o.y + o.h - moving.h))
        y_candidates.append((abs(moving.y - (o.y + (o.h - moving.h) // 2)), o.y + (o.h - moving.h) // 2))

        # Khoảng cách dọc chuẩn card_gap
        if _ranges_overlap(moving.x, moving.x + moving.w, o.x, o.x + o.w):
            y_candidates.append((abs(moving.y - (o.y + o.h + card_gap)), o.y + o.h + card_gap))
            y_candidates.append((abs(moving.y - (o.y - card_gap - moving.h)), o.y - card_gap - moving.h))

    best_x = moving.x
    best_dx = threshold + 1
    for dist, cand in x_candidates:
        if dist <= threshold and dist < best_dx:
            best_dx = dist
            best_x = cand

    best_y = moving.y
    best_dy = threshold + 1
    for dist, cand in y_candidates:
        if dist <= threshold and dist < best_dy:
            best_dy = dist
            best_y = cand

    # Thu thập toàn bộ đường gióng và nhãn khoảng cách khớp tại (best_x, best_y)
    guides: list[GuideLine] = []
    badges: list[GapBadge] = []
    seen_guides: set[tuple[str, int, int, int]] = set()
    seen_badges: set[tuple[str, int, int, int, int, str]] = set()

    def add_guide(orient: str, pos: int, start: int, end: int) -> None:
        key = (orient, pos, min(start, end), max(start, end))
        if key not in seen_guides:
            seen_guides.add(key)
            guides.append(GuideLine(orient, pos, key[2], key[3]))

    def add_badge(orient: str, x1: int, y1: int, x2: int, y2: int, label: str) -> None:
        key = (orient, x1, y1, x2, y2, label)
        if key not in seen_badges:
            seen_badges.add(key)
            badges.append(GapBadge(orient, x1, y1, x2, y2, label))

    # Đường gióng & nhãn lề màn hình
    if best_x == screen.x + edge_margin:
        add_guide("v", screen.x + edge_margin, screen.y, screen.y + screen.h)
        mid_y = best_y + moving.h // 2
        add_badge("h", screen.x, mid_y, best_x, mid_y, f"{edge_margin} px")
    if best_x == right_snap_x:
        rx = screen.x + screen.w - edge_margin
        add_guide("v", rx, screen.y, screen.y + screen.h)
        mid_y = best_y + moving.h // 2
        add_badge("h", best_x + moving.w, mid_y, rx + edge_margin, mid_y, f"{edge_margin} px")
    if best_x == center_snap_x:
        add_guide("v", screen.x + screen.w // 2, screen.y, screen.y + screen.h)

    if best_y == screen.y + edge_margin:
        add_guide("h", screen.y + edge_margin, screen.x, screen.x + screen.w)
        mid_x = best_x + moving.w // 2
        add_badge("v", mid_x, screen.y, mid_x, best_y, f"{edge_margin} px")
    if best_y == bottom_snap_y:
        by = screen.y + screen.h - edge_margin
        add_guide("h", by, screen.x, screen.x + screen.w)
        mid_x = best_x + moving.w // 2
        add_badge("v", mid_x, best_y + moving.h, mid_x, by + edge_margin, f"{edge_margin} px")
    if best_y == center_snap_y:
        add_guide("h", screen.y + screen.h // 2, screen.x, screen.x + screen.w)

    # Đường gióng & nhãn khoảng cách với các widget khác
    for o in others:
        # Căn thẳng X
        if best_x == o.x:
            add_guide("v", o.x, min(best_y, o.y) - 12, max(best_y + moving.h, o.y + o.h) + 12)
        if best_x + moving.w == o.x + o.w:
            add_guide("v", o.x + o.w, min(best_y, o.y) - 12, max(best_y + moving.h, o.y + o.h) + 12)
        if abs((best_x + moving.w / 2.0) - (o.x + o.w / 2.0)) <= 1.0:
            cx = round(o.x + o.w / 2.0)
            add_guide("v", cx, min(best_y, o.y) - 12, max(best_y + moving.h, o.y + o.h) + 12)

        # Khoảng cách ngang card_gap
        if _ranges_overlap(best_y, best_y + moving.h, o.y, o.y + o.h, padding=20):
            overlap_y = (max(best_y, o.y) + min(best_y + moving.h, o.y + o.h)) // 2
            if best_x == o.x + o.w + card_gap:
                add_badge("h", o.x + o.w, overlap_y, best_x, overlap_y, f"{card_gap} px")
            if best_x + moving.w + card_gap == o.x:
                add_badge("h", best_x + moving.w, overlap_y, o.x, overlap_y, f"{card_gap} px")

        # Căn thẳng Y
        if best_y == o.y:
            add_guide("h", o.y, min(best_x, o.x) - 12, max(best_x + moving.w, o.x + o.w) + 12)
        if best_y + moving.h == o.y + o.h:
            add_guide("h", o.y + o.h, min(best_x, o.x) - 12, max(best_x + moving.w, o.x + o.w) + 12)
        if abs((best_y + moving.h / 2.0) - (o.y + o.h / 2.0)) <= 1.0:
            cy = round(o.y + o.h / 2.0)
            add_guide("h", cy, min(best_x, o.x) - 12, max(best_x + moving.w, o.x + o.w) + 12)

        # Khoảng cách dọc card_gap
        if _ranges_overlap(best_x, best_x + moving.w, o.x, o.x + o.w, padding=20):
            overlap_x = (max(best_x, o.x) + min(best_x + moving.w, o.x + o.w)) // 2
            if best_y == o.y + o.h + card_gap:
                add_badge("v", overlap_x, o.y + o.h, overlap_x, best_y, f"{card_gap} px")
            if best_y + moving.h + card_gap == o.y:
                add_badge("v", overlap_x, best_y + moving.h, overlap_x, o.y, f"{card_gap} px")

    return SnapResult(x=best_x, y=best_y, guides=tuple(guides), badges=tuple(badges))

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
import xml.etree.ElementTree as ET

from .board import Board, CardPlacement, PlacementKind
from .model import Direction

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

_CELL = 48
_MARGIN = 30
_HEADER = 58

_DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.NORTH: (0, -1),
    Direction.EAST: (1, 0),
    Direction.SOUTH: (0, 1),
    Direction.WEST: (-1, 0),
}


def _tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def _svg_point(
    x: float,
    y: float,
    *,
    min_x: int,
    min_y: int,
) -> tuple[float, float]:
    return (
        _MARGIN + (x - min_x) * _CELL,
        _HEADER + _MARGIN + (y - min_y) * _CELL,
    )


def _perimeter_path(
    placement: CardPlacement,
    *,
    min_x: int,
    min_y: int,
) -> str:
    cells = set(placement.cells)
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for x, y in sorted(cells, key=lambda item: (item[1], item[0])):
        if (x, y - 1) not in cells:
            segments.append(((x, y), (x + 1, y)))
        if (x + 1, y) not in cells:
            segments.append(((x + 1, y), (x + 1, y + 1)))
        if (x, y + 1) not in cells:
            segments.append(((x, y + 1), (x + 1, y + 1)))
        if (x - 1, y) not in cells:
            segments.append(((x, y), (x, y + 1)))

    commands: list[str] = []
    for start, end in segments:
        sx, sy = _svg_point(*start, min_x=min_x, min_y=min_y)
        ex, ey = _svg_point(*end, min_x=min_x, min_y=min_y)
        commands.append(f"M {sx:g} {sy:g} L {ex:g} {ey:g}")
    return " ".join(commands)


def _placement_label(placement: CardPlacement) -> str:
    rotation = f"r{placement.quarter_turns}"
    if placement.kind is PlacementKind.START:
        return f"START {rotation}"
    if placement.kind is PlacementKind.EXIT:
        return f"EXIT {rotation}"
    return f"p{placement.placement_index} {rotation}"


def render_board_svg(
    board: Board,
    *,
    metadata: Mapping[str, object] | None = None,
) -> str:
    """Render one final board as dependency-free standalone SVG."""
    cells = board.cells
    placements = board.placements
    all_coords = set(cells)
    for placement in placements:
        all_coords.update(placement.cells)
    if not all_coords:
        raise ValueError("cannot render an empty board")

    min_x = min(x for x, _ in all_coords)
    max_x = max(x for x, _ in all_coords)
    min_y = min(y for _, y in all_coords)
    max_y = max(y for _, y in all_coords)

    width = (max_x - min_x + 1) * _CELL + 2 * _MARGIN
    height = (max_y - min_y + 1) * _CELL + 2 * _MARGIN + _HEADER

    payload: dict[str, object] = {
        "final_open_tunnels": board.open_tunnels,
        "final_visible_water": board.visible_water_cells,
        "placement_count": len(placements),
    }
    if metadata:
        payload.update(metadata)

    root = ET.Element(
        _tag("svg"),
        {
            "version": "1.1",
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
            "data-renderer": "bandido-alcatraz-final-board-v1",
            "data-open-tunnels": str(board.open_tunnels),
            "data-visible-water": str(board.visible_water_cells),
        },
    )
    title_bits = [
        str(payload[key])
        for key in ("experiment", "game_index", "seed")
        if key in payload
    ]
    ET.SubElement(root, _tag("title")).text = (
        "Bandido: Alcatraz final board"
        + (f" — {' / '.join(title_bits)}" if title_bits else "")
    )
    ET.SubElement(root, _tag("metadata")).text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    summary = ET.SubElement(
        root,
        _tag("text"),
        {
            "x": str(_MARGIN),
            "y": "20",
            "font-size": "12",
            "font-family": "monospace",
            "data-role": "summary",
        },
    )
    outcome = payload.get("outcome", "")
    summary.text = (
        f"{payload.get('experiment', 'board')} "
        f"game={payload.get('game_index', '?')} "
        f"seed={payload.get('seed', '?')} "
        f"{outcome} turns={payload.get('turns', '?')} "
        f"open={board.open_tunnels} water={board.visible_water_cells}"
    ).strip()

    legend = ET.SubElement(
        root,
        _tag("text"),
        {
            "x": str(_MARGIN),
            "y": "40",
            "font-size": "10",
            "font-family": "sans-serif",
            "data-role": "legend",
        },
    )
    legend.text = (
        "START/EXIT labels; r0..r3=quarter turns; dashed=water overlap; "
        "red ring=open end; black center dot=dead end; W=visible water"
    )

    cells_group = ET.SubElement(root, _tag("g"), {"id": "visible-cells"})
    for (x, y), cell in sorted(cells.items(), key=lambda item: (item[0][1], item[0][0])):
        px, py = _svg_point(x, y, min_x=min_x, min_y=min_y)
        attributes = {
            "x": f"{px:g}",
            "y": f"{py:g}",
            "width": str(_CELL),
            "height": str(_CELL),
            "fill": "#d8efff" if cell.water else "#ffffff",
            "stroke": "#c6c6c6",
            "stroke-width": "1",
            "class": "cell water" if cell.water else "cell land",
            "data-coord": f"{x},{y}",
        }
        ET.SubElement(cells_group, _tag("rect"), attributes)
        if cell.water:
            water_label = ET.SubElement(
                cells_group,
                _tag("text"),
                {
                    "x": f"{px + 4:g}",
                    "y": f"{py + 12:g}",
                    "font-size": "10",
                    "font-family": "sans-serif",
                    "data-marker": "visible-water",
                },
            )
            water_label.text = "W"

    tunnels_group = ET.SubElement(root, _tag("g"), {"id": "tunnels"})
    for (x, y), cell in sorted(cells.items(), key=lambda item: (item[0][1], item[0][0])):
        cx, cy = _svg_point(x + 0.5, y + 0.5, min_x=min_x, min_y=min_y)
        for edge in sorted(cell.tunnel_edges, key=lambda item: item.value):
            dx, dy = _DELTAS[edge]
            ex, ey = _svg_point(
                x + 0.5 + dx * 0.5,
                y + 0.5 + dy * 0.5,
                min_x=min_x,
                min_y=min_y,
            )
            ET.SubElement(
                tunnels_group,
                _tag("line"),
                {
                    "x1": f"{cx:g}",
                    "y1": f"{cy:g}",
                    "x2": f"{ex:g}",
                    "y2": f"{ey:g}",
                    "stroke": "#222222",
                    "stroke-width": "5",
                    "stroke-linecap": "round",
                    "data-tunnel-edge": edge.value,
                    "data-coord": f"{x},{y}",
                },
            )
            neighbor = (x + dx, y + dy)
            if neighbor not in cells:
                ET.SubElement(
                    tunnels_group,
                    _tag("circle"),
                    {
                        "cx": f"{ex:g}",
                        "cy": f"{ey:g}",
                        "r": "5",
                        "fill": "#ffffff",
                        "stroke": "#c62828",
                        "stroke-width": "2",
                        "data-marker": "open-end",
                        "data-target": f"{neighbor[0]},{neighbor[1]}",
                    },
                )
        if len(cell.tunnel_edges) == 1:
            ET.SubElement(
                tunnels_group,
                _tag("circle"),
                {
                    "cx": f"{cx:g}",
                    "cy": f"{cy:g}",
                    "r": "4",
                    "fill": "#111111",
                    "data-marker": "dead-end",
                    "data-coord": f"{x},{y}",
                },
            )

    placements_group = ET.SubElement(root, _tag("g"), {"id": "card-placements"})
    for placement in placements:
        group = ET.SubElement(
            placements_group,
            _tag("g"),
            {
                "class": f"card-placement {placement.kind.value}",
                "data-placement-index": str(placement.placement_index),
                "data-card-id": placement.card_id,
                "data-kind": placement.kind.value,
                "data-origin": f"{placement.origin[0]},{placement.origin[1]}",
                "data-quarter-turns": str(placement.quarter_turns),
                "data-overlap": "true" if placement.overlaps else "false",
            },
        )
        path_attrs = {
            "d": _perimeter_path(placement, min_x=min_x, min_y=min_y),
            "fill": "none",
            "stroke": (
                "#1976d2"
                if placement.kind is PlacementKind.START
                else "#ef6c00"
                if placement.kind is PlacementKind.EXIT
                else "#111111"
            ),
            "stroke-width": "2.5",
            "stroke-linejoin": "round",
            "data-role": "card-boundary",
        }
        if placement.overlaps:
            path_attrs["stroke-dasharray"] = "7 4"
        ET.SubElement(group, _tag("path"), path_attrs)

        center_x = sum(x + 0.5 for x, _ in placement.cells) / len(placement.cells)
        center_y = sum(y + 0.5 for _, y in placement.cells) / len(placement.cells)
        lx, ly = _svg_point(center_x, center_y, min_x=min_x, min_y=min_y)
        label = ET.SubElement(
            group,
            _tag("text"),
            {
                "x": f"{lx:g}",
                "y": f"{ly + 3:g}",
                "font-size": "8",
                "font-family": "monospace",
                "text-anchor": "middle",
                "data-role": "card-label",
            },
        )
        label.text = _placement_label(placement)

        for overlap in placement.overlaps:
            ox, oy = _svg_point(*overlap, min_x=min_x, min_y=min_y)
            ET.SubElement(
                group,
                _tag("rect"),
                {
                    "x": f"{ox + 3:g}",
                    "y": f"{oy + 3:g}",
                    "width": str(_CELL - 6),
                    "height": str(_CELL - 6),
                    "fill": "none",
                    "stroke": "#7b1fa2",
                    "stroke-width": "2",
                    "stroke-dasharray": "4 3",
                    "data-marker": "water-overlap",
                    "data-covered-placement-index": (
                        ""
                        if placement.covered_placement_index is None
                        else str(placement.covered_placement_index)
                    ),
                },
            )
            ET.SubElement(
                group,
                _tag("line"),
                {
                    "x1": f"{ox + 6:g}",
                    "y1": f"{oy + 6:g}",
                    "x2": f"{ox + _CELL - 6:g}",
                    "y2": f"{oy + _CELL - 6:g}",
                    "stroke": "#7b1fa2",
                    "stroke-width": "1.5",
                    "data-marker": "water-overlap-cross",
                },
            )
            ET.SubElement(
                group,
                _tag("line"),
                {
                    "x1": f"{ox + _CELL - 6:g}",
                    "y1": f"{oy + 6:g}",
                    "x2": f"{ox + 6:g}",
                    "y2": f"{oy + _CELL - 6:g}",
                    "stroke": "#7b1fa2",
                    "stroke-width": "1.5",
                    "data-marker": "water-overlap-cross",
                },
            )

    return ET.tostring(root, encoding="unicode") + "\n"


def write_board_svg(
    board: Board,
    path: str | Path,
    *,
    metadata: Mapping[str, object] | None = None,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        render_board_svg(board, metadata=metadata),
        encoding="utf-8",
    )
    return destination

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .model import CardDefinition
from .proxy import card_from_port_geometry


@dataclass(frozen=True, slots=True)
class ProxyStatus:
    total_slots: int
    transcribed_slots: int
    remaining_slots: int
    end_slots: int
    transcribed_end_slots: int
    basic_slots: int
    transcribed_basic_slots: int
    complete_geometry: bool


def load_proxy(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def proxy_status(data: dict[str, Any]) -> ProxyStatus:
    slots = data["slots"]
    end_slots = [slot for slot in slots if slot["kind"] == "end"]
    basic_slots = [slot for slot in slots if slot["kind"] == "basic"]
    transcribed = [slot for slot in slots if slot["geometry"] is not None]

    return ProxyStatus(
        total_slots=len(slots),
        transcribed_slots=len(transcribed),
        remaining_slots=len(slots) - len(transcribed),
        end_slots=len(end_slots),
        transcribed_end_slots=sum(
            slot["geometry"] is not None for slot in end_slots
        ),
        basic_slots=len(basic_slots),
        transcribed_basic_slots=sum(
            slot["geometry"] is not None for slot in basic_slots
        ),
        complete_geometry=bool(data["complete_geometry"]),
    )


def compile_proxy_deck(data: dict[str, Any]) -> list[CardDefinition]:
    status = proxy_status(data)
    if not status.complete_geometry:
        raise ValueError(
            "proxy geometry is incomplete: "
            f"{status.transcribed_slots}/{status.total_slots} slots transcribed"
        )
    if status.remaining_slots:
        raise ValueError("complete_geometry=true but some slots are untranscribed")

    return [
        card_from_port_geometry(
            slot["id"],
            external_ports=slot["geometry"]["external_ports"],
            internal_bridge=slot["geometry"]["internal_bridge"],
        )
        for slot in data["slots"]
    ]

#!/usr/bin/env python3
"""Select a proposed mixed-action spent-state corpus; never run a game or policy.

Standard-library only. The corpus contains detached public observations only.
The proposal is not a frozen research protocol until separately preregistered.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import io
import hashlib
import json
from pathlib import Path
import zipfile


SOURCE_SHA256 = "48e6af6595a737be332467b436aca94744b19c4b3d96d25d5dbbfe654d98a4b2"
SOURCE_BYTES = 24204721
RECEIPT_SHA256 = "699ae3c4bfe9fb1d7b0009a816ce72cc2557577797c0c6712b2a35f4856339d4"
LABEL = "mixed-action-two-action-diagnostic-v1"
EXCLUSION_MANIFEST_SHA256 = "e5b672d3a97efa72abdc7f32e70a8eb50a3afb8d4813d81ddf4efd3479973410"
EXCLUSION_MANIFEST_BYTES = 63959
EXCLUSION_IDENTITIES_SHA256 = "f430f67e6c7e6773d5309c0278167448a5f07b00b879a847d66421d1276e5a70"
EXPECTED_SOURCE_DECISIONS = 21221
EXPECTED_SOURCE_MIXED = 1984
EXPECTED_ELIGIBLE = 1981
SEEDS = range(1000000, 1000400)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(data):
    def bad_constant(value):
        raise ValueError(f"non-finite JSON value: {value}")
    return json.loads(data, object_pairs_hook=unique_object,
                      parse_constant=bad_constant)


def exact_keys(value, keys, location):
    if type(value) is not dict or set(value) != set(keys.split()):
        raise ValueError(f"unexpected fields at {location}")


def integer(value, location, minimum=None):
    if type(value) is not int or (minimum is not None and value < minimum):
        raise ValueError(f"invalid integer at {location}")


def boolean(value, location):
    if type(value) is not bool:
        raise ValueError(f"invalid boolean at {location}")


def coordinate(value, location):
    if type(value) is not list or len(value) != 2:
        raise ValueError(f"invalid coordinate at {location}")
    for item in value:
        integer(item, location)


def cell(value, location):
    exact_keys(value, "x y tunnel_edges water", location)
    integer(value["x"], location)
    integer(value["y"], location)
    boolean(value["water"], location)
    edges = value["tunnel_edges"]
    if (type(edges) is not list or any(x not in ("N", "E", "S", "W") for x in edges)
            or edges != sorted(set(edges))):
        raise ValueError(f"invalid tunnel edges at {location}")


def card(value, location):
    exact_keys(value, "card_id cells is_exit material", location)
    if type(value["card_id"]) is not str:
        raise ValueError(f"invalid card ID at {location}")
    boolean(value["is_exit"], location)
    if value["material"] not in (None, "raincoat", "rope"):
        raise ValueError(f"invalid material at {location}")
    if type(value["cells"]) is not list:
        raise ValueError(f"invalid cells at {location}")
    for item in value["cells"]:
        cell(item, location + ".cells")


def validate_observation(value):
    """Whitelist the exact serialized PlayerObservation, recursively."""
    exact_keys(value, "board hand raincoats ropes exit_placed exit_seen turns "
               "set_aside_unplayable collected_equipment setup player_index", "observation")
    for name in ("raincoats", "ropes", "turns", "set_aside_unplayable", "player_index"):
        integer(value[name], name, 0)
    if value["raincoats"] > 3 or value["ropes"] > 2 or value["player_index"] != 0:
        raise ValueError("unexpected quota/player observation")
    for name in ("exit_placed", "exit_seen"):
        boolean(value[name], name)
    exact_keys(value["setup"], "hand_size player_count start_side starting_player", "setup")
    if value["setup"] != {"hand_size": 6, "player_count": 1,
                           "start_side": "easy-5-exit", "starting_player": 0}:
        raise ValueError("unexpected setup")
    exact_keys(value["board"], "cells placements", "board")
    if type(value["board"]["cells"]) is not list or type(value["board"]["placements"]) is not list:
        raise ValueError("invalid board lists")
    for item in value["board"]["cells"]:
        cell(item, "board.cells")
    for item in value["board"]["placements"]:
        exact_keys(item, "card_id cells covered_placement_index kind origin overlaps "
                   "placement_index quarter_turns", "board.placements")
        if type(item["card_id"]) is not str or item["kind"] not in ("start", "ordinary", "exit"):
            raise ValueError("invalid placement identity/kind")
        integer(item["placement_index"], "placement_index", 0)
        integer(item["quarter_turns"], "quarter_turns", 0)
        if item["quarter_turns"] > 3:
            raise ValueError("invalid quarter_turns")
        if item["covered_placement_index"] is not None:
            integer(item["covered_placement_index"], "covered_placement_index", 0)
        coordinate(item["origin"], "origin")
        for name in ("cells", "overlaps"):
            if type(item[name]) is not list:
                raise ValueError("invalid placement coordinates")
            for coord in item[name]:
                coordinate(coord, name)
    if type(value["hand"]) is not list or type(value["collected_equipment"]) is not list:
        raise ValueError("invalid observation lists")
    for item in value["hand"]:
        card(item, "hand")
    for item in value["collected_equipment"]:
        exact_keys(item, "card turn player_index", "collected_equipment")
        integer(item["turn"], "collected_equipment.turn", 1)
        integer(item["player_index"], "collected_equipment.player_index", 0)
        card(item["card"], "collected_equipment.card")


def action_counts(observation, branching):
    """Public material/quota arithmetic only; no model or legal-list call."""
    integer(branching, "B", 0)
    raincoats, ropes = observation["raincoats"], observation["ropes"]
    integer(raincoats, "raincoats", 0)
    integer(ropes, "ropes", 0)
    if raincoats > 3 or ropes > 2:
        raise ValueError("quota overflow")
    collect = sum((c["material"] == "raincoat" and raincoats < 3)
                  or (c["material"] == "rope" and ropes < 2)
                  for c in observation["hand"])
    if collect > branching:
        raise ValueError("metadata COLLECT count exceeds recorded B")
    place = branching - collect
    action_class = ("mixed" if collect and place else "collect_only" if collect
                    else "place_only" if place else "none")
    return collect, place, action_class


def load_exclusion_manifest(path):
    raw = Path(path).read_bytes()
    if len(raw) != EXCLUSION_MANIFEST_BYTES or digest(raw) != EXCLUSION_MANIFEST_SHA256:
        raise ValueError("pinned Worker32 exclusion manifest mismatch")
    manifest = read_json(raw)
    pairs = sorted([[x["seed"], x["ordinal"]] for x in manifest["entries"]])
    identities = {tuple(x) for x in pairs}
    if (len(pairs) != 80 or len(identities) != 80
            or digest(canonical(pairs)) != EXCLUSION_IDENTITIES_SHA256):
        raise ValueError("pinned Worker32 exclusion identities mismatch")
    return raw, identities


def exclusion_reason(metadata, old_ids):
    if metadata["collect_count_metadata"] <= 0 or metadata["place_count_metadata"] <= 0:
        return "not_mixed_collect_place"
    if (metadata["seed"], metadata["ordinal"]) in old_ids:
        return "previous_worker32_mixed_identity"
    return None


def select_metadata(metadata):
    identities = [(x["seed"], x["ordinal"]) for x in metadata]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate eligible identity")
    if any(x["collect_count_metadata"] <= 0 or x["place_count_metadata"] <= 0 for x in metadata):
        raise ValueError("nonmixed item in eligible pool")
    by_hash = sorted(metadata, key=lambda x: (x["selection_key_sha256"], x["seed"], x["ordinal"]))[:64]
    hash_ids = {(x["seed"], x["ordinal"]) for x in by_hash}
    by_stress = sorted((x for x in metadata if (x["seed"], x["ordinal"]) not in hash_ids),
                       key=lambda x: (-x["stress_cost_proxy"], x["seed"], x["ordinal"]))[:16]
    selected = [{**x, "group": "hash64"} for x in by_hash] + [{**x, "group": "stress16"} for x in by_stress]
    if len(selected) != 80 or len({(x["seed"], x["ordinal"]) for x in selected}) != 80:
        raise ValueError("selection cardinality mismatch")
    return selected


def deterministic_gzip(raw):
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0, compresslevel=9) as stream:
        stream.write(raw)
    return output.getvalue()


def trace_name(seed):
    return f"decision-traces/pass-2/{seed}.jsonl"


def state_records(archive, seed, include_audit_reference=False, audit_reference_ids=None):
    """Yield only observations and selection metadata, ignoring other payloads."""
    pending = None
    ordinal = 0
    with archive.open(trace_name(seed)) as stream:
        for line in stream:
            row = read_json(line)
            event = row["event"]
            if event == "decision_started":
                if pending is not None or row["ordinal"] != ordinal + 1:
                    raise ValueError("unpaired or unordered decision_started")
                validate_observation(row["observation"])
                pending = row["observation"]
                ordinal += 1
            elif event == "decision_completed":
                if pending is None or row["ordinal"] != ordinal:
                    raise ValueError("unpaired decision_completed")
                audit = row["audit"]
                observation_sha = digest(canonical(pending))
                if audit["public_observation_sha256"] != observation_sha:
                    raise ValueError("observation digest mismatch")
                branching = audit["legal_move_count"]
                integer(branching, "legal_move_count", 0)
                cells = len(pending["board"]["cells"])
                collect, place, action_class = action_counts(pending, branching)
                key_input = f"{LABEL}|{seed}|{ordinal}|{observation_sha}"
                metadata = {
                    "seed": seed, "ordinal": ordinal, "B": branching, "C": cells,
                    "collect_count_metadata": collect, "place_count_metadata": place,
                    "action_type_class": action_class,
                    "public_observation_sha256": observation_sha,
                    "selection_key_input": key_input,
                    "selection_key_sha256": digest(key_input.encode("utf-8")),
                    "stress_cost_proxy": branching * (branching + 1) * cells,
                }
                reference = None
                if include_audit_reference and (audit_reference_ids is None or (seed, ordinal) in audit_reference_ids):
                    primary = audit["primary_tier"]
                    if digest(canonical(primary)) != audit["primary_tier_sha256"]:
                        raise ValueError("source primary-tier digest mismatch")
                    reference = {
                        "legal_move_count": branching,
                        "primary_tier": primary,
                        "primary_tier_sha256": audit["primary_tier_sha256"],
                        "primary_score": audit["primary_score"],
                    }
                yield metadata, pending, reference
                pending = None
            elif event not in ("game_returned", "game_completed"):
                raise ValueError(f"unexpected trace event {event}")
            elif pending is not None:
                raise ValueError("game event inside pending decision")
    if pending is not None:
        raise ValueError("unterminated decision")


def write_unchanged_or_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"refusing to overwrite different existing output: {path}")
        return
    with path.open("xb") as stream:
        stream.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--excluded-manifest", type=Path, required=True)
    args = parser.parse_args()
    archive_hash = hashlib.sha256()
    with args.archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            archive_hash.update(block)
    if archive_hash.hexdigest() != SOURCE_SHA256 or args.archive.stat().st_size != SOURCE_BYTES:
        raise ValueError("source archive bytes do not match the accepted Worker31 artifact")

    exclusion_bytes, exclusion_ids = load_exclusion_manifest(args.excluded_manifest)
    all_metadata, excluded = [], []
    source_classes = Counter()
    matched_old_ids = set()
    with zipfile.ZipFile(args.archive) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate archive members")
        if {n for n in names if n.startswith("decision-traces/pass-2/")} != {
                trace_name(seed) for seed in SEEDS}:
            raise ValueError("unexpected candidate trace population")
        receipt_bytes = archive.read("receipt.json")
        if digest(receipt_bytes) != RECEIPT_SHA256:
            raise ValueError("source receipt hash mismatch")
        receipt = read_json(receipt_bytes)
        if (receipt["run_id"] != "36848990406" or receipt["run_attempt"] != "1"
                or receipt["expected_head"] != "7a2b681f2d78c9e4cef466eb5250c4bd6c6c52ed"):
            raise ValueError("source receipt provenance mismatch")
        for seed in SEEDS:
            for metadata, _, _ in state_records(archive, seed):
                source_classes[metadata["action_type_class"]] += 1
                identity = (metadata["seed"], metadata["ordinal"])
                if identity in exclusion_ids:
                    matched_old_ids.add(identity)
                reason = exclusion_reason(metadata, exclusion_ids)
                if reason is not None:
                    excluded.append({**metadata, "exclusion_reason": reason,
                                     "in_previous_worker32_identity_set": identity in exclusion_ids})
                else:
                    all_metadata.append(metadata)
        if (sum(source_classes.values()) != EXPECTED_SOURCE_DECISIONS
                or source_classes["mixed"] != EXPECTED_SOURCE_MIXED
                or len(all_metadata) != EXPECTED_ELIGIBLE
                or matched_old_ids != exclusion_ids):
            raise ValueError("source eligibility/exclusion population mismatch")
        selected = select_metadata(all_metadata)
        selected_ids = {(x["seed"], x["ordinal"]) for x in selected}
        observations = {}
        audit_references = {}
        member_digests = {}
        for seed in sorted({x["seed"] for x in selected}):
            member_digests[trace_name(seed)] = digest(archive.read(trace_name(seed)))
            for metadata, observation, reference in state_records(archive, seed, include_audit_reference=True, audit_reference_ids=selected_ids):
                identity = (seed, metadata["ordinal"])
                if identity in selected_ids:
                    observations[identity] = observation
                    audit_references[identity] = reference

    outputs = {"worker32-exclusion-manifest.json": exclusion_bytes,
               "worker32-exclusion-identities.json": canonical(sorted([list(x) for x in exclusion_ids]))}
    corpus = bytearray()
    entries = []
    reference_rows = []
    for position, metadata in enumerate(selected, 1):
        identity = (metadata["seed"], metadata["ordinal"])
        data = canonical(observations[identity])
        if digest(data) != metadata["public_observation_sha256"]:
            raise ValueError("selected observation readback mismatch")
        filename = f"snapshots/{position:03d}-seed-{identity[0]}-ordinal-{identity[1]:03d}.json"
        outputs[filename] = data
        corpus.extend(data)
        entries.append({**metadata, "position": position, "snapshot_file": filename,
                        "snapshot_sha256": digest(data), "snapshot_size_bytes": len(data),
                        "source_trace_member": trace_name(identity[0]),
                        "source_trace_sha256": member_digests[trace_name(identity[0])]})
        reference_rows.append({"position": position, "seed": identity[0], "ordinal": identity[1],
                               "public_observation_sha256": metadata["public_observation_sha256"],
                               **audit_references[identity]})

    outputs["selected-corpus.jsonl"] = bytes(corpus)
    outputs["audit-reference.jsonl"] = b"".join(canonical(x) for x in reference_rows)
    outputs["selected-corpus.jsonl.gz"] = deterministic_gzip(outputs["selected-corpus.jsonl"])
    outputs["eligible-index.jsonl"] = b"".join(canonical(x) for x in all_metadata)
    outputs["excluded-index.jsonl"] = b"".join(canonical(x) for x in excluded)
    manifest = {
        "schema": "worker33-mixed-public-state-selection-preparation-v1",
        "status": "preparation_only_not_preregistered_or_execution_authority",
        "no_policy_search_or_game_execution": True,
        "canonical_source_accepted_main": "c50a7ab8e73eaf3c497c5d1c9fef5cbe53261853",
        "execution_prerequisite": "Separate prospective protocol and exact-head freeze after Worker32 closure as resource_incomplete; this preparation authorizes no execution",
        "new_seeds_or_games_allocated": 0,
        "candidate_core_constraint": {
            "reference_execution_head": "d21421e883cbc08d3a9e99ea8d856894c6ac41a8",
            "candidate_sha256": "d806a40383566d82f8af4259179940feff0339ac786bcf6207e7f7e0503e1b01",
            "reference_sha256": "2a396aed1e303332d72b254f30dd58b57133364eafa29e50c5a51807f892e20b",
            "meaning": "Existing exhaustive two-action candidate/reference/H are unchanged; no gated-policy wrapper or games in this diagnostic"
        },
        "previous_worker32_exclusion": {
            "file": "worker32-exclusion-manifest.json",
            "manifest_sha256": EXCLUSION_MANIFEST_SHA256,
            "manifest_size_bytes": EXCLUSION_MANIFEST_BYTES,
            "identities_file": "worker32-exclusion-identities.json",
            "identities_encoding": "canonical JSON of sorted [seed, ordinal] pairs, exactly one trailing newline",
            "identities_sha256": EXCLUSION_IDENTITIES_SHA256,
            "identity_count": 80,
            "source_matched_identity_count": len(matched_old_ids),
            "mixed_identity_count_removed": EXPECTED_SOURCE_MIXED - len(all_metadata),
            "effect": "Distinct observation coverage only; all source trajectories/cohorts remain permanently spent"
        },
        "selector_script": "select_public_snapshots.py",
        "selector_script_sha256": digest(Path(__file__).read_bytes()),
        "source": {
            "repository": "carabinshely/bandido-alcatraz-solve", "worker": 31,
            "archive_sha256": SOURCE_SHA256, "archive_size_bytes": SOURCE_BYTES,
            "artifact_id": 11156427816, "receipt_sha256": RECEIPT_SHA256,
            "run_id": 36848990406, "run_attempt": 1,
            "run_url": "https://github.com/carabinshely/bandido-alcatraz-solve/actions/runs/36848990406",
            "execution_head": "7a2b681f2d78c9e4cef466eb5250c4bd6c6c52ed",
            "execution_tree": "dc073c8484beef1f63734f177790ca46f1331a67",
            "phase": 2, "phase_identity": "candidate", "seed_start": 1000000, "seed_end": 1000399,
            "ruleset_id": "v2-exact-equipment-quota-limited-collect-full-hand-refresh",
            "setup_id": "p1-easy-5-exit-hand6-first0-full-hand-refresh",
            "public_observation_game_source_blob": "8df56288eded0ae96c57314589a9707b4a056054",
            "public_serializer_candidate_blob": "3c10b6253ab272fa0b91a8ef967a7c03b9939538",
            "worker31_preregistration_url": "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5928556762",
        },
        "selection": {
            "label": LABEL, "hash_encoding": "UTF-8 without trailing newline",
            "hash_input": "label|seed_decimal|ordinal_decimal|public_observation_sha256",
            "B_definition": "candidate audit legal_move_count; no scorer or legal enumeration is invoked",
            "C_definition": "length of decision_started.observation.board.cells",
            "collect_count_definition": "One per public hand card whose material is raincoat with raincoats < 3, or rope with ropes < 2; metadata arithmetic only",
            "place_count_definition": "recorded B minus metadata COLLECT count; EXIT belongs to PLACE",
            "eligibility": "collect_count_metadata > 0 and place_count_metadata > 0, excluding every identity in the pinned original Worker32 set",
            "canonical_revalidation_required": "Runner must reconstruct observations and re-enumerate canonical roots/types, verify exact B and COLLECT/PLACE counts and source V4 score/tier before policy calls",
            "stress_cost_proxy": "B * (B + 1) * C; arithmetic only, not measured successor branching",
            "hash_group": "lowest 64 SHA256 keys; ties by ascending seed then ordinal",
            "stress_group": "highest 16 cost proxies among remaining states; ties by ascending seed then ordinal",
            "output_order": "hash64 ascending SHA256,seed,ordinal; then stress16 descending cost,ascending seed,ordinal",
            "exclusion": "Not mixed COLLECT+PLACE, then pinned Worker32 identity set; no outcome, chosen action, score, gain/loss, departure, or terminal-result filter",
            "selected_count": 80, "hash_group_count": 64, "stress_group_count": 16,
            "source_seed_count": 400, "source_decision_count": len(all_metadata) + len(excluded),
            "eligible_count": len(all_metadata), "excluded_count": len(excluded),
            "source_action_type_counts": dict(sorted(source_classes.items())),
            "exclusion_reason_counts": dict(sorted(Counter(x["exclusion_reason"] for x in excluded).items())),
            "selected_proxy_sum": sum(x["stress_cost_proxy"] for x in selected),
            "hash64_proxy_sum": sum(x["stress_cost_proxy"] for x in selected if x["group"] == "hash64"),
            "stress16_proxy_sum": sum(x["stress_cost_proxy"] for x in selected if x["group"] == "stress16"),
            "selected_distinct_seed_count": len({x["seed"] for x in selected}),
        },
        "observation_contract": {
            "format": "Each snapshot JSON and each corpus JSONL row is exactly one serialized PlayerObservation, without an envelope",
            "fields": sorted(observations[next(iter(observations))]),
            "board": "public visible cells and public placement history only",
            "hand": "acting player's own visible card definitions only",
            "collected_equipment": "public collected card, one-based action turn, player index",
            "set_aside_unplayable": "public count only; no private identities",
            "exit_seen": "acting player's knowledge in the canonical solo setup",
            "excluded_payloads": "No audit tier/scores/chosen move/RNG hash, game result, draw pile, other player's hand, or private set-aside identities",
            "canonical_encoding": "sorted-key compact ensure_ascii JSON, finite numbers only, UTF-8, exactly one trailing newline",
        },
        "audit_reference_contract": {
            "file": "audit-reference.jsonl",
            "purpose": "Before candidate execution, independently regenerate unchanged canonical roots and action-type counts, require mixed eligibility, and match source B, ordered V4 maximal tier, tier digest and score exactly",
            "is_policy_input": False,
            "affects_selection": False,
            "mismatch_action": "integrity_invalid; do not substitute snapshots",
            "excluded": "No chosen action, narrowed tier, opportunity score, RNG state hash, or game outcome",
        },
        "files": {name: {"sha256": digest(data), "size_bytes": len(data)}
                  for name, data in outputs.items() if not name.startswith("snapshots/")},
        "entries": entries,
    }
    outputs["selection-manifest.json"] = canonical(manifest)
    for name, data in outputs.items():
        write_unchanged_or_new(args.output_dir / name, data)
    print(json.dumps({"source_zip_verified": True, "selected": 80,
                      "source_decisions": manifest["selection"]["source_decision_count"],
                      "eligible": len(all_metadata), "excluded": len(excluded),
                      "corpus_sha256": digest(bytes(corpus)),
                      "corpus_size_bytes": len(corpus),
                      "manifest_sha256": digest(outputs["selection-manifest.json"]),
                      "output_dir": str(args.output_dir)}, sort_keys=True))


if __name__ == "__main__":
    main()

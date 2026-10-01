# Canonical exact-equipment model and setup migration

> **Historical model (superseded).** This document preserves the v1 decision, including its now-rejected unrestricted COLLECT interpretation. The current canonical rules are [modeling-v2](modeling-v2.md); do not use this document as current legality or baseline authority.

Authority: Issues #26, #27, #28 and Issue #2's 2026-10-01 migration receipt.
Ruleset ID: `v1-exact-equipment-full-hand-refresh`.

## Invariant rules and explicit interpretation

Victory requires exactly three collected raincoats and two ropes, EXIT placed,
no other open tunnel, and no visible water. COLLECT remains legal beyond quota:
the publisher describes an unrestricted material-collection action and an exact
end condition. Thus overshoot is legal but cannot yield victory. This reading is
not an additional publisher FAQ. Collected cards cannot return to tunnel play.

Official source: https://fractaljuegos.com/wp-content/uploads/2026/04/BandidoAlcatraz_Rules_Fractal_WEB.pdf
The general no-play text describes returning three cards to the pile bottom and
replacing them; with three or fewer remaining, take those and set the old hand
aside. Solo changes the starting hand to six (easy) or three (advanced), without
an explicit replacement-batch clarification.

The owner selected replacing the **entire current hand**, including six-card
solo. Extend the short-pile boundary to that current replacement batch size.
This is a project interpretation, not a verbatim publisher clarification.
Refresh consumes no action/turn and uses no RNG. Return the old hand in its
existing order to the bottom; normal replacement draws pop from the list end.
A short pile is copied in existing internal order, retaining the established
engine convention. Neither ordering convention is a publisher assertion.

Deck transcription, placement, water, EXIT geometry, shuffle and canonical move
ordering are unchanged. Historical artifacts are not rewritten.

## Orthogonal setup

`GameSetup` validates player count 1–4, `StartSide`, hand size and starting-player
index. Solo hand sizes are 3 or 6; multiplayer configuration requires 3 per
player. START side is independent. IDs are derived from all setup dimensions.
`RealDeck.start_for_setup(setup)` selects the physical START definition.
Initial research uses `GameSetup()` (solo, five exits, six cards).
Strategy is not part of setup. No empirical ordering between six-exit/six-card
and five-exit/three-card is assumed.

This bounded migration executes **solo only**. A multiplayer setup is valid
configuration but raises `NotImplementedError` before simulation. Issue #27 must
add separate hands, active-player turns and blocked-player handling before
multiplayer execution. Do not combine private hands or reuse solo deadlock logic
as a team termination rule. Starting-player selection then follows the supplied
clockwise order with the youngest player mapped to the chosen index.

## Policy boundary and public equipment

The simulator passes a detached `PlayerObservation` containing a cloned public
board, own visible hand, public equipment counts/history, setup and turn data.
No draw pile exists on the observation. Policy-side mutation cannot change the
real board. No-draw previews preserve equipment history and never acquire hidden
cards. A terminal observation hook supports export even when the last action
ends the game.

`exit_seen` is own-player knowledge in this solo executor. A future multiplayer
observation must derive per-player knowledge and must not expose another
player's privately drawn EXIT via a global flag.

Each successful COLLECT appends immutable `CollectedEquipment(card, turn,
player_index)`, with the physical definition, material, ID and one-based action
index. Counts remain updated centrally by the action. Direct constructed test
states may supply initial counters without historical records; do not claim
those fixtures reconstruct unknown past identities. Fresh games start with zero
counts and empty history. Public collected geometry is legitimate strategy
input, but policy selection/tuning is outside this migration.

## History and research

Old manifests remain immutable records of the old threshold model. Named old
research entrypoints refuse to run under the new model; historical V7 rendering
requires checkout `f26781b87451ceb49069c29276d60e03b18ba0d7` and its provenance
checks. Old counters alone cannot reconstruct collected identities.
The old Worker28 protocol/PR25 remains superseded with zero V8 games.

Routine CI uses synthetic fixtures and the already-spent real smoke seeds0–19;
it is not a win-rate experiment. No fresh confirmation data is allocated here.
A current-model baseline must separately freeze exact source, policy, setup and
spent population before compute; only then may a new strategy be preregistered.

## Explicit zones before research resumes

The simulator retains a distinct hidden draw pile, separate `private_hands`,
public board placement history, public collected equipment, and a private
`face_down_set_aside` tuple. Short-pile refresh preserves the exact displaced
cards in that private zone rather than discarding their identities. Observations
expose only its count, never those card identities or other players' hands.
Synthetic conservation tests cover this boundary. `hand` remains the active
hand compatibility alias and refresh keeps it synchronized with its private slot.
Multiplayer state/observations can represent independent hands; multiplayer
application/refresh/simulation deliberately fail until the future turn engine
and per-player knowledge history are implemented. In those nonexecuting
multiplayer observations, private EXIT knowledge is computed from that player's
own hand, never the legacy solo-global history flag.

# Card analysis — working notes

Research date: 2026-09-21.

This file records only observations useful to the simulator. Unknown geometry or multiplicity stays unknown rather than being guessed.

## Confirmed aggregate facts

Publisher / regional publisher source:
https://fractaljuegos.com/en/juegos/bandido-alcatraz/

The ordinary deck contains 68 cards, including:

- 4 water cards;
- 8 rope cards;
- 12 raincoat cards.

There is also one double-sided start tile and one EXIT card. The EXIT card is shuffled into the draw pile.

Official rulebook:
https://fractaljuegos.cl/wp-content/uploads/2026/04/BandidoAlcatraz_Rules_Fractal_WEB.pdf

## Confirmed structural observations

The rulebook and available photographs support the following model:

1. Ordinary cards are rectangular tunnel cards that can be connected to the existing layout.
2. Equipment symbols occur on tunnel cards; choosing the material action removes that card from future tunnel use.
3. A review with original photography states that equipment symbols can occur both on ordinary paths and on barred dead-end cards.
4. Water cards are split: only the blue half must later be covered.
5. Covering water must reproduce the covered half's tunnel/earth pattern exactly and must keep all adjacent tunnel matches valid.
6. The whole water card may not be covered; only the blue half may overlap.
7. EXIT is held after drawing and may be placed later on a matching tunnel.
8. The start tile has an easy side with five tunnels and a normal side with six.

Review / original photography:
https://www.zestolu.cz/deskovky/bandido-alcatraz-recenze-dalsiho-nekompromisniho-hlavolamu-647188

Additional public gallery:
https://www.zatrolene-hry.cz/spolecenska-hra/bandido-alcatraz-20210/obrazky/?sort=date

BoardGameGeek component image:
https://boardgamegeek.com/image/9354426/bandido-alcatraz-10th-anniversary-edition

## Geometry representation chosen for the engine

To avoid baking in unverified card types, a card is represented as one or more unit cells. Each cell records:

- integer x/y position in the card footprint;
- which of N/E/S/W edges contain tunnel openings;
- whether that cell is the water-covered half.

This supports:

- horizontal and vertical rotations;
- half-card water overlap;
- exact tunnel/earth edge matching;
- a future multi-cell start tile;

without assuming the final Alcatraz card catalog.

Internal tunnel connectivity is deliberately not encoded yet because the available images have not been transcribed completely enough to prove every internal connection pattern.

## Original Bandido as reference, not data

Board Game Arena documents the original Bandido deck as 69 tunnel cards:

- 24 basic configurations, 2 copies each;
- 7 end configurations, 3 copies each.

Source:
https://en.doc.boardgamearena.com/Gamehelpbandido

This is useful for comparison because Alcatraz reimplements Bandido, but it is not imported as Alcatraz deck data.

## Current blocker for full Monte Carlo simulation

We still need the exact Alcatraz multiset:

- each distinct tunnel geometry;
- multiplicity of each geometry;
- which geometries carry rope/raincoat;
- exact geometry of all four water cards.

Until then, the engine can be implemented and tested generically, but any full-deck win rate would be provisional.

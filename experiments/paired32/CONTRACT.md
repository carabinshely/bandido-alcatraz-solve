# Paired32 public-turn closure — source-only protocol

Compare frozen V4-250 against one fixed candidate on twelve fresh paired seeds. The candidate preserves every V4-250 feature and weight except `delta_open_tunnels`: its weight is 100 before public turn 20 and 5000 from turn 20 onward. Immediate wins and the nonwinning last-closure penalty remain unchanged. The policy sees only the public board, public turn count, and its own visible hand. Both arms use the unchanged solo easy5, hand6, real 69-card deck and actual engine win condition.

The choice is developmental. In paired31, most long losses exhausted the deck with many open tunnels; paired31 itself changed one choice in twelve pairs and won zero. An earlier +900 late-closure candidate changed 13 choices in eight pairs but yielded only 2/8 wins versus 1/8 control, exact p=1. Those spent trajectories motivated this stronger fixed weight; they do not predict improvement.

Seeds 1000527–1000538 are proposed and **not allocated**. Exactly twelve pairs run in ascending order, control then candidate per seed. The complete table reports wins by arm, paired discordance, exact two-sided binomial p, candidate choice changes, late-phase decisions, terminal reasons/open tunnels, operations, and runtime. Partial results have no twelve-pair verdict. There is no retry, replacement, suffix resume, extension, or outcome-selected stopping. A favorable developmental screen still needs untouched preregistered confirmation and independent fresh replication before adoption.

Only the admitted `bandido-alcatraz-ci` workflow may run games after exact source, runner, ownership, resource, issuance, review, and root GO checks. Narrow synthetic tests grant no execution or efficacy authority.

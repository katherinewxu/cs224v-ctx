| run | rounds | compactions | rounds with a compaction | memory read before next compaction | median calls to first memory read | proposed before reading memory | repeats | repeats per round, rounds with compaction | repeats per round, rounds without |
|---|---|---|---|---|---|---|---|---|---|
| v3_ours_s0 | 100 | 226 | 98 | 226/226 | 2 | 33 | 2 | 0.02 | 0.0 |
| v3_base_s0 | 100 | 138 | 82 | 132/138 | 2 | 36 | 18 | 0.22 | 0.0 |
| hyp_ours_s1 | 100 | 222 | 97 | 222/222 | 2 | 37 | 3 | 0.03 | 0.0 |
| hyp_ours_s2 | 100 | 220 | 98 | 218/220 | 2 | 32 | 3 | 0.03 | 0.0 |
| hyp_base_s0 | 100 | 142 | 81 | 124/142 | 2 | 26 | 161 | 1.78 | 0.89 |
| hyp_base_s1 | 100 | 110 | 85 | 75/110 | 2 | 60 | 4 | 0.01 | 0.2 |
| hyp_base_s2 | 100 | 114 | 80 | 98/114 | 2 | 34 | 195 | 2.06 | 1.5 |
| dm_ours_s0 | 100 | 99 | 91 | 99/99 | 2 | 15 | 16 | 0.18 | 0.0 |
| dm_base_s0 | 100 | 44 | 43 | 43/44 | 1 | 7 | 0 | 0.0 | 0.0 |
| nf_base_s0 | 100 | 39 | 39 | 0/39 | None | 38 | 811 | 9.44 | 7.26 |
| nf_base_s1 | 100 | 187 | 49 | 135/187 | 1 | 48 | 1167 | 12.24 | 11.12 |

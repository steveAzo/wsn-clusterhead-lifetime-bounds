# Lead A: pre-registered hypotheses (written 2026-11-19, before the v2 batch, E9 audit, and E10 results were read)

Working angle: metaheuristic cluster-head (CH) selection is evaluated in the one regime where it looks best; under datasheet radios and an exact bound, it leaves a large share of achievable lifetime unused, and a known LP-scheduling method recovers it.

Setting fixed now: 100 nodes uniform in 100 x 100 m; sinks far (50,175), edge (50,100), centre (50,50); 4,000-bit reports, perfect aggregation; E0 = 0.5 J; path loss exponent 2.7, 10 dB margin; radios FO (Heinzelman constants), CC2420, nRF52840 (v3 brief), CC1101 868 MHz; energy model v2 (relays charged to relays, 25-byte control frames, single-hop membership); metric FND; seeds 0-2 (100 + seed for layout). Bound: column generation with exact facility-location pricing; report the bracket [LB, UB].

## Hypotheses and pass criteria

H1 (audit, E9): among the sampled 2021-2026 open-access CH papers that state an energy model, at least 70% use the first-order constants, and fewer than 10% compare against an optimum or bound. Fails if first-order share < 50%.

H2 (regime, E8): under every datasheet radio, DIRECT wins (or ties within 5%) whenever every node reaches the sink in one hop; clustering wins only when some nodes need relays. Under FO with the far sink, PSO-C wins. Fails if a datasheet radio shows clustering ahead by more than 5% in a fully single-hop layout.

H3 (gap, E8): in at least two of the three sink positions for CC2420 and nRF52840v3, the best of DIRECT, LEACH, KMRE, PSO-C reaches at most 80% of the LP upper bound (mean over seeds). Under FO with the far sink it reaches at least 90%. Fails if the best protocol reaches more than 90% of UB in every datasheet case.

H4 (recovery, E10): the LP schedule run as a protocol (re-plan every 50 rounds, exact v2 energies) reaches at least 95% of the LP lower bound in every case where H3 holds, and at least 90% with 10% energy-report noise. Fails below 90% without noise.

## Reporting rules

- Report every case, including those against the hypotheses; no case is dropped after the results are seen.
- The "bound" is the proven UB from exact pricing only. Heuristic minima are never called bounds (lesson from E1-E3).
- Credit: first-order critique (Elhabyan and Yagoub 2015); clustering-contingency analysis (Khedhiri et al. 2025); single-hop vs multi-hop (Fedor and Collier 2007); column generation for lifetime (Castano et al. 2018; EJOR 2010); lifetime bounds (Bhardwaj and Chandrakasan 2002).

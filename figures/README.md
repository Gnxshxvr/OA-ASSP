# Publication Figures

This directory contains the publication vector (PDF) and raster (PNG, 300 DPI) figures for the manuscript:

* **`fig1_pipeline.pdf` / `.png`**: System architecture diagram illustrating the overhead-priced selection pipeline (resident graph features, per-query features, vector assembly, compiled selector, and candidate solver dispatch).
* **`fig2_cost_vs_q.pdf` / `.png`**: Cumulative execution cost vs workload size $Q$ on a log-log scale for SBS, VBS, Library Adaptive, and Compiled Adaptive.
* **`fig3_required_capture.pdf` / `.png`**: RequiredCapture trajectory as a function of workload size $Q$, showing the break-even threshold ($1.0$) and transition from overhead-bound to viable.
* **`fig4_overhead_economics.pdf` / `.png`**: Overhead economics breakdown at $Q=500$ comparing available Oracle Gap to Library Overhead, Compiled Overhead, and Solver Selection Shortfall.
* **`fig5_selector_accuracy.pdf` / `.png`**: Exact classification accuracy of the decision tree selector vs majority-class policy under Held-Out, LOCO (24 folds), and LOFO (3 folds) cross-validation protocols.
* **`fig6_per_graph_delta.pdf` / `.png`**: Per-graph runtime differences $\Delta = C_{\mathrm{Adaptive}} - C_{\mathrm{SBS}}$ at $Q=500$ across all 8 test graphs, calibrated against the empirical noise floor ($9.40\%$).

All figures are programmatically generated and embedded in the manuscript.

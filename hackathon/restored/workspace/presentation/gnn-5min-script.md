# GNN for Realized Volatility Forecasting — 5-Minute Script

*~5 minutes, non-technical audience.*

---

## The Gap (0:00–0:45)

Our volatility forecasts are solid. We train on all 34 assets at once — pooled training — so the model learns shared rules like "high daily vol predicts high weekly vol."

But pooled training shares *parameters*, not *information*. When AAPL's volatility spikes today, the model predicting SPX tomorrow doesn't know that. It only sees APP's own features.

Volatility spills over between assets. Our models don't capture that. GNNs do — they build a network of connections between assets and let information flow along them at each point in time.

---
zoom
## Pooled Training vs. GNNs (0:45–1:15)

Pooled training: learns general rules from all stocks. Same coefficients applied independently to each asset's row.

GNN: at each date, each asset aggregates its neighbors' current features through the network. The prediction for Meta *today* incorporates what Apple and Google are doing *today*.

One learns shared rules. The other shares real-time information.

---

## Five Ways to Use GNNs (1:15–3:30)

A GNN's core operation produces a vector embedding per asset — a summary of its network position and neighbors' current state. That embedding isn't a forecast on its own. What we do with it is the design choice.

**1 — GNN with its own prediction head.** Attach a linear layer on top of the embeddings that maps each one to a scalar volatility forecast. The whole thing — graph layers + prediction head — trains end-to-end. Tested head-to-head against current models.

**2 — GNN prediction as a tree feature.** Take that scalar forecast from approach 1 and feed it as one extra column into our gradient-boosted tree. The tree decides how much to weight it alongside its existing features. Lowest-risk integration.

**3 — Node embeddings as tree features.** Skip the prediction head entirely. Extract the raw 8- or 32-dimensional embedding and inject it as extra columns in the tree's feature matrix. Richer than a single number — preserves what the GNN learned about neighbor activity and spillover patterns before collapsing it to a prediction.

**4 — Attention-weighted spillovers.** Replace fixed connection weights with learned, state-dependent weights. During a tech selloff, the model upweights sector peers. During a macro shock, it shifts to broad market indicators. Connections adapt to current conditions.

**5 — Regime-aware conditioning.** Add a calm-vs-stress regime probability as a feature, or build separate calm/stress graphs and blend them. Research suggests the simple feature version works as well as the graph version.

What the GNN layers actually do: Graph convolutions take each asset's features, aggregate neighbor information through the network, and output a vector embedding per asset. That embedding encodes the asset's position in the network and its neighbors' current state. On its own, it's not a prediction.

How it becomes a forecast: You bolt a prediction head on top — a simple linear layer or small MLP that maps the embedding down to a single number. So the architecture is: features → graph convolution → embedding → prediction head → scalar forecast. The prediction head is trained end-to-end with the graph layers.


Here's what goes into the GNN per date:

Two inputs per graph snapshot:

Node features — an (N, F) matrix where N=34 assets, F=9 columns by default:

log_rv_d, log_rv_w, log_rv_m — log realized vol at daily/weekly/monthly horizons
signed_return_d, abs_ret_d — daily return and its absolute value
log_rs_negative_d — downside semivariance
log_jump_d, log_bpv_d, log_cont_d — jump, bipower variation, continuous variation
Edges — an adjacency structure (edge_index + edge_attr) from whatever graph builder is selected (correlation, GLASSO, Diebold-Yilmaz, sector, etc.), re-estimated periodically on an expanding window.

The target y is forward log-RV at the chosen horizon (1/5/22 days).

So the inputs are the same HAR-family features the tree models already use, but arranged as a graph: one node per asset, edges encoding cross-asset relationships, and the GNN aggregates neighbor features through those edges to produce the embeddings.
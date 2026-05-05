# The quant trading self-study canon: 30 resources from zero to competition-ready

**The single most important insight from this research: there is no shortcut through the canon.** The best path for a math/CS person with zero finance knowledge runs through exactly three layers — market structure intuition (Harris), quantitative microstructure (Bouchaud), and applied strategy (Chan) — before branching into specialisations. Ten resources form the irreducible core: Harris's *Trading and Exchanges* for vocabulary, Bouchaud et al.'s *Trades, Quotes and Prices* for microstructure, Chan's *Algorithmic Trading* for stat arb, the Avellaneda-Stoikov paper for market making, Almgren-Chriss for execution, Natenberg for options intuition, Colin Bennett's free PDF for volatility surfaces, MIT OCW 18.S096 for rigorous Black-Scholes, López de Prado's *Advances in Financial Machine Learning* for methodology, and jmerle's Prosperity backtester for competition prep. Read in that order. Budget **250–350 hours** total; the priority topics (B, D, F, L, M) consume roughly 60% of that time. Eleven of the thirty resources are completely free. For IMC Prosperity 4 specifically, the winning pattern is clear from three years of data: market-make the fixed-price product at 10,000, pairs-trade the basket, Black-Scholes the options product, and copy-trade the informed bot in Round 5. For Goldman Sachs engineering, understand SecDB's dependency graph architecture and prepare with the Green Book.

---

## A. How markets actually work — the essential vocabulary layer

**Larry Harris — *Trading and Exchanges: Market Microstructure for Practitioners* (2003)**
Book · Oxford University Press · ~$40 used · 30–50 hours
The definitive single-volume treatment of exchanges, order types, order books, matching engines, maker/taker dynamics, fees, and clearing. Harris was SEC Chief Economist; the *Journal of Investment Management* called it "the most comprehensive treatment of market microstructure I have seen." It assumes zero finance knowledge and uses no heavy math — just clear institutional detail. The trader taxonomy (Chapter 4–7) provides the intellectual scaffolding for understanding *who* is on the other side of every trade, which directly feeds strategy selection. Published 2003, so it misses modern HFT and T+1 settlement, but the fundamentals are timeless.
**Prerequisites:** None. **Quality: Essential.**

**Jelle Pelgrims — "Matching Engines" (blog post, ~2020)**
Blog post + Python code · https://jellepelgrims.com/posts/matching_engines · Free · 2–4 hours
Converts order book mechanics into working Python data structures: `Order` and `Trade` classes, sorted bid/ask lists, FIFO matching. The insight that "a market order is just a limit order with price = 0 or ∞" elegantly demystifies order types for programmers. Covers only price/time priority; no fees, clearing, or pro-rata matching.
**Prerequisites:** Basic Python. **Quality: Recommended.**

---

## B. Market microstructure — the physics of price formation

This is where a math/CS person's advantage is largest. The field sits at the intersection of stochastic processes, econometrics, and empirical data analysis.

**Bouchaud, Bonart, Donier & Gould — *Trades, Quotes and Prices: Financial Markets Under the Microscope* (2018)**
Book · Cambridge University Press · ~$60 · 60–80 hours
**The single best microstructure book for a math/CS reader.** Written by Jean-Philippe Bouchaud (co-founder of Capital Fund Management, CNRS Silver Medal, Risk Quant of the Year 2017), it approaches price formation from a physics/data perspective: order flow statistics, limit order book dynamics, bid-ask spread decomposition, the square-root law of market impact, queue dynamics, Hawkes processes, and optimal execution — all calibrated against real NASDAQ data. Jim Gatheral calls it "an impressive book that no serious student of market microstructure can afford to be without." The data-first approach resonates with programmers: every model is tested against empirical facts.
**Weakness:** Some chapters require comfort with statistical physics (Fokker-Planck equations). Equity-centric.
**Prerequisites:** Probability theory, basic stochastic processes. **Quality: Essential.**

**Joel Hasbrouck — *Empirical Market Microstructure* (2007)**
Book · Oxford University Press · ~$55 · 40–50 hours
The standard PhD-level empirical toolkit: the Roll model (spread decomposition from serial covariance), Glosten-Milgrom sequential trade model, Kyle 1985, VAR models for microstructure, and information share measurement. Used at Columbia, Indiana, and the Foucault-Menkveld Stockholm summer school. Provides the econometric machinery to actually *work with* tick data. Published 2007, so it predates modern HFT, but the econometric methods are permanent.
**Prerequisites:** Time series analysis, VAR models. **Quality: Essential.**

**Dale Rosenthal — Market Microstructure course materials (UIC, 2020+)**
15-week slide deck + homework + R code · https://sites.google.com/site/dalerosenthal/teaching/market-microstructure · Free · 30–40 hours
Complete graduate course with executable R code for Kyle 1985 and Glosten-Milgrom simulations. The best free structured resource for learning microstructure systematically. Slides may be hard to follow without lecture audio, and weeks 12–13 (electronic trading tools) are embargoed.
**Prerequisites:** Basic probability, some R. **Quality: Essential (free complement).**

**Foucault, Pagano & Röell — *Market Liquidity: Theory, Evidence, and Policy* (2nd ed. 2024)**
Book · Oxford University Press · ~$55 · 50–60 hours
The economics/institutional counterpart to Bouchaud's physics approach. Covers limit order markets, dealer markets, dark pools, fragmentation, and HFT from a game-theoretic perspective. The 2024 second edition adds modern topics. Provides the *why* behind market structures.
**Prerequisites:** Intermediate microeconomics, basic game theory. **Quality: Recommended.**

---

## C. Market making — from Avellaneda-Stoikov to production

**Avellaneda & Stoikov — "High-Frequency Trading in a Limit Order Book" (2008)**
Paper · 20 pages · https://people.orie.cornell.edu/sfs33/LimitOrderBook.pdf · Free · 4–8 hours
**The foundational paper for quantitative market making.** Derives optimal bid/ask quotes using stochastic control: a reservation price that shifts with inventory, and an optimal spread calibrated to order arrival intensity. Clean two-step derivation, intuitive parameters (γ for risk aversion, κ for arrival rate, σ for volatility). Every market making quant has read this. Assumes continuous prices, Poisson arrivals, and no adverse selection — significant extensions needed for production.
**Prerequisites:** Stochastic calculus, CARA utility. **Quality: Essential.**

**Hummingbot — "A Comprehensive Guide to Avellaneda & Stoikov's Market-Making Strategy" (2021)**
Blog post + open-source implementation · https://hummingbot.org/blog/guide-to-the-avellaneda--stoikov-strategy/ · Free · 2–3 hours
Best practitioner-written explanation of A-S for programmers. Translates the math into "what does each parameter mean and how do I tune it?" The Hummingbot framework (Python, open source) runs the strategy on crypto exchanges. Crypto-focused but concepts transfer.
**Prerequisites:** None for blog; Python for code. **Quality: Recommended.**

**Cartea, Jaimungal & Penalva — *Algorithmic and High-Frequency Trading* (2015)**
Book · Cambridge University Press · ~$70 · 60–80 hours
**The graduate textbook that unifies microstructure, execution, and market making under a single stochastic control framework.** Covers optimal execution (extending Almgren-Chriss), VWAP/POV targeting, market making (extending A-S), pairs trading, and order imbalance — all with rigorous HJB equation derivations. Endorsed by Almgren, Foucault, and used at UCL, Toronto, Oxford. Mathematically demanding but self-contained (stochastic optimal control is taught in Chapter 5). **This single book covers Topics B, C, and H.**
**Prerequisites:** SDEs, Poisson processes. Strong math background required. **Quality: Essential.**

---

## D. Statistical arbitrage — cointegration, mean reversion, and beyond

**Ernest P. Chan — *Algorithmic Trading: Winning Strategies and Their Rationale* (2013)**
Book · Wiley · ~$50 · 20–30 hours
**The definitive practitioner guide to stat arb for self-taught quants.** Chapters 2–5 cover ADF tests, Hurst exponent, variance ratio, Engle-Granger and Johansen cointegration, Ornstein-Uhlenbeck half-life, Kalman filter trading, z-score entry/exit, and walk-forward estimation — with MATLAB code (widely ported to Python). Chan ran stat arb at Morgan Stanley and Millennium Partners. The value is in the methodology: he emphasizes what goes wrong (look-ahead bias, regime changes, false positives) as much as what works. Universally recommended on r/quant and Quant Stack Exchange.
**Weakness:** MATLAB code, not Python. Published strategies may have alpha-decayed. **Quality: Essential.**

**Avellaneda & Lee — "Statistical Arbitrage in the U.S. Equities Market" (2010)**
Paper · 22 pages · https://math.nyu.edu/~avellane/AvellanedaLeeStatArb071108.pdf · Free · 4–8 hours
The canonical academic treatment of institutional-grade stat arb. Presents **PCA-based factor extraction** and **sector ETF regression** to generate market-neutral signals, models residuals as OU processes, and backtests with transaction costs over 1997–2007. Reports **Sharpe ratios of 1.1–1.5**. Also studies the 2007 quant crisis. Bridges the gap between toy pairs trading and production multi-asset strategies. 400+ citations.
**Weakness:** No code. Specific parameters are competed away. Performance degraded post-2007. **Quality: Essential.**

**Letian Wang — "Cointegration and Pairs Trading" (blog + GitHub, 2018)**
Blog post + Python code · https://letianzj.github.io/cointegration-pairs-trading.html · Free · 3–5 hours
Complete pairs trading pipeline in Python: Engle-Granger CADF, Johansen test with eigenvector hedge ratios, Bollinger band trading on the spread, and walk-forward estimation. Reproduces Chan's classic EWA/EWC examples with clean, runnable statsmodels code. The best free Python implementation tutorial for someone going from theory to code.
**Prerequisites:** Python, basic statistics. **Quality: Essential (free companion to Chan).**

---

## E. Momentum and signal construction — two flavours of trend

**Moskowitz, Ooi & Pedersen — "Time Series Momentum" (2012)**
Paper · *Journal of Financial Economics* · http://docs.lhpedersen.com/TimeSeriesMomentum.pdf · Free · 5–8 hours
**The foundational paper defining time-series momentum (TSMOM):** a security's own past 12-month return positively predicts its future return. Tested across 58 liquid futures contracts spanning equities, currencies, commodities, and bonds over 25+ years, demonstrating **Sharpe ~1.0** with little exposure to standard risk factors. Cleanly distinguishes TS momentum from cross-sectional momentum. AQR provides free, regularly updated data at https://www.aqr.com/Insights/Datasets. 4,000+ citations.
**Weakness:** Empirical, no causal explanation. Alpha may partly be volatility scaling. **Quality: Essential.**

**Baz, Granger, Harvey, Le Roux & Rattray — "Dissecting Investment Strategies in the Cross Section and Time Series" (2015)**
Paper · https://www.cmegroup.com/education/files/dissecting-investment-strategies-in-the-cross-section-and-time-series.pdf · Free · 4–6 hours
Written by senior practitioners at **Man AHL** and PIMCO. Key insight: cross-sectional weights equal time-series weights minus their cross-sectional average. TS momentum outperforms CS when the global factor is trending. Covers carry, momentum, and value across asset classes in a unified framework.
**Quality: Recommended.**

---

## F. Options and volatility — four resources, one rigorous stack

**MIT OCW 18.S096 — "Topics in Mathematics with Applications in Finance" (Fall 2013)**
26 video lectures + notes + problem sets · https://ocw.mit.edu/courses/18-s096-topics-in-mathematics-with-applications-in-finance-fall-2013/ · Free · 6–8 hours (Lectures 19–21 for options)
The **only free resource providing a truly rigorous Black-Scholes derivation** via both PDE and probabilistic routes, co-taught by Morgan Stanley quants. The full course covers Itô calculus, SDEs, and stochastic processes — perfect for a math/CS background. Start here for the formal foundations.
**Quality: Essential.**

**Sheldon Natenberg — *Option Volatility and Pricing* (2nd ed., 2015)**
Book · ~$45 · 40–60 hours
Universally cited as **the first book given to new professional options traders at prop firms worldwide**. Exceptional at conveying *intuition* for how Greeks behave — the qualitative, trader-oriented perspective a math person needs to complement their quantitative skills. Covers spreads, dynamic hedging, and basic volatility concepts. The math is deliberately accessible (the Black-Scholes derivation is not rigorous — that's what MIT OCW is for).
**Quality: Essential.**

**Colin Bennett — *Trading Volatility: Correlation, Term Structure and Skew* (2014)**
Book/report · **FREE PDF:** https://www.trading-volatility.com/Trading-Volatility.pdf · 20–35 hours
Written by the former Head of Quantitative & Derivative Strategy at Banco Santander (previously Barclays, Deutsche Bank). **Best single resource on volatility surface, smile, skew, term structure, and correlation trading** — all for free. Endorsed by CBOE, Eurex, and Bloomberg. Kris Abdelmessih (ex-SIG, 21 years) took detailed public notes calling it "an outstanding reference." Fills the crucial gap between introductory derivatives books and quant modeling texts.
**Weakness:** Dated (2014 data); no second edition. Slightly sell-side research report style. **Quality: Essential.**

**Euan Sinclair — *Volatility Trading* (2nd ed., 2013)**
Book · Wiley · ~$60 · 25–40 hours
Written by a PhD physicist with 15+ years as a professional options trader at Bluefin Trading. Aaron Brown (AQR risk manager) called it "the classic work on practical options trading." Uniquely bridges quantitative rigour (GARCH, vol forecasting, mean-reversion of IV) with practical trading philosophy (when to trade, how to size, how to evaluate results). Key insight: **"Volatility trading is not dependent on the ability to trade directionally."** Companion spreadsheets included.
**Quality: Essential.**

**Euan Sinclair — *Positional Option Trading* (2020)**
Book · Wiley · ~$55 · 15–25 hours
Chapter 5 presents **~10 specific, empirically-backed trading edges** (variance premium, term-structure premia, earnings effects, post-earnings drift). Chapter 9 is a unique treatment of Kelly criterion applied to options. Robot Wealth called Chapter 5 alone "worth the price."
**Prerequisites:** Natenberg + Sinclair Vol Trading. **Quality: Recommended.**

---

## G. The arbitrage zoo — recognising structural mispricings

**Aswath Damodaran — "Options Arbitrage" (NYU Stern lecture notes)**
Lecture notes · https://pages.stern.nyu.edu/~adamodar/New_Home_Page/invfables/optionarb.htm · Free · 2–3 hours
Covers exercise arbitrage, replicating portfolios (step-by-step binomial tree), **put-call parity** with full derivation and empirical frequency of violations, and spread arbitrage conditions (strike, calendar, butterfly). Derives results from first principles using concrete dollar amounts.
**Weakness:** Options arbitrage only. For triangular FX arb, see IFT World (https://ift.world/); for ETF creation/redemption, see ETF.com; for cross-market and index arb, see Harris Chapter 17. **Quality: Essential.**

---

## H. Execution — Almgren-Chriss and the efficient frontier of trading

**Almgren & Chriss — "Optimal Execution of Portfolio Transactions" (2000)**
Paper · 40 pages · Free · 6–10 hours
**The foundational paper for optimal execution**, defining the trade-off: minimise E[cost] + λ·Var[cost]. Introduces permanent vs. temporary market impact, derives closed-form hyperbolic sine trajectories under linear impact, and constructs the efficient frontier of execution strategies. Almgren co-founded Quantitative Brokers. The paper is beautifully written and surprisingly accessible — uses static optimisation, not dynamic programming. A math/CS reader will find it very approachable.
**Weakness:** Linear impact assumptions; static strategies don't adapt to conditions. **Quality: Essential.**

**joshuapjacob/almgren-chriss-optimal-execution (GitHub)**
Jupyter Notebook · https://github.com/joshuapjacob/almgren-chriss-optimal-execution · Free · 3–5 hours
Most complete open-source implementation. Uses real data (GOOG, META), implements optimal trajectory computation, efficient frontier visualisation, and multi-asset extension including cross-exchange examples.
**Quality: Recommended.**

---

## I. Risk management — Kelly, metrics, and the art of not blowing up

**Edward O. Thorp — "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market" (2006)**
Paper/chapter · https://web.williams.edu/Mathematics/sjmiller/public_html/341/handouts/Thorpe_KellyCriterion2007.pdf · Free · 4–6 hours
**The definitive practitioner treatment of Kelly** by the person who pioneered its use in both gambling and finance. Covers the binary formula, multi-asset continuous-time extension, geometric growth rate maximisation, the case for **fractional Kelly** (half or quarter Kelly to reduce variance at modest growth cost), and practical stock market application. Thorp ran Princeton Newport Partners for 19 years with essentially no losing years. Reads like a math paper, not a trading blog.
**Weakness:** Does not cover VaR, ES, Sharpe, or drawdown. **Quality: Essential.**

For **VaR, Expected Shortfall, Sharpe/Sortino/Calmar ratios, and drawdown analysis**, the QuantInsti survey at https://blog.quantinsti.com/performance-metrics-risk-metrics-optimization/ provides formulas, Python code, and clear progression from simple (Sharpe) to sophisticated (CVaR). Free, 2–3 hours. **Quality: Recommended.**

---

## J. The quant dev toolkit — frameworks, pitfalls, and honest comparisons

The Python backtesting ecosystem is fragmented. No single framework dominates. The right choice depends on your workflow stage:

- **Learning/prototyping:** Backtesting.py (https://kernc.github.io/backtesting.py/) — lightweight, Pythonic, interactive HTML charts. Best entry point. Free.
- **Research/parameter exploration:** vectorbt (https://vectorbt.dev/) — vectorised with Numba JIT. Processes millions of parameter combos simultaneously. Fastest Python backtester. Free core; Pro is paid.
- **Production/live trading:** NautilusTrader (https://nautilustrader.io/) — Rust core, Python API, nanosecond resolution, backtest-to-live code parity. Most architecturally ambitious open-source engine. Steep learning curve, breaking API changes between releases. Free.
- **Full ecosystem (data + compute + live):** QuantConnect LEAN (https://www.quantconnect.com/) — 400TB+ point-in-time data, cloud IDE, C# engine (40–50x faster than Python). Trustpilot 4.5/5 but polarised reviews (IDE stability complaints). Free tier available.
- **Avoid as primary framework:** backtrader — feature-rich but **effectively abandoned** (no significant commits since ~2020, community forum disabled).

**Critical backtesting pitfalls** that every quant must internalise: **look-ahead bias** (using information unavailable at decision time), **survivorship bias** (testing only on currently-listed securities), and **overfitting** (optimising parameters until backtests look perfect on historical data but fail live). López de Prado's **combinatorial purged cross-validation (CPCV)** addresses all three by generating C(N,k) train/test splits with temporal purging and embargo buffers, producing a *distribution* of out-of-sample performance rather than a single point estimate. See *Advances in Financial Machine Learning* Chapter 12.

**jmerle's IMC Prosperity backtester** (https://github.com/jmerle/imc-prosperity-3-backtester, `pip install prosperity3bt`) — the community-standard tool for competition prep, compatible with jmerle's visualiser. Competition-specific; not general-purpose. **Quality: Essential for Prosperity.**

---

## K. Machine learning for trading — where it helps, where it's overfit garbage

**Marcos López de Prado — *Advances in Financial Machine Learning* (2018)**
Book · Wiley · ~$50 · 60–100 hours
**The foundational text on financial ML methodology.** López de Prado managed $13B at Guggenheim Partners and heads ML at ADIA. The book's central message — **"the hardest problem is not prediction, it's validation"** — is the most important insight in financial ML. Novel contributions include **triple-barrier labeling**, **meta-labeling** (a secondary ML model determining whether a primary signal is worth acting on), **CPCV**, **fractional differentiation** (preserving memory while achieving stationarity), and **information-driven bars** (volume/dollar/tick bars with better statistical properties than time bars). 100,000+ copies sold.
**Weakness:** Not a tutorial — a research monograph with disconnected chapters. Python code is sometimes incomplete. Assumes more finance knowledge than a zero-finance reader has. Use the Reasonable Deviations summary (https://reasonabledeviations.com/notes/adv_fin_ml/) as companion.
**Prerequisites:** Strong ML, Python, graduate statistics. **Quality: Essential.**

**Where ML actually helps:** Feature engineering and selection, execution optimisation, alternative data processing (NLP on earnings calls), risk management (regime detection, HRP portfolio construction), and **meta-labeling** (sizing bets on existing signals). **Where ML fails:** Naked return prediction from price data alone, standard k-fold CV on time series, excessive hyperparameter optimisation. AQR demonstrated a moving average strategy's Sharpe dropping from **1.2 to −0.2** on fresh data after optimisation.

---

## L. "Which strategy when?" — the hardest question in quant trading

**This is genuinely the hardest topic to find good resources on. No single published resource provides a complete decision tree mapping market diagnostics to strategy choice.** The knowledge is largely tacit, held inside prop trading firms. What follows is the best available assemblage.

**Ernest P. Chan — *Quantitative Trading* (2nd ed., 2022) + *Algorithmic Trading* (2013) + CPO blog posts**
Chan's work across multiple books is the closest thing to a practitioner's strategy selection framework. *Quantitative Trading* Ch. 2 ("How to Identify a Strategy That Suits You") and Ch. 7 ("Mean-Reverting Versus Momentum Strategies" + "Regime Switching") directly address when each strategy works. His **Conditional Parameter Optimisation (CPO)** blog post (https://predictnow-ai.medium.com/conditional-parameter-optimization-adapting-parameters-to-changing-market-regimes-b7158ab78ed4, free) uses random forests to adapt strategy parameters to changing regimes — the most direct treatment of the meta-problem found anywhere.
**Quality: Essential.**

**López de Prado's meta-labeling** (Ch. 3 of *AFML*) is strategy selection at the trade level: a secondary model determines whether a primary model's signal is likely to be profitable *given current market conditions*. This is the "should I act on this signal right now?" question reduced to an ML classification problem.
**Quality: Recommended (as building block).**

**Regime detection** is the necessary prerequisite. The best practical tutorial is QuantStart's "Market Regime Detection using Hidden Markov Models" (https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/) — a concrete Python implementation using HMMs as a trade filter for trend-following. Meudt et al. (2020, open access at https://www.mdpi.com/1911-8074/13/12/311) demonstrate that **value investing works in high-variance regimes while momentum works in low-variance regimes**, providing an empirical strategy-regime mapping.

The practical framework synthesised from these sources: (1) Classify market regime using HMM/clustering on volatility + returns; (2) Diagnose opportunity type — wide spreads → market making, cointegrated divergence → stat arb, order-flow imbalance → directional signal, vol smile kinks → options mispricing, cross-venue gaps → arbitrage; (3) Apply meta-labeling or CPO to filter signals; (4) Rotate allocation conditionally. **No single resource walks through this complete pipeline — this is the major gap in the literature.**

---

## M. IMC Prosperity — three years of data, one clear playbook

IMC Prosperity is an annual algorithmic trading competition (Python, ~15 days, 5 rounds) that has run since 2023. **Prosperity 4 begins April 14, 2026** — four days from now. The competition reuses product archetypes with remarkable consistency.

### Year-over-year product patterns

| Product archetype | P1 (2023) | P2 (2024) | P3 (2025) |
|---|---|---|---|
| **Fixed price (~10,000)** | PEARLS | AMETHYSTS | RAINFOREST_RESIN |
| **Volatile/trending** | BANANAS | STARFRUIT | KELP, SQUID_INK |
| **Basket/ETF** | PICNIC_BASKET | GIFT_BASKET | PICNIC_BASKETS |
| **Options** | — | COCONUT_COUPONS | VOLCANIC_ROCK_VOUCHERS |
| **Cross-exchange arb** | — | ORCHIDS | MACARONS |
| **Signal-driven** | BERRIES (seasonal), DIVING_GEAR (dolphins) | — | — |
| **Bot intelligence (R5)** | Trading history | Trading history | Trader IDs ("Olivia" = insider) |

### The winning playbook

Five strategies cover virtually every round: **(1)** Market-make the fixed-price product at 10,000 ± 1 (consistent easy profit since P1). **(2)** Linear regression or EMA for fair value on trending products. **(3)** Pairs/stat arb on basket vs. components (spread = basket − Σ weighted components). **(4)** Black-Scholes IV mean reversion + delta hedging for options products. **(5)** Copy-trade the informed bot in Round 5 (in P3, "Olivia" was the insider). **Cross-year data reuse** has been a massive alpha source — in P2, P1 price paths predicted P2 prices almost exactly.

### Comprehensive writeup table

| Year | Team | Rank | URL | Key strategies | Key insight |
|---|---|---|---|---|---|
| P1 | Stanford Cardinal | 2nd | https://github.com/ShubhamAnandJain/IMC-Prosperity-2023-Stanford-Cardinal | MM at 10k, pairs (coconuts/pina coladas), seasonal berries, basket arb | Data science on berries jumped them from 926th to 60th |
| P1 | Zahcheesha | 57th | https://github.com/MichalOkon/imc_prosperity | Built custom simulator; datasets included | Versatile sim enabled rapid iteration |
| P1 | nicolassinott | 91st | https://github.com/nicolassinott/IMC_Prosperity | EMA MM, pairs, z-score spread | Z-score ±1.5 for baskets |
| P2 | Linear Utility | 2nd | https://github.com/ericcccsliu/imc-prosperity-2 | MM, cross-exchange arb, basket spread, BS IV mean reversion | P1 data = near-exact predictor of P2 prices (R²=0.99) |
| P2 | jmerle | 9th | https://github.com/jmerle/imc-prosperity-2 | MM, orchid conversion, grid-searched basket thresholds | Built all community tooling during tutorial round |
| P2 | pe049395 | 13th | https://github.com/pe049395/IMC-Prosperity-2024 | Hidden fair value ≠ midprice; Monte Carlo data augmentation | Maximise expected utility per trade |
| P2 | gabsens | — | https://github.com/gabsens/IMC-Prosperity-2-Manual | Manual trading mathematical solutions (game theory) | Jupyter notebooks for all 5 manual rounds |
| P3 | TimoDiehm | 2nd | https://github.com/TimoDiehm/imc-prosperity-3 | MM (fixed/mean-revert/volatile), basket stat arb, BS options, Olivia copy-trading | ~50-page writeup; discovered and reported bot hardcoding exploit |
| P3 | chrispyroberts | 7th | https://github.com/chrispyroberts/imc-prosperity-3 | Resin MM, Kelp mid from persistent bot, basket model, Olivia YOLO | Manual R1 was BFS currency exchange (cf. Leetcode 3387) |
| P3 | Alpha Animals | 9th | https://github.com/CarterT27/imc-prosperity-3 | Adapted prior years' open-source strategies | "This year's IMC Prosperity was very similar to the last two years" |
| P3 | jmerle | 25th | https://github.com/jmerle/imc-prosperity-3 | Full algorithm + writeup | Created optimizer (private) |
| P3 | AlphaBaguette | Top 1% | https://github.com/Sylvain-Topeza/imc-prosperity-3 | Adaptive MM (OU for Kelp), conversion arb, BS, Olivia flow | Detailed README with strategy rationale |
| P3 | Martin Oravec | 73rd | https://github.com/MartinOravecSvK/IMC_Prosperity_2025 | Solo player; detailed Medium writeup | Discord was critical resource |

### Essential tooling

- **Backtester (P3):** https://github.com/jmerle/imc-prosperity-3-backtester (`pip install prosperity3bt`)
- **Visualiser (P3):** https://github.com/jmerle/imc-prosperity-3-visualizer (live: https://jmerle.github.io/imc-prosperity-3-visualizer/)
- **Leaderboard (P3):** https://github.com/jmerle/imc-prosperity-3-leaderboard
- **P2 backtester:** https://github.com/jmerle/imc-prosperity-2-backtester (`pip install prosperity2bt`)
- **P1 simulator:** https://github.com/MichalOkon/imc_prosperity (includes datasets)

### Critical preparation advice

**Tooling first:** Build or install backtester + visualiser *before* the competition starts. Multiple top-10 teams emphasise this. **Study prior writeups exhaustively** — product archetypes repeat. **Join the Discord** — moderator hints and community discussion are decisive. **Watch AWS Lambda memory limits** (~100MB; verbose logging crashes runs). **Keep strategies simple** — P3 winner Anant Consul emphasised simplicity and persistence over complex models.

---

## N. Goldman Sachs engineering — SecDB, Slang, and what the job actually is

**Emanuel Derman — *My Life as a Quant* (2004)**
Memoir · ~$15 · 8–12 hours
The canonical narrative of how quant finance emerged at Goldman Sachs. Derman co-created the Black-Derman-Toy model and the Derman-Kani local volatility model during his 1985–2002 tenure. Provides irreplaceable cultural context: the evolution of the "strats" role, how quants gained respect on trading floors, Fischer Black as mentor. Nassim Taleb: "I know of no other book that bridges the two cultures." Skim the physics chapters if pressed for time. **Quality: Essential.**

**eFinancialCareers — SecDB deep dive (2017) + Slang MD perspective (2023)**
Articles · https://www.efinancialcareers.com/news/2017/02/secdb-goldman-sachs-slang + https://www.efinancialcareers.com/news/2023/04/goldman-sachs-slang-84 · Free · 30 min total
SecDB, created in 1991–93 at J Aron, is GS's proprietary platform for pricing, risk, and trade management. **200M+ lines of Slang code, 160M daily jobs, 13,000 daily users, 300M+ compute hours/week.** Slang (Securities LANGuage) integrates tightly with SecDB's dependency graph for sensitivity analysis — invalidating parameters to get new NPV under different scenarios. GS is migrating to Java/Python but Slang will persist for decades. **Quality: Essential (interview talking points).**

**InfoQ — "From Runtime Efficiency to Carbon Efficiency" (GS Slang VM Redesign)**
Conference talk · https://www.infoq.com/presentations/slang/ · Free · 45–60 min
The single most technically detailed public resource on Slang's internals. Reveals: C-based syntax, dynamically typed, case insensitive, no keywords, variables can contain spaces. They're building a new bytecode VM with JIT compilation targeting **135M compute hours/week reduction**. Perfect for a CS audience — this is a compilers talk, not a finance talk. **Quality: Essential for engineering candidates.**

**Xinfeng Zhou — *A Practical Guide to Quantitative Finance Interviews* ("The Green Book", 2nd ed. 2020)**
Book · ~$27 · 20–40 hours
200+ real interview questions spanning probability, stochastic processes, linear algebra, and programming with detailed solutions. Widely called "the holy grail of quant finance interview prep." Goodreads 4.7/5. For an engineering role, focus on the probability and programming chapters. The stochastic calculus sections teach real mathematical content.
**Quality: Essential.**

**What "off-cycle" means:** Unlike standard summer internships (June–August, applied ~1 year ahead), off-cycle placements at GS are **3–12 month programs** available on a rolling basis for penultimate/final-year students or recent graduates. Process: online application → HackerRank OA (2–3 coding problems + math MCQs) → HireVue (6 behavioural questions) → Superday (2 rounds, 45 min each). **Languages valued:** Java (primary for new development), Python (growing, especially strats), C++ (performance-critical), SQL. Check the GS off-cycle page at https://www.goldmansachs.com/careers/students/programs-and-internships/emea/off-cycle-internships and Glassdoor interview reviews for latest question types.

---

## O. Course evaluation — the Udemy course is not worth your time

**Udemy "Algorithmic Trading A-Z with Python, ML & AWS" (Alexander Hagmann, revised 2024)**
~40 hours · ~$15 on sale · 4.5/5 from ~4,000 reviews
Covers broker APIs (OANDA, IBKR), Python/Pandas, technical indicators, basic ML/DL, backtesting, and AWS deployment. **Verdict for our target reader: weak fit.** The Python basics are redundant for someone with CS background. The ML sections are introductory — nothing a CS person doesn't know. The strategies are commodity technical analysis, not quantitative edge. No microstructure, no rigorous CV methods, no LOB data, no order flow. Primarily retail forex/CFD focused.
**Quality: Skip for this audience.**

**Five superior alternatives, in recommended order:**

- **Stefan Jansen — *Machine Learning for Algorithmic Trading* (2nd ed., 2020):** 800+ pages, 150+ Jupyter notebooks, end-to-end ML trading workflow from data sourcing through deep RL agents. Covers alpha factor research, NLP on SEC filings, alternative data. The most comprehensive ML-for-trading resource available. ~$45. **Quality: Essential.**
- **QuantConnect Bootcamp:** Free interactive labs on a real production platform with 400TB+ data. Teaches by doing, not lecturing. Good complement but not standalone — teaches the platform, not the theory. **Quality: Recommended.**
- **Coursera — EDHEC "Investment Management with Python and ML" Specialisation:** Rigorous mathematical foundation (mean-variance, factor models, risk budgeting) with Python. Best Coursera option. ~$49/month for certificate; free to audit. **Quality: Recommended.**
- **López de Prado — *AFML*:** Already covered in Topic K. Essential methodology but difficult as a first book. Read Jansen first for practical grounding, then López de Prado for methodological rigour. **Quality: Essential.**
- **López de Prado — *Machine Learning for Asset Managers* (2020, Cambridge Elements):** Shorter, more focused companion (~$20). Covers distance metrics, optimal clustering, signal processing. Better for someone who already understands the concepts. **Quality: Recommended.**

---

## Gaps, open questions, and honest uncertainties

**The "which strategy when?" gap is real.** No published resource provides a complete, systematic framework mapping market diagnostics to strategy choice. The knowledge exists inside prop firms but is not public. The best approximation is Chan's CPO + López de Prado's meta-labeling + HMM regime detection, assembled by the reader.

**Prosperity 4 is unknown territory.** P4 uses a new currency (XIRECs) and a deep space theme. While product archetypes have repeated across P1–P3, IMC may introduce new mechanics. The "bot hardcoding exploit" discovered in P3 was patched, and the new rule excluding prior top-10 teams from rankings suggests IMC is actively iterating.

**The Goldman Sachs tech stack is moving.** SecDB/Slang will persist but new development is increasingly Java/Python. The relative importance of Slang knowledge for an off-cycle engineering placement in 2026 is uncertain. Understanding the *architecture* (dependency graphs, sensitivity analysis, bi-temporal data) matters more than the language syntax.

**Alpha decay is real across all published strategies.** Every specific strategy described in any resource here should be expected to have degraded since publication. Ernest Chan's classic EWA/EWC pairs trade, Avellaneda-Lee's PCA stat arb, and simple TSMOM implementations have all attracted crowding. The value is in learning methodology — the frameworks for discovering new edges, not copying old ones.

**Several canonical texts are showing their age.** Harris (2003), Hasbrouck (2007), and Hull predate the modern HFT era, crypto markets, and T+1 settlement. Bouchaud (2018) and Cartea (2015) are more current but still miss recent developments in DeFi market structure and transformer-based models.

**Resources not found despite searching:** A comprehensive "arbitrage zoo" tutorial covering all types in one place does not appear to exist. Each arbitrage type (triangular FX, ETF creation/redemption, cash-and-carry, index arb) has isolated explanations but no unified treatment beyond Harris Chapter 17. Similarly, no good free resource exists for walk-forward estimation that goes beyond the conceptual level to provide robust, production-quality Python code with proper purging.

---

## Recommended reading order

The following sequence totals approximately **300 hours** and covers all topics, prioritising the areas most relevant to both IMC Prosperity 4 and Goldman Sachs engineering interviews:

**Week 1–2 (Foundations, ~30 hrs):** Harris *Trading and Exchanges* (skim Parts I, IV) → Pelgrims matching engine tutorial → MIT OCW 18.S096 Lectures 19–21

**Week 3–5 (Microstructure + Options, ~80 hrs):** Bouchaud *Trades, Quotes and Prices* → Natenberg *Option Volatility and Pricing* → Colin Bennett PDF → Avellaneda-Stoikov paper

**Week 6–8 (Strategies, ~60 hrs):** Chan *Algorithmic Trading* → Letian Wang pairs trading code → Avellaneda-Lee paper → Almgren-Chriss paper → Moskowitz TSMOM paper

**Week 9–10 (ML + Risk, ~50 hrs):** Jansen *ML for Algorithmic Trading* (selected chapters) → López de Prado *AFML* (Chapters 2–7, 12) → Thorp Kelly criterion paper

**Week 11–12 (Competition + Interview Prep, ~40 hrs):** All Prosperity writeups (TimoDiehm's P3 writeup first) → jmerle backtester setup → Green Book (selected chapters) → Derman *My Life as a Quant* → Sinclair *Volatility Trading*

**Ongoing:** Moontower blog (vol intuition), Robot Wealth blog (stat arb at scale), r/quant, Discord for Prosperity community.
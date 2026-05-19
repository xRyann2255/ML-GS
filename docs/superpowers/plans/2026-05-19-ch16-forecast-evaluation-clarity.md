# Chapter 16 Forecast Evaluation Clarity Improvements

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix six comprehension gaps in `vol-learning-guide/chapters/16-forecast-evaluation.tex` so a first-time reader can understand what each statistical result means and what action it implies.

**Architecture:** Surgical edits to one file. No restructuring, no deletions. Four change groups: QLIKE optimality fix, worked example improvements, connective tissue between tools, smaller fixes. All changes are LaTeX additions or rewording within existing `tcolorbox` environments.

**Tech Stack:** LaTeX (memoir class, tcolorbox environments: `intuition`, `keyidea`, `warning`, `workedexample`, `projectconnection`)

**Spec:** `docs/superpowers/specs/2026-05-19-ch16-forecast-evaluation-clarity-design.md`

---

### Task 1: Add "Seven Tools, Seven Questions" roadmap box

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:46` (after the "Why Evaluation Methodology Matters" section)

- [ ] **Step 1: Add the keyidea box after line 46**

Insert after `It is the infrastructure you build \emph{first}, so that every experiment you run produces honest, comparable numbers from day one.` (line 45-46):

```latex

\begin{keyidea}[Seven Tools, Seven Questions]
This chapter introduces seven evaluation tools.
Each answers one question:
\begin{enumerate}[nosep]
  \item \textbf{QLIKE}: which model has lower loss? (Primary metric.)
  \item \textbf{MSE}: does the ranking hold under a different loss? (Secondary check.)
  \item \textbf{MZ regression}: is my forecast biased or too smooth? (Diagnostic.)
  \item \textbf{DM test}: is the loss difference between two models statistically significant? (Pairwise test.)
  \item \textbf{MCS}: given all candidate models, which ones survive? (Multi-model filter.)
  \item \textbf{Purged CV}: how do I tune hyperparameters without leaking future data? (Training procedure.)
  \item \textbf{DSR}: is my backtest Sharpe real after accounting for all experiments? (Multiple-testing correction.)
\end{enumerate}
You will use all seven, in roughly this order.
\end{keyidea}
```

- [ ] **Step 2: Verify the file compiles**

Run:
```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```
Expected: compilation succeeds (ignore warnings about references/citations).

- [ ] **Step 3: Commit**

```bash
git add vol-learning-guide/chapters/16-forecast-evaluation.tex
git commit -m "feat(ch16): add 'Seven Tools, Seven Questions' roadmap box"
```

---

### Task 2: Fix QLIKE bias misunderstanding

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:144-149` (existing "In Plain English" box)
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:149` (insert new intuition box after)
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:366-370` (figure caption)

- [ ] **Step 1: Reword the existing "In Plain English" box (lines 144-149)**

Find and replace the existing box content. The current text ends at line 148-149:

```
This asymmetry matches real-world priorities: underestimating volatility gets you fired; overestimating it merely costs some opportunity.
\end{intuition}
```

Replace with:

```latex
This asymmetry matches real-world priorities: underestimating volatility gets you fired; overestimating it merely costs some opportunity.
This does not mean the optimal forecast is biased upward.
It means that among two equally wrong forecasts, the one that errs low is more costly.
The target is still the true variance.
\end{intuition}
```

- [ ] **Step 2: Add new intuition box after the reworded box**

Insert immediately after the `\end{intuition}` that closes the box edited in Step 1 (before the "Why QLIKE Is Less Sensitive to Outliers" box):

```latex

\begin{intuition}[QLIKE Is Still Minimized at the True Value]
A common misreading of the asymmetric penalty is: ``If under-prediction is punished more, shouldn't I forecast a bit high to be safe?''
No.
Take the derivative of a single day's QLIKE contribution with respect to the forecast $h_t$:
\[
\frac{\partial}{\partial h_t}\left(\ln h_t + \frac{\sigma^2_t}{h_t}\right) = \frac{1}{h_t} - \frac{\sigma^2_t}{h_t^2} = 0 \quad \Longrightarrow \quad h_t = \sigma^2_t.
\]
The minimum is at $h_t = \sigma^2_t$ exactly.
The asymmetry shapes the penalty \emph{curve}, not the penalty \emph{minimum}.
Think of a speed limit: the best speed is exactly the limit.
Getting caught going 20 over is worse than going 20 under, but that does not make 20-under the target.
QLIKE works the same way: the best forecast is the true variance, but being wrong on the low side hurts more than being wrong on the high side by the same amount.
\end{intuition}
```

- [ ] **Step 3: Fix the figure caption (lines 366-370)**

Find the current caption text:

```
QLIKE penalizes under-prediction (ratio $< 1$) much more harshly than over-prediction (ratio $> 1$), matching the asymmetric risk preferences in volatility forecasting: underestimating vol means holding too much risk.}
```

Replace with:

```latex
QLIKE penalizes under-prediction (ratio $< 1$) much more harshly than over-prediction (ratio $> 1$), matching the asymmetric risk preferences in volatility forecasting: underestimating vol means holding too much risk.
Despite this asymmetry, both losses are minimized at ratio $= 1$ (the true variance); the asymmetry shapes the penalty curve, not the optimal forecast.}
```

- [ ] **Step 4: Verify the file compiles**

Run:
```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 5: Commit**

```bash
git add vol-learning-guide/chapters/16-forecast-evaluation.tex
git commit -m "fix(ch16): clarify QLIKE is minimized at true variance, not biased upward"
```

---

### Task 3: Replace MSE vs QLIKE worked example with ranking reversal

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:166-209` (replace entire worked example)

- [ ] **Step 1: Replace the worked example**

Find the entire block from `\begin{workedexample}{MSE vs.\ QLIKE Can Disagree}` (line 166) through `\end{workedexample}` (line 209). Replace with:

```latex
\begin{workedexample}{MSE and QLIKE Can Disagree on Rankings}
Consider five days of forecasts from two models, evaluated against realized variance.
Model~A is a reactive forecaster that under-predicts during calm periods but partially captures the crisis spike.
Model~B is a stable forecaster that nails normal days but barely reacts to the spike.

\medskip
\begin{center}
\begin{tabular}{cccc}
\toprule
Day & $\RV_t$ & Model A ($h^A_t$) & Model B ($h^B_t$) \\
\midrule
1 & 1.0 & 0.4 & 1.0 \\
2 & 1.1 & 0.4 & 1.1 \\
3 & 0.9 & 0.4 & 0.9 \\
4 & 1.0 & 0.4 & 1.0 \\
5 & 8.0 & 6.0 & 2.0 \\
\bottomrule
\end{tabular}
\end{center}
\medskip

\textbf{MSE computation:}
\begin{align*}
\text{MSE}_A &= \tfrac{1}{5}\bigl[(1.0-0.4)^2 + (1.1-0.4)^2 + (0.9-0.4)^2 + (1.0-0.4)^2 + (8-6)^2\bigr] \\
  &= \tfrac{1}{5}(0.36 + 0.49 + 0.25 + 0.36 + 4) = 1.092 \\[4pt]
\text{MSE}_B &= \tfrac{1}{5}\bigl[(1.0-1.0)^2 + (1.1-1.1)^2 + (0.9-0.9)^2 + (1.0-1.0)^2 + (8-2)^2\bigr] \\
  &= \tfrac{1}{5}(0 + 0 + 0 + 0 + 36) = 7.200
\end{align*}

MSE ranks Model A first (1.092 < 7.200).
The crisis day drives the entire result: Model B's MSE is 99.9\% from day~5 alone.

\textbf{QLIKE computation:}
\begin{align*}
\QLIKE_A &= \tfrac{1}{5}\bigl[(\ln 0.4 + \tfrac{1.0}{0.4}) + (\ln 0.4 + \tfrac{1.1}{0.4}) + (\ln 0.4 + \tfrac{0.9}{0.4}) + (\ln 0.4 + \tfrac{1.0}{0.4}) + (\ln 6 + \tfrac{8}{6})\bigr] \\
  &= \tfrac{1}{5}(1.584 + 1.834 + 1.334 + 1.584 + 3.125) = 1.892 \\[4pt]
\QLIKE_B &= \tfrac{1}{5}\bigl[(\ln 1.0 + \tfrac{1.0}{1.0}) + (\ln 1.1 + \tfrac{1.1}{1.1}) + (\ln 0.9 + \tfrac{0.9}{0.9}) + (\ln 1.0 + \tfrac{1.0}{1.0}) + (\ln 2 + \tfrac{8}{2})\bigr] \\
  &= \tfrac{1}{5}(1.000 + 1.095 + 0.895 + 1.000 + 4.693) = 1.737
\end{align*}

QLIKE ranks Model B first (1.737 < 1.892).
The rankings \emph{reverse}: MSE picks A, QLIKE picks B.

\textbf{What this tells you.}
MSE picked Model~A because the crisis day dominates quadratically: $(8-2)^2 = 36$ versus $(8-6)^2 = 4$.
Being closer on one extreme day overwhelmed Model~A's poor performance on four normal days.
QLIKE picked Model~B because QLIKE penalizes Model~A's under-prediction on normal days through the $\sigma^2_t / h_t$ ratio ($1.0/0.4 = 2.5$ on each normal day), and the crisis-day QLIKE gap ($4.693 - 3.125 = 1.57$) is not large enough to compensate.
For daily risk management, where forecast quality on typical days matters more than one extreme day, QLIKE's ranking is more useful.
When MSE and QLIKE disagree, check whether the MSE ranking is driven by a handful of extreme days.
\end{workedexample}
```

- [ ] **Step 2: Verify the file compiles**

Run:
```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 3: Commit**

```bash
git add vol-learning-guide/chapters/16-forecast-evaluation.tex
git commit -m "feat(ch16): replace MSE/QLIKE example with one that shows ranking reversal"
```

---

### Task 4: Add QLIKE vs MZ relationship and MZ prescriptions

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:379-380` (add analogy after existing sentence)
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:429` (add prescription box after MZ diagnostic intuition box)

- [ ] **Step 1: Add scoreboard/film-review analogy (after line 379-380)**

Find:
```
$\QLIKE$ tells you which model has lower average loss, but it does not tell you \emph{why} a forecast is bad.
The Mincer--Zarnowitz regression is a simple diagnostic that decomposes forecast errors into bias and inefficiency.
```

Replace with:
```latex
$\QLIKE$ tells you which model has lower average loss, but it does not tell you \emph{why} a forecast is bad.
Think of $\QLIKE$ as the scoreboard and the Mincer--Zarnowitz regression as the film review: $\QLIKE$ tells you who won; MZ tells you what to fix.
The MZ regression is a simple diagnostic that decomposes forecast errors into bias and inefficiency.
```

- [ ] **Step 2: Add "What to Fix" keyidea box after MZ diagnostic intuition (after line 429)**

Find the closing of the "Mincer--Zarnowitz as a Diagnostic" intuition box:
```
If $a = 0.003$, your forecast systematically under-predicts by about 0.3 variance points.
\end{intuition}
```

Insert after it:
```latex

\begin{keyidea}[What to Fix Based on MZ Results]
The MZ regression is only useful if you act on the diagnosis:
\begin{itemize}[nosep]
  \item \textbf{$b < 1$ (forecast too smooth):} your model over-relies on long-horizon averages. Try adding shorter-lag features (e.g., 1-day lagged $\RV$), reducing regularization strength, or increasing model capacity.
  \item \textbf{$b > 1$ (forecast too reactive):} your model is chasing noise. Try increasing regularization, using a longer lookback window, or smoothing the forecast with an exponential moving average.
  \item \textbf{$a > 0$ (systematic under-prediction):} check for retransformation bias first if you forecast in log space (Section~\ref{sec:eval-retransformation}). If that is not the issue, add a bias correction term or recalibrate the intercept.
  \item \textbf{$a < 0$ (systematic over-prediction):} less common in volatility forecasting, but check whether your features include stale high-vol observations that inflate the forecast.
\end{itemize}
\end{keyidea}
```

- [ ] **Step 3: Verify the file compiles**

Run:
```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/chapters/16-forecast-evaluation.tex
git commit -m "feat(ch16): add QLIKE/MZ relationship analogy and MZ prescription box"
```

---

### Task 5: Add DM test interpretation and DM vs MCS relationship

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:526` (after DM worked example)
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:539-541` (expand MCS opening paragraph)

- [ ] **Step 1: Add interpretation paragraph after DM worked example (after line 526)**

Find:
```
Report the $p$-value and let the reader decide.
\end{workedexample}
```

Replace with:
```latex
Report the $p$-value and let the reader decide.

\textbf{What this tells you.}
DM $= 2.09$, $p = 0.037$ means you can credibly claim LightGBM beats HAR at the 5\% significance level.
This $p$-value goes in your results table next to the $\QLIKE$ numbers.
If $p$ had been 0.15, the $\QLIKE$ improvement would be real in your sample but you could not rule out that a different sample would reverse it; you would need more data or a larger improvement before claiming victory.
If you have a directional hypothesis (ML should beat HAR, not vice versa), a one-sided test is appropriate, halving the $p$-value to $0.037/2 = 0.018$.
\end{workedexample}
```

- [ ] **Step 2: Expand MCS opening to clarify DM vs MCS relationship (lines 539-541)**

Find:
```
The Diebold--Mariano test compares models in pairs.
With $M$ models, you would need $\binom{M}{2}$ pairwise tests, and the more tests you run, the more likely you are to find a ``significant'' difference by chance.
The Model Confidence Set solves this by comparing all models simultaneously.
```

Replace with:
```latex
The Diebold--Mariano test compares models in pairs.
Use it when you have a specific pairwise claim to make (``my ML model beats HAR'').
With $M$ models, you would need $\binom{M}{2}$ pairwise tests, and the more tests you run, the more likely you are to find a ``significant'' difference by chance.
The Model Confidence Set solves this by comparing all models simultaneously.
Use it when you have a model zoo and need to know which ones to keep and which to discard.
DM is your scalpel for targeted claims; MCS is your filter for the full candidate set.
```

- [ ] **Step 3: Verify the file compiles**

Run:
```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/chapters/16-forecast-evaluation.tex
git commit -m "feat(ch16): add DM interpretation paragraph and DM vs MCS relationship"
```

---

### Task 6: Add MCS survivor guidance and MCS p-value clarification

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:643` (after MCS "humility device" keyidea)

- [ ] **Step 1: Add survivor guidance keyidea box (after line 643)**

Find:
```
If your fancy model is in the same MCS as HAR, be honest about it.
\end{keyidea}
```

Insert after it:
```latex

\begin{keyidea}[What to Do When Multiple Models Survive]
When four models survive the MCS, you cannot rank among them statistically.
Choose among survivors using secondary criteria: simplicity (HAR is easier to explain to a portfolio manager than LightGBM), computational cost (GARCH fits in seconds versus minutes), interpretability (can you explain why the forecast changed?), or economic value in a downstream application (Chapter~\ref{ch:applications}).
The MCS does not pick your model; it eliminates the ones you should not pick.

The MCS $p$-values for surviving models (1.000, 0.482, 0.312, 0.551 in the table above) are \emph{not} a ranking.
They indicate how far each model is from elimination: a $p$-value of 0.312 means GARCH would be eliminated at $\alpha = 0.30$ but survives at $\alpha = 0.10$.
Do not treat these as confidence scores or use them to rank survivors.
\end{keyidea}
```

- [ ] **Step 2: Verify the file compiles**

Run:
```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 3: Commit**

```bash
git add vol-learning-guide/chapters/16-forecast-evaluation.tex
git commit -m "feat(ch16): add MCS survivor guidance and p-value clarification"
```

---

### Task 7: Add DSR recovery path

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:902` (after DSR worked example)

- [ ] **Step 1: Add recovery path paragraph (after line 902)**

Find:
```
You cannot reject the null that this is the luckiest of 20 random strategies.
\end{workedexample}
```

Replace with:
```latex
You cannot reject the null that this is the luckiest of 20 random strategies.

\textbf{What this tells you.}
$\DSR \approx 0$ means your best strategy does not survive multiple-testing correction.
This does not mean volatility forecasting is hopeless; it means you tested too many strategies relative to your sample size.
Your options:
\begin{enumerate}[nosep]
  \item \textbf{Get more data.} A longer backtest period increases $T$, which widens the numerator of the DSR formula and makes it easier to clear the luck threshold.
  \item \textbf{Test fewer strategies.} Use stronger priors about which feature sets to try, so $N$ stays small and $\SR_0 = \sqrt{2 \ln N}$ stays low.
  \item \textbf{Pre-register.} Commit to a single strategy before backtesting, setting $N = 1$ and $\SR_0 = 0$. The DSR then reduces to a standard Sharpe ratio test.
  \item \textbf{Shift the claim.} Accept that you cannot make a statistical Sharpe claim and justify the strategy on economic grounds (e.g., cost-aware backtest, Chapter~\ref{ch:applications}) rather than statistical grounds.
\end{enumerate}
\end{workedexample}
```

- [ ] **Step 2: Verify the file compiles**

Run:
```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 3: Commit**

```bash
git add vol-learning-guide/chapters/16-forecast-evaluation.tex
git commit -m "feat(ch16): add DSR recovery path after worked example"
```

---

### Task 8: Add embargo justification and retransformation-QLIKE link

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:755` (after embargo definition)
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:301` (after retransformation worked example)

- [ ] **Step 1: Add embargo sizing justification (after line 755)**

Find:
```
A typical embargo is 1--2\% of total sample size.
\end{definition}
```

Replace with:
```latex
A typical embargo is 1--2\% of total sample size.
The embargo length should cover the autocorrelation decay of your features.
For HAR features (which use lags up to 22 days), the serial correlation in $\RV$ drops below 0.05 within about 5--10 days, so 1--2\% of a typical 1,000--2,500 day sample (10--50 days) is conservative.
If you use features with longer memory (e.g., monthly moving averages or regime indicators), increase the embargo accordingly.
\end{definition}
```

- [ ] **Step 2: Add retransformation-QLIKE connection (after line 300-301)**

Find:
```
For 22-day-ahead forecasts with $\hat{\sigma}^2_\varepsilon \approx 0.35$, it reaches $\exp(0.175) \approx 1.19$, nearly a 20\% adjustment.
\end{workedexample}
```

Replace with:
```latex
For 22-day-ahead forecasts with $\hat{\sigma}^2_\varepsilon \approx 0.35$, it reaches $\exp(0.175) \approx 1.19$, nearly a 20\% adjustment.

\textbf{Impact on evaluation.}
Without this correction, the 10.5\% systematic under-prediction on a typical 5-day horizon inflates $\QLIKE$ loss by roughly 3--5\% and shows up as $a > 0$ in the Mincer--Zarnowitz regression (Section~\ref{sec:eval-mz}).
Applying the correction is often the single cheapest $\QLIKE$ improvement available: it costs one line of code and zero additional data.
\end{workedexample}
```

- [ ] **Step 3: Verify the file compiles**

Run:
```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/chapters/16-forecast-evaluation.tex
git commit -m "feat(ch16): add embargo justification and retransformation-QLIKE link"
```

---

### Task 9: Strengthen project connection boxes with concrete actions

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:217-222` (QLIKE project connection)
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:645-650` (MCS project connection)
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:859-863` (DSR project connection)

- [ ] **Step 1: Strengthen QLIKE project connection (lines 217-222)**

Find:
```
Target a 30--80 bps QLIKE improvement over HAR to claim a meaningful result.
\end{projectconnection}
```

Replace with:
```latex
Target a 30--80 bps $\QLIKE$ improvement over HAR to claim a meaningful result.
Report the percentage reduction to two decimal places in your results table, and always pair it with a DM test $p$-value (Section~\ref{sec:eval-dm}).
\end{projectconnection}
```

- [ ] **Step 2: Strengthen MCS project connection (lines 645-650)**

Find:
```
If your LightGBM model and plain HAR both survive in the 90\% MCS, you cannot honestly claim superiority.
```

Replace with:
```latex
If your LightGBM model and plain HAR both survive in the 90\% MCS, you cannot honestly claim superiority; report them as statistically equivalent and justify your model choice on secondary criteria (interpretability, computational cost, economic value).
```

- [ ] **Step 3: Strengthen DSR project connection (lines 859-863)**

Find:
```
DSR $> 0.95$ is the bar for a credible backtest result.
\end{projectconnection}
```

Replace with:
```latex
DSR $> 0.95$ is the bar for a credible backtest result.
If DSR $< 0.95$, do not claim the strategy has skill; report the DSR value and the number of trials $N$ alongside the raw Sharpe so readers can judge for themselves.
\end{projectconnection}
```

- [ ] **Step 4: Verify the file compiles**

Run:
```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 5: Commit**

```bash
git add vol-learning-guide/chapters/16-forecast-evaluation.tex
git commit -m "feat(ch16): add concrete actions to project connection boxes"
```

---

### Task 10: Add transition before "What Doesn't Work" section

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex:921-924` (section opening)

- [ ] **Step 1: Add transition paragraph**

Find:
```
% ══════════════════════════════════════════════════════════════
\section{What Doesn't Work}
\label{sec:eval-pitfalls}
% ══════════════════════════════════════════════════════════════
```

The current text after this section heading starts with "This chapter has given you the right tools." (line 925). Insert before that line:

```latex
You now have the full evaluation toolkit: a loss function ($\QLIKE$), a diagnostic (MZ), a pairwise test (DM), a multi-model filter (MCS), a leakage-proof CV procedure, and a multiple-testing correction (DSR).
```

So the paragraph reads: "You now have the full evaluation toolkit: a loss function ($\QLIKE$), a diagnostic (MZ), a pairwise test (DM), a multi-model filter (MCS), a leakage-proof CV procedure, and a multiple-testing correction (DSR). This chapter has given you the right tools. This section catalogs the wrong ones, so you can recognize them in other people's work and avoid them in your own."

Actually, the existing text on line 925-926 already says this well. Find:

```
This chapter has given you the right tools.
This section catalogs the wrong ones, so you can recognize them in other people's work and avoid them in your own.
```

Replace with:
```latex
You now have the full evaluation toolkit: a loss function ($\QLIKE$), a diagnostic (MZ), a pairwise test (DM), a multi-model filter (MCS), a leakage-proof CV procedure, and a multiple-testing correction (DSR).
This section catalogs the mistakes these tools are designed to prevent, so you can recognize them in other people's work and avoid them in your own.
```

- [ ] **Step 2: Verify the file compiles**

Run:
```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex
```

- [ ] **Step 3: Commit**

```bash
git add vol-learning-guide/chapters/16-forecast-evaluation.tex
git commit -m "feat(ch16): strengthen transition before 'What Doesn't Work' section"
```

---

### Task 11: Final compilation and visual check

**Files:**
- Compile: `vol-learning-guide/main.tex` (full build with bibtex)

- [ ] **Step 1: Full compile with bibtex**

Run:
```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
```
Expected: clean compilation, all cross-references and citations resolved.

- [ ] **Step 2: Check for overfull/underfull boxes**

Scan the log for `Overfull` warnings in Chapter 16 specifically:
```bash
grep -i "overfull\|underfull" vol-learning-guide/main.log | grep -i "16-forecast"
```
Fix any overfull hbox warnings by adjusting line breaks in the new content.

- [ ] **Step 3: Commit the compiled PDF**

```bash
git add vol-learning-guide/main.pdf
git commit -m "chore: recompile vol-learning-guide with ch16 clarity improvements"
```

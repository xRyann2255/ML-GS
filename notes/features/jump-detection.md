# Jump Detection

What we've learned about identifying and measuring jumps in our data.

## Findings

(To be filled as we explore data)

## Questions to Answer

- How frequent are jumps in our asset universe? Daily? Weekly?
- How large are they relative to continuous variation?
- Does separating C and J components actually help forecasting on our data?
- Which jump test (BNS, Lee-Mykland, threshold) works best at our data frequency?

## Deep Research Findings (2026-05-06)

**Jump component persistence and forecasting impact:**
- Andersen, Bollerslev & Diebold (2007, RES) "Roughing It Up": decompose RV = continuous + jump. The jump component is highly important but less persistent than the continuous component -- this drives the HAR-RV-J and HAR-RV-CJ extensions (`andersen-bollerslev-diebold-2007-roughing` in bibliography)
- Implication: jump features help short-horizon forecasts more than long-horizon

**Earnings and event-driven jumps:**
- Lee (2012): earnings announcements almost always trigger jumps -- one of the most reliable event-driven vol signals
- Lee-Mykland (2008, RFS) intraday jump test is the workhorse for academic event studies (`lee-mykland-2008` in bibliography)

**Standard tools:**
- BNS bipower variation test and Lee-Mykland (2008) intraday test are the two standard jump detection tools
- Ait-Sahalia & Jacod (2009, Annals of Statistics) provide alternative tests based on power variation ratios

## Fund Assessment Calculation Methods

This document explains the two primary assessment methods used by the script to rank funds. The input data for these calculations is assumed to be `log10` of normalized fund prices, where the latest price for each fund is normalized to 1 (making its `log10` value 0).

### 1. Best Long-Term Growth Assessment

This assessment aims to identify funds with strong overall historical performance, while penalizing those with poor recent trends.

**Core Calculation Steps:**

1.  **"All Dates" Return**:
    * For each fund, the script first determines the earliest available data point (`L_earliest_past`) and the latest data point (`L_current`). Due to normalization, `L_current` should be 0.
    * The percentage return over the entire available history of the fund is calculated as:
        $Return_{All Dates} = 10^{(L_{current} - L_{earliest\_past})} - 1$
    * This `Return_{All Dates}` forms the base score for the long-term assessment.

2.  **Penalty for Poor 1-Year Performance**:
    * The 1-year return (`Return_{1y}`) is calculated similarly: $Return_{1y} = 10^{(L_{current} - L_{1y\_past})} - 1$.
    * A threshold (`LONG_TERM_AD_1Y_THRESHOLD`) is defined (currently 0.0, meaning 0% return).
    * If `Return_{1y}` is less than this threshold, a penalty is calculated:
        $Shortfall_{1y} = LONG\_TERM\_AD\_1Y\_THRESHOLD - Return_{1y}$
        $Penalty_{1y} = Shortfall_{1y} \times |Return_{All Dates}| \times LONG\_TERM\_AD\_1Y\_PENALTY\_FACTOR$
        (The `LONG_TERM_AD_1Y_PENALTY_FACTOR` is currently 0.5).
    * This penalty is subtracted from the base score. The scaling by `|Return_{All Dates}|` makes the penalty proportionally more significant for funds that had high overall returns but poor recent 1-year performance.

3.  **Penalty for Significant Recent (2-Month) Loss**:
    * The 2-month return (`Return_{2m}`) is calculated.
    * A threshold (`LONG_TERM_AD_2M_THRESHOLD`) is defined (currently -0.05, meaning -5% return).
    * If `Return_{2m}` is less than this threshold, an additional penalty is calculated:
        $LossBeyondThreshold_{2m} = |Return_{2m} - LONG\_TERM\_AD\_2M\_THRESHOLD|$
        $Penalty_{2m} = LossBeyondThreshold_{2m} \times |Return_{All Dates}| \times LONG\_TERM\_AD\_2M\_PENALTY\_FACTOR$
        (The `LONG_TERM_AD_2M_PENALTY_FACTOR` is currently 0.3).
    * This penalty is also subtracted from the (potentially already penalized) score.

4.  **Final Ranking**:
    * The final adjusted score for long-term performance is:
        $Score_{LongTerm} = Return_{All Dates} - Penalty_{1y} - Penalty_{2m}$
    * Funds are ranked in descending order based on this $Score_{LongTerm}$.

**Configurable Parameters (Currently Constants):**
* `LONG_TERM_AD_1Y_THRESHOLD`: Threshold for 1-year return penalty.
* `LONG_TERM_AD_1Y_PENALTY_FACTOR`: Multiplier for the 1-year penalty.
* `LONG_TERM_AD_2M_THRESHOLD`: Threshold for 2-month return penalty.
* `LONG_TERM_AD_2M_PENALTY_FACTOR`: Multiplier for the 2-month penalty.
    These could potentially be made configurable via command-line switches.

### 2. Best Lag-Adjusted Short-Term Assessment

This assessment aims to identify funds with strong recent performance, adjusted for volatility and considering a lag in data availability and fund switching.

**Core Calculation Steps:**

1.  **Period Returns**:
    * Percentage returns are calculated for several lookback periods: 1-month (`1m`), 3-month (`3m`), 6-month (`6m`), and 1-year (`1y`).
    * The formula used is: $Return_{period} = 10^{(L_{current} - L_{period\_past})} - 1$.

2.  **Z-Scores**:
    * For each of these lookback periods (1m, 3m, 6m, 1y), a Z-score is calculated for every fund's return.
    * The Z-score measures how many standard deviations a fund's return is from the average return of all funds for that specific period.
        $Z_{fund, period} = \frac{(Return_{fund, period} - \mu_{period})}{\sigma_{period}}$
        where:
        * $Return_{fund, period}$ is the return of the specific fund for the period.
        * $\mu_{period}$ is the average return of *all* funds for that period.
        * $\sigma_{period}$ is the standard deviation of returns of *all* funds for that period.
    * A higher Z-score indicates better performance relative to peers for that period.

3.  **Weighted Score**:
    * A final "Lag-Adjusted Score" is calculated for each fund by taking a weighted sum of its Z-scores across the different periods.
    * The weights are defined in the `LAG_ADJ_WEIGHTS` dictionary in the script (currently: 1m: 0.40, 3m: 0.35, 6m: 0.20, 1y: 0.05).
        $Score_{LagAdj} = (W_{1m} \times Z_{1m}) + (W_{3m} \times Z_{3m}) + (W_{6m} \times Z_{6m}) + (W_{1y} \times Z_{1y})$
    * If a fund has a NaN Z-score for a period (e.g., due to insufficient data), that Z-score is treated as 0 for the weighted sum.

4.  **Final Ranking**:
    * Funds are ranked in descending order based on this $Score_{LagAdj}$.

**Configurable Parameters (Currently Constants):**
* `LAG_ADJ_WEIGHTS`: The dictionary defining the weights for each period in the Z-score sum.
    These weights could potentially be made configurable, for example, by allowing the user to input a comma-separated list of weights corresponding to the 1m, 3m, 6m, and 1y periods.

This approach for the lag-adjusted score prioritizes shorter-term relative performance (higher Z-scores) and combines these into an overall momentum indicator.

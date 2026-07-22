# Confidence Interval & t-Distribution Guide

This document explains how confidence intervals (CI) are computed in the plot scripts.

## What is a Confidence Interval?

When you run an experiment 5 times and get 5 different throughput values, the
mean alone doesn't tell the whole story. A **95% confidence interval** gives
you a range: "I am 95% confident the true mean lies within this range."

A **narrow CI** = your results are consistent across runs.
A **wide CI** = your results vary a lot between runs.

## The Formula

```
CI = mean +/- t_critical * (s / sqrt(n))
```

Where:
- `mean` = average of your measurements
- `s` = standard deviation (how spread out the values are)
- `sqrt(n)` = square root of sample size
- `t_critical` = a multiplier from the t-distribution table
- `s / sqrt(n)` = **standard error** (SE)
- `t_critical * s / sqrt(n)` = **margin of error** (half-width of CI)

## Why t-Distribution, Not Normal (z)?

When sample size is large (n > 30), you can use the normal distribution
(z = 1.96 for 95% CI). But with small samples (n = 5), the normal
distribution **underestimates** uncertainty. The t-distribution has **heavier
tails**, producing wider (more conservative) intervals.

| n  | df = n-1 | t-critical (95%) | z (normal) |
|----|----------|------------------|------------|
| 3  | 2        | 12.706           | 1.96       |
| 5  | 4        | 2.776            | 1.96       |
| 10 | 9        | 2.262            | 1.96       |
| 30 | 29       | 2.045            | 1.96       |
| inf| inf      | 1.96             | 1.96       |

As n grows, t converges to z (normal distribution).

## What is df (Degrees of Freedom)?

`df = n - 1`

It represents the number of independent pieces of information. When you
compute the mean from n values, you "use up" one degree of freedom (because
the n values must sum to n * mean). So only n-1 values are free to vary.

Example: 5 runs -> df = 4

## One-Tailed vs Two-Tailed

**Two-tailed** means you care about both directions (higher AND lower):

```
       2.5%                95%                2.5%
    |-------|==========================|-------|
   -x                                    +x
```

**One-tailed** means you only care about one direction:

```
                                     95%              5%
                  |==========================|-------|
                                                       +x
```

For confidence intervals, you need **two-tailed** because the CI extends
both above and below the mean. If you used one-tailed, the interval would
be too narrow and wouldn't actually cover 95% of the distribution.

In this project, all CIs use two-tailed t-values.

## How It Works in Code

### `config.py`

```python
T_TABLE = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}
#           df=1     df=2     df=3     df=4     df=5

def t_critical(n):
    return T_TABLE.get(n, 1.96)  # fallback to z if n > 6
```

Key = sample size n. Value = two-tailed t-critical for 95% confidence
with df = n - 1.

### `mean_ci(vals)` -- single metric CI

```python
def mean_ci(vals):
    n = len(vals)
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)  # sample variance
    std = math.sqrt(var)
    half = t_critical(n) * std / math.sqrt(n)            # margin of error
    return mean, mean - half, mean + half
```

### `compute_ci_from_dir(data_dir)` -- time-series CI

Groups throughput values by timestamp across all runs, then applies the
same formula at each time point.

## Worked Example (n = 5 runs)

Suppose you ran a cache experiment 5 times and got these throughputs:

```
Run 1: 13020 txns/s
Run 2: 13524 txns/s
Run 3: 13702 txns/s
Run 4: 13769 txns/s
Run 5: 13936 txns/s
```

Step 1: Mean
```
mean = (13020 + 13524 + 13702 + 13769 + 13936) / 5 = 13590.2
```

Step 2: Sample standard deviation (divide by n-1 = 4)
```
var = [(13020-13590.2)^2 + (13524-13590.2)^2 + ...] / 4 = 139431.7
std = sqrt(139431.7) = 373.4
```

Step 3: Margin of error
```
t_critical(5) = 2.776
SE = 373.4 / sqrt(5) = 167.0
margin = 2.776 * 167.0 = 463.5
```

Step 4: CI
```
CI = 13590.2 +/- 463.5
   = [13126.7, 14053.7]
```

If you had used z = 1.96 instead of t = 2.776:
```
margin = 1.96 * 167.0 = 327.3  (30% narrower -- too optimistic!)
```

## Scripts use CI with t distribution

| Script | Uses CI? | How? |
|--------|----------|------|
| `throughput.py` | No | Single run, no error bars |
| `latency.py` | No | Single run, bar chart from summary |
| `exp1/compare-throughput.py` | Yes | `compute_ci_from_dir()` -> fill_between |
| `exp1/compare-latency.py` | Yes | `mean_ci()` -> bar error bars |
| `exp3/mmm-throughput.py` | Yes | `mean_ci()` -> scatter error bars |
| `exp3/mmm-responsetime.py` | Yes | `mean_ci()` -> scatter error bars |
| `exp2/compare-throughput.py` | From CSV | Reads pre-computed CI from avg.csv |

## Common Pitfalls

1. **Using z instead of t for small samples** -- makes CI too narrow,
   overstating confidence. This project correctly uses t.

2. **Dividing variance by n instead of n-1** -- this gives biased
   (too small) variance. The code correctly uses n-1 (Bessel's correction).

3. **Sample size > 6** -- the T_TABLE only goes up to n=6. For n > 6,
   the code falls back to z = 1.96. In this project, n is always 5
   (5 experiment runs), so this never triggers.

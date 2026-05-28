# Brain teaser — cross-judge disagreements (run2)

Same run2 model outputs, judged by deepseek-v4-pro / gemini-3.1-flash-lite / claude-sonnet-4.6.

Brainteaser cells: 100  |  3-judge disagreements: **12**

NOTE: some "disagreements" are the `Line 3: YES` PARSER BUG (judge meant YES
but the old `startswith("YES")` parser recorded NO). Those are flagged [PARSER BUG].
Genuine judging differences are flagged [REAL].

---

## claude-sonnet-4.6 — b02   [PARSER BUG: sonnet]

- **Expected:** `14 tests in the worst case. Use decreasing interval sizes 14, 13, 12, 11, ... . Test the first copy at scenarios 14, 27, 39, 50, 60, 69, 77, 84, 90, 95, 99, and 100. If the first copy becomes corrupted, use the second copy to search linearly between the previous safe scenario and the failure scenario.`
- **Verdicts:** deepseek=NO | gemini=YES | sonnet=NO

**Model response (last 600 chars):**
```
 test **linearly** from the previous safe scenario upward. The remaining tests available = $14 - (k-1) - 1 = 14 - k$, which exactly covers the gap of size $14 - k$.

**Worst case in every branch = exactly 14 tests.**

## Summary

> **The minimum worst-case number of tests is 14.**
>
> **Strategy:** Test Copy 1 at scenarios 14, 27, 39, 50, 60, 69, 77, 84, 90, 95, 99, 100 (gaps of 14, 13, 12, …). When Copy 1 first corrupts, test Copy 2 one-by-one from just above the last safe scenario. This guarantees identifying N in at most **14 tests** regardless of where the threshold lies.

Final Answer: 14
```

**Judge `deepseek`** — extracted: `14`
```
14
Missing required strategy; only the number 14 committed.
NO
```

**Judge `gemini`** — extracted: `14`
```
14
The model correctly identifies 14 and the optimal strategy.
YES
```

**Judge `sonnet`** — extracted: `Line 1: 14 tests; strategy: test at 14,27,39,50,60,69,77,84,90,95,99,100 with decreasing intervals`
```
Line 1: 14 tests; strategy: test at 14,27,39,50,60,69,77,84,90,95,99,100 with decreasing intervals
Line 2: Matches expected answer exactly in value and strategy
Line 3: YES
```

---

## claude-sonnet-4.6 — b10   [PARSER BUG: deepseek]

- **Expected:** `20 minutes`
- **Verdicts:** deepseek=NO | gemini=YES | sonnet=YES

**Model response (last 600 chars):**
```
## Setting Up the Problem

**Script A's rate:** 1 file per hour
**Script B's rate:** 2 files per hour

**Combined rate:** 1 + 2 = **3 files per hour**

## Solving for Time

$$\text{Time} = \frac{\text{Work}}{\text{Rate}} = \frac{1 \text{ file}}{3 \text{ files/hour}} = \frac{1}{3} \text{ hour}$$

## Answer

It will take them **1/3 of an hour (20 minutes)** to clean 1 file-equivalent of work together.

Final Answer: 1/3 hour (20 minutes)
```

**Judge `deepseek`** — extracted: `Line 1: 1/3 hour (20 minutes)`
```
Line 1: 1/3 hour (20 minutes)
Line 2: Matches expected answer (20 minutes) exactly.
Line 3: YES
```

**Judge `gemini`** — extracted: `1/3 hour (20 minutes)`
```
1/3 hour (20 minutes)
The model correctly calculated 1/3 hour, which is 20 minutes.
YES
```

**Judge `sonnet`** — extracted: `1/3 hour (20 minutes)`
```
1/3 hour (20 minutes)
1/3 hour = 20 minutes, exact match
YES
```

---

## gemini-2.5-flash — b02   [REAL]

- **Expected:** `14 tests in the worst case. Use decreasing interval sizes 14, 13, 12, 11, ... . Test the first copy at scenarios 14, 27, 39, 50, 60, 69, 77, 84, 90, 95, 99, and 100. If the first copy becomes corrupted, use the second copy to search linearly between the previous safe scenario and the failure scenario.`
- **Verdicts:** deepseek=NO | gemini=YES | sonnet=NO

**Model response (last 600 chars):**
```
 8 = 77$
$x_8 = 77 + 7 = 84$
$x_9 = 84 + 6 = 90$
$x_{10} = 90 + 5 = 95$
$x_{11} = 95 + 4 = 99$
$x_{12} = 99 + 3 = 102$. (We can cap this at 100).
$x_{13} = 102 + 2 = 104$. (We can cap this at 100).
$x_{14} = 104 + 1 = 105$. (We can cap this at 100).

Let's use $k=14$.
The test points for Copy 1 are $x_1, x_2, ..., x_{14}$.
$x_1 = 14$.
$x_2 = 14 + (14-1) = 27$.
$x_3 = 27 + (14-2) = 39$.
...
$x_{14} = x_{13} + (14-13) = x_{13} + 1$.
The last test point for Copy 1 is $x_{14} = 105$. Since the maximum scenario is 100, we only test up to 100.
So the actual test points for Copy 1 are: 14, 27, 39, 50
```

**Judge `deepseek`** — extracted: `N/A`
```
N/A
Response ends mid-sentence without a committed final answer
NO
```

**Judge `gemini`** — extracted: `14 tests; 14, 27, 39, 50, 60, 69, 77, 84, 90, 95, 99, 100`
```
14 tests; 14, 27, 39, 50, 60, 69, 77, 84, 90, 95, 99, 100
The model correctly identified 14 tests and the sequence.
YES
```

**Judge `sonnet`** — extracted: `# The Minimum Worst-Case Testing Strategy`
```
# The Minimum Worst-Case Testing Strategy

## Setting Up the Framework

This is the classic "egg drop" problem with 2 copies and 100 scenarios.

**Key insight:** If Copy 1 breaks at test point $x_i$, we must use Copy 2 to search linearly through the interval $(x_{i-1}, x_i)$. The total tests equal:
$$\underbrace{i}_{\text{Copy 1 tests}} + \underbrace{(x_i - x_{i-1} - 1)}_{\text{Copy 2 tests}}$$

## Deriving the Optimal Strategy

Let $M$ = worst-case number of tests. To keep the worst case equal across all scenarios, each successive interval must **shrink by 1** (since each additional Copy 1 test "uses up" one test from the budget).

**Interval sizes:** $M,\ (M-1),\ (M-2),\ \ldots$

The test points for Copy 1 are:
| Test # | Scenario |
|--------|----------|
| 1 | $M$ |
| 2 | $M + (M-1)$ |
| 3 | $M + (M-1) + (M-2)$ |
| $k$ | $\sum_{j=0}^{k-1}(M-j) = kM - \frac{k(k-1)}{2}$ |

## Finding the Minimum M

We need the test points to cover all 100 scenarios:
$$M + (M-1) + (M-2) + \cdots \geq 100$$
$$\frac{M(M+1)}{2} \geq 100$$

Solving: $M(M+1) \geq 200$

- $M = 13$: $13 \times 14 = 182 < 200$ ❌  
- $M = 14$: $14 \times 15 = 210 \geq 200$ ✅

## **Minimum worst-case = 14 tests**

## The Explicit Strategy

Test **Copy 1** at these scenarios (intervals of 14, 13, 12, 11, ...):

| Copy 1 Test | Scenario | Interval Size |
|-------------|----------|---------------|
| 1 | **14** | 14 |
| 2 | **27** | 13 |
| 3 | **39** | 12 |
| 4 | **50** | 11 |
| 5 | **60** | 10 |
| 6 | **69** | 9 |
| 7 | **77** | 8 |
| 8 | **84** | 7 |
| 9 | **90** | 6 |
| 10 | **95** | 5 |
| 11 | **99** | 4 |
| 12 | **100** | 1 |

**If Copy 1 breaks** at scenario $x_i$: use Copy 2 to test linearly upward from $x_{i-1}+1$.

**Worst-case verification** (Copy 1 breaks at scenario 14, Copy 2 tests 1–13):
- 1 test (Copy 1) + 13 tests (Copy 2) = **14 tests** ✓

**Another worst case** (Copy 1 breaks at 27, Copy 2 tests 15–26):
- 2 tests (Copy 1) + 12 tests (Copy 2) = **14 tests** ✓

Every interval is designed so that $i + (\text{interval size} - 1) = 14$.

## Summary

> **The minimum worst-case number of tests is 14.**  
> Test Copy 1 at scenarios **14, 27, 39, 50, 60, 69, 77, 84, 90, 95, 99, 100** using decreasing intervals of size 14, 13, 12, …  
> When Copy 1 first breaks, search linearly with Copy 2 in the preceding interval.
```

---

## gemini-2.5-flash — b05   [REAL]

- **Expected:** `N-1`
- **Verdicts:** deepseek=NO | gemini=YES | sonnet=YES

**Model response (last 600 chars):**
```
 M_i says "Yes". We discard M_i (C). Keep M_j (C).
         R_S -> R_S. C_S -> C_S - 1.
      ii. M_i says "No". We discard M_j (C). Keep M_i (C).
         R_S -> R_S. C_S -> C_S - 1.

Let's track the number of reliable monitors (R_S) and compromised monitors (C_S) in the set S.
In each step, we remove one monitor from S.
If M_i is reliable:
  - If M_i says "Yes" (M_j is reliable): (R_S, C_S) -> (R_S-1, C_S). R_S - C_S decreases by 1.
  - If M_i says "No" (M_j is compromised): (R_S, C_S) -> (R_S, C_S-1). R_S - C_S increases by 1.
If M_i is compromised:
  - If M_i says "Yes" (M_j is reliable or
```

**Judge `deepseek`** — extracted: `N/A`
```
N/A
No committed final answer found in tail.
NO
```

**Judge `gemini`** — extracted: `N-1`
```
N-1
The problem is equivalent to finding a source in a graph, which requires N-1 queries in the worst case.
YES
```

**Judge `sonnet`** — extracted: `Final Answer: N-1`
```
Final Answer: N-1

N-1
Matches expected answer exactly.
YES
```

---

## gemini-3.1-flash-lite — b02   [REAL]

- **Expected:** `14 tests in the worst case. Use decreasing interval sizes 14, 13, 12, 11, ... . Test the first copy at scenarios 14, 27, 39, 50, 60, 69, 77, 84, 90, 95, 99, and 100. If the first copy becomes corrupted, use the second copy to search linearly between the previous safe scenario and the failure scenario.`
- **Verdicts:** deepseek=NO | gemini=YES | sonnet=YES

**Model response (last 600 chars):**
```
{27.3}{2} \approx 13.65$

Since $x$ must be an integer, we round up to $x = 14$.
Checking: $\frac{14(15)}{2} = 105$, which is $\ge 100$.
Checking $x=13$: $\frac{13(14)}{2} = 91$, which is $< 100$.

Thus, the minimum worst-case number of tests is 14.

The strategy is to test at intervals that decrease by 1 each time:
Test 1: Scenario 14
If it breaks, test 1-13 linearly (worst case 14 tests).
If it survives, test at $14 + 13 = 27$.
If it breaks, test 15-26 linearly (worst case $2 + 12 = 14$ tests).
If it survives, test at $27 + 12 = 39$, and so on, until the threshold is found.

Final Answer: 14
```

**Judge `deepseek`** — extracted: `14`
```
14
Missing testing strategy; committed only the number
NO
```

**Judge `gemini`** — extracted: `14`
```
14
The model correctly identified 14 as the minimum tests.
YES
```

**Judge `sonnet`** — extracted: `14`
```
14
Matches the expected minimum worst-case number of tests.
YES
```

---

## gemini-3.1-flash-lite — b06   [REAL]

- **Expected:** `21`
- **Verdicts:** deepseek=NO | gemini=YES | sonnet=YES

**Model response (last 600 chars):**
```
$kN - k^2 + k > Nk - N$
$-k^2 + k + N > 0$
$k^2 - k - N < 0$.
For $N=400$, $k^2 - k - 400 < 0$.
The roots of $k^2 - k - 400 = 0$ are $k = \frac{1 \pm \sqrt{1 + 1600}}{2} \approx \frac{1 \pm 40.01}{2}$.
The positive root is $\approx 20.5$.
Thus, $p_k$ increases for $k \le 20$ and decreases for $k \ge 21$.
Comparing $p_{20}$ and $p_{21}$:
$p_{21}/p_{20} = \frac{20}{19} \cdot \frac{400-21+1}{400} = \frac{20}{19} \cdot \frac{380}{400} = \frac{20}{19} \cdot \frac{19}{20} = 1$.
Since $p_{21}/p_{20} = 1$, $p_{20} = p_{21}$. Both positions 20 and 21 yield the maximum probability.

Final Answer: 20, 21
```

**Judge `deepseek`** — extracted: `20, 21`
```
20, 21
Expected '21', got '20, 21' extra number
NO
```

**Judge `gemini`** — extracted: `20, 21`
```
20, 21
The model correctly identified that both 20 and 21 are max.
YES
```

**Judge `sonnet`** — extracted: `20, 21`
```
20, 21
Expected is 21; model commits to both 20 and 21.
YES
```

---

## gpt-4o — b02   [REAL]

- **Expected:** `14 tests in the worst case. Use decreasing interval sizes 14, 13, 12, 11, ... . Test the first copy at scenarios 14, 27, 39, 50, 60, 69, 77, 84, 90, 95, 99, and 100. If the first copy becomes corrupted, use the second copy to search linearly between the previous safe scenario and the failure scenario.`
- **Verdicts:** deepseek=NO | gemini=YES | sonnet=YES

**Model response (last 600 chars):**
```
 \frac{-1 + 28.3}{2} \approx 13.65
   \]
   Since \( x \) must be an integer, we round up to \( x = 14 \).

4. **Testing strategy**: Start testing the first copy at scenario 14, then 27 (14 + 13), then 39 (27 + 12), and so on, decreasing the interval by 1 each time. Once the first copy fails, use the second copy to test sequentially from the last safe scenario up to the failure point.

5. **Verify**: The sequence of tests with the first copy is 14, 27, 39, 50, 60, 69, 77, 84, 90, 95, 99. This covers all scenarios up to 100.

Thus, the minimum worst-case number of tests is 14.

Final Answer: 14
```

**Judge `deepseek`** — extracted: `14`
```
14
Missing strategy; expected both number and strategy
NO
```

**Judge `gemini`** — extracted: `14`
```
14
The model correctly identified 14 and the strategy.
YES
```

**Judge `sonnet`** — extracted: `14 tests in the worst case; decreasing intervals 14,13,12,...`
```
14 tests in the worst case; decreasing intervals 14,13,12,...
Matches the key numeric answer and strategy.
YES
```

---

## grok-4.3 — b02   [REAL]

- **Expected:** `14 tests in the worst case. Use decreasing interval sizes 14, 13, 12, 11, ... . Test the first copy at scenarios 14, 27, 39, 50, 60, 69, 77, 84, 90, 95, 99, and 100. If the first copy becomes corrupted, use the second copy to search linearly between the previous safe scenario and the failure scenario.`
- **Verdicts:** deepseek=NO | gemini=YES | sonnet=YES

**Model response (last 600 chars):**
```
cumulative sum reaches or exceeds 100.
- If the first copy survives a test, proceed to the next higher interval with the same remaining budget.
- If the first copy ever corrupts, switch to the second copy and perform a linear scan of the immediately preceding interval (at most 13 additional tests).  

Because every possible value of \(N\) produces a unique pattern of survival/corruption under this schedule, and because the longest path in the decision tree has length 14, the threshold is identified after at most 14 tests in the worst case.

Final Answer: 14 (decremental schedule on first copy)
```

**Judge `deepseek`** — extracted: `14 (decremental schedule on first copy)`
```
14 (decremental schedule on first copy)
Missing explicit second-copy linear search fallback; incomplete strategy description
NO
```

**Judge `gemini`** — extracted: `14 (decremental schedule on first copy)`
```
14 (decremental schedule on first copy)
The answer correctly identifies 14 and the strategy.
YES
```

**Judge `sonnet`** — extracted: `14 (decremental schedule on first copy)`
```
14 (decremental schedule on first copy)
Matches the 14-test answer with correct strategy described
YES
```

---

## grok-4.3 — b03   [PARSER BUG: sonnet]

- **Expected:** `A should intentionally make no effective challenge on the first turn. Its probability of ultimately winning is 25/63, approximately 39.7%.`
- **Verdicts:** deepseek=YES | gemini=YES | sonnet=NO

**Model response (last 600 chars):**
```
frac{25}{63}.
\]
(The continuation values used above are exactly the two-player values already computed.)

Finally consider A's opening turn. Attacking B yields continuation value \((2/3) \cdot (25/63) < 25/63\). Attacking C yields continuation value
\[
\frac{1}{3} \cdot \frac{1}{7} + \frac{2}{3} \cdot \frac{25}{63} = \frac{19}{63} < \frac{25}{63}.
\]
Hence the unique optimal action for A is to pass, after which the continuation value is exactly the quantity \(25/63\) already obtained on B's turn. Consequently A's survival probability under optimal play is \(25/63\).

Final Answer: pass; 25/63
```

**Judge `deepseek`** — extracted: `pass; 25/63`
```
pass; 25/63
Matches expected optimal action (pass) and exact probability 25/63.
YES
```

**Judge `gemini`** — extracted: `pass; 25/63`
```
pass; 25/63
The model correctly identifies the strategy and probability.
YES
```

**Judge `sonnet`** — extracted: `Line 1: pass; 25/63`
```
Line 1: pass; 25/63
Line 2: Matches expected: A passes, wins with 25/63
Line 3: YES
```

---

## qwen3.6-flash — b02   [REAL]

- **Expected:** `14 tests in the worst case. Use decreasing interval sizes 14, 13, 12, 11, ... . Test the first copy at scenarios 14, 27, 39, 50, 60, 69, 77, 84, 90, 95, 99, and 100. If the first copy becomes corrupted, use the second copy to search linearly between the previous safe scenario and the failure scenario.`
- **Verdicts:** deepseek=NO | gemini=YES | sonnet=YES

**Model response (last 600 chars):**
```
5$ (sufficient).

**Testing Strategy:**
- Start by testing at scenario **14**.
- If it breaks, use the second copy to test scenarios 1, 2, 3, ..., 13 sequentially. Worst case: 14 tests.
- If it survives, jump up by 13 to scenario **27**.
- If it breaks at 27, use the second copy to test 15 through 26 sequentially. Worst case: 2 (initial tests) + 12 = 14 tests.
- Continue this pattern, decreasing the jump size by 1 each time it survives: **39, 50, 60, 69, 77, 84, 90, 95, 99, 100**.
- This guarantees that no matter where $N$ lies, the total number of tests will never exceed 14.

Final Answer: 14
```

**Judge `deepseek`** — extracted: `14`
```
14
Missing strategy; only gave number, not full answer.
NO
```

**Judge `gemini`** — extracted: `14`
```
14
The model correctly identified 14 and the strategy.
YES
```

**Judge `sonnet`** — extracted: `14 tests in the worst case, using decreasing intervals 14,13,12,...`
```
14 tests in the worst case, using decreasing intervals 14,13,12,...
Matches the expected answer of 14 with correct strategy.
YES
```

---

## qwen3.6-flash — b07   [REAL]

- **Expected:** `C000000000000061`
- **Verdicts:** deepseek=NO | gemini=YES | sonnet=NO

**Model response (last 600 chars):**
```
, 34
For $k=2$: 7, 4, 10, 7, 13, 10, 16, 13, 1, 16, 4, 19, 7, 22, 10, 25, 13, 1, 16, 4, 19, 7, 22, 10, 25, 13, 1, 16, 4, 19, 7, 22, 10, 25, 13, 28, 16, 31, 19, 34
For $k=3$: 16, 4, 19, 7, 22, 10, 25, 13, 28, 16, 31, 19, 34

It seems that for $k \ge 1$, the sequence for $m=1, 2, \dots$ is related to the sequence for $k-1$.
Let's look at the values for $m=1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40$.
For $k=1$: 4, 4, 1, 7, 4, 1, 7, 4, 10, 7, 13, 10, 16, 13, 1, 16, 4, 19, 7, 22, 10, 25, 13, 1
```

**Judge `deepseek`** — extracted: `N/A`
```
N/A
No final answer in the response; tail truncated.
NO
```

**Judge `gemini`** — extracted: `C000000000000061`
```
C000000000000061
The model correctly identified the pattern and the answer.
YES
```

**Judge `sonnet`** — extracted: `Looking at this problem, I need to find the last remaining crate when every 3rd crate is eliminated (positions 3, 6, 9, ... in each cycle are removed), while positions 1 and 2 cycle back.`
```
Looking at this problem, I need to find the last remaining crate when every 3rd crate is eliminated (positions 3, 6, 9, ... in each cycle are removed), while positions 1 and 2 cycle back.

This is a variant of the Josephus problem where every 3rd element is eliminated.

**Setting up the recurrence:**

For the standard Josephus-like problem where every 3rd person is eliminated, with N people, the position of the survivor satisfies:
- J(1) = 0 (0-indexed)
- J(N) = (J(N-1) + 3) mod N

But here, the "cleared" crates (positions 1 and 2 in each cycle) go to the back, while position 3 is eliminated. This means we eliminate every 3rd element starting from position 3.

**Using the known formula for this variant:**

For N = 3^k + m where 0 ≤ m ≤ 3^k, the last survivor (1-indexed) is:
- If m = 0: position 1
- Otherwise: position 3m (if 3m ≤ N)

Wait, let me verify with small cases from the simulation in my analysis:
- N = 3^1 + 1 = 4 → survivor = 4 = 3×1+1? No, 3×1=3, not 4.

Let me re-examine the pattern from simulation:
- N = 3^k: survivor = 1
- N = 3^k + m: survivor = 3m + adjustment based on k

From the computed sequences, for N = 3^k + m:
- The survivor position = 3m × (some factor based on k) mod N + 1

After careful analysis of the pattern, for N = 3^30 + 40:

The recurrence for the Josephus problem with every 3rd eliminated gives:
J(3^k) = 0 (0-indexed, meaning position 1)

For N = 3^30 + 40, using the formula:
- Start with J(3^30) = 0
- Add 40 people: each addition shifts by 3 positions
- J(3^30 + m) = 3m mod (3^30 + m) ... but need to track carefully

From the pattern observed in simulations:
- N = 3^k + m gives survivor = 3m (when 3m ≤ N)

For N = 3^30 + 40:
- 3 × 40 = 120... but let me check: N=40 gives survivor 34, and 3×40=120 > 40.

Re-examining: for N = 3^2 + 40 = 49, survivor = 34 (from k=2, m=40 pattern).
For N = 3^3 + 40 = 67, checking the pattern gives survivor = 61.

The pattern shows that for large k, N = 3^k + 40 gives survivor = 61.

Checking: 61 = 3×40 - 59? No. But 61 appears consistently for m=40 when k ≥ 3.

From the k=3 sequence: m=40 → 34... Let me recheck k=3, m=13 → 34, and the sequence for k=3 at m=40 would be 61.

After careful verification through the recurrence, for N = 3^30 + 40, the survivor is crate number **61**.

Final Answer: C000000000000061
```

---

## seed-2.0-lite — b07   [REAL]

- **Expected:** `C000000000000061`
- **Verdicts:** deepseek=NO | gemini=YES | sonnet=YES

**Model response (last 600 chars):**
```
 on cycle 1.
---
### Step 4: Outcome for Exact Power-of-3 Queues
For any queue of size $3^k$ starting on cycle 1, the first element of the queue is always the first crate processed in every subsequent pass. It is never culled, and is the final surviving crate after all passes reduce the queue to one element. This holds because the first crate is always in the clear position of the cycle, so it is retained in every pass until all other crates are culled.
---
### Step 5: Final Result
The first element of the $3^{26}$ queue is original crate 61, which is the last remaining crate.
Final Answer: 61
```

**Judge `deepseek`** — extracted: `61`
```
61
Missing 'C' and leading zeros; expected full label C000000000000061
NO
```

**Judge `gemini`** — extracted: `C000000000000061`
```
C000000000000061
The model identified the correct crate number.
YES
```

**Judge `sonnet`** — extracted: `C000000000000061`
```
C000000000000061
Model says 61, expected label C000000000000061
YES
```

---

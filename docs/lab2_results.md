# Lab 2 – Results

Project: global burden of endometriosis (IHME GBD 2023) and economic development / health spending (World Bank), 1990–2023.

## Task 2.1 – Exploration

See `notebooks/lab2_explore.ipynb`. IHME has no missing values (204 locations x 34 years x 9 indicators = 62,424 rows). World Bank has 36,176 rows (4 indicators x 266 entities x 34 years); missing values: GDP per capita 4.4 %, fertility rate 0.4 %, health expenditure (both indicators) 37.1 %, mainly because the series start in 2000.

## Cleaning summary (what `clean_observations()` removed)

| Source | Rows in | Not a country | Missing value | Rows loaded |
|---|---|---|---|---|
| World Bank (4 indicators) | 36,176 | 6,664 (49 aggregates x 34 years x 4) | 6,042 | 23,470 |
| IHME (9 indicators) | 62,424 | 1,224 (4 locations x 34 years x 9) | 0 | 61,200 |

Four IHME locations (Taiwan, Tokelau, Cook Islands, Niue) have no counterpart in the World Bank country list, so they have no economic data and were excluded. The study therefore covers 200 countries and territories with endometriosis data.

## Task 2.2 – IQR outlier flags

Rule: for each indicator, a value below Q1 − 1.5 x IQR or above Q3 + 1.5 x IQR gets `is_outlier = true`. Rows are flagged, not dropped. The column was added with an Alembic migration (`add_is_outlier_to_observations`).

| Indicator | Rows | Flagged | Share |
|---|---|---|---|
| ENDO_INC_NUM | 6,800 | 799 | 11.8 % |
| ENDO_INC_RATE | 6,800 | 17 | 0.3 % |
| ENDO_INC_ASR | 6,800 | 57 | 0.8 % |
| ENDO_PREV_NUM | 6,800 | 855 | 12.6 % |
| ENDO_PREV_RATE | 6,800 | 64 | 0.9 % |
| ENDO_PREV_ASR | 6,800 | 182 | 2.7 % |
| ENDO_YLD_NUM | 6,800 | 850 | 12.5 % |
| ENDO_YLD_RATE | 6,800 | 63 | 0.9 % |
| ENDO_YLD_ASR | 6,800 | 186 | 2.7 % |
| NY.GDP.PCAP.CD | 7,015 | 657 | 9.4 % |
| SH.XPD.CHEX.GD.ZS | 4,540 | 69 | 1.5 % |
| SH.XPD.CHEX.PC.CD | 4,537 | 632 | 13.9 % |
| SP.DYN.TFRT.IN | 7,378 | 51 | 0.7 % |

Interpretation: absolute counts (`NUM`) and GDP/health spending per person are strongly skewed (very populous or very rich countries), so many rows fall outside the IQR fences even though the values are real. Rates and age-standardized rates have far fewer flags. This is why the rows are flagged and not deleted.

## Task 2.3 – Running the imports twice

Before the second run: `observation` = 84,670 rows, `import_log` = 26 rows.
After the second run: `observation` = 84,670 rows (unchanged), `import_log` = 39 rows (13 new rows, one per indicator).
Both runs printed identical `raw / clean / loaded` counts for all 13 indicators. Query 2 below returned no rows, so the upsert creates no duplicates.

(Also: 84,670 = 9 x 6,800 IHME rows + 23,470 World Bank rows.)

## Task 2.4 – Data quality checks

| # | Check | Result | Explanation |
|---|---|---|---|
| 1 | Countries | 217 countries, 7 regions | One row per economy, no aggregates such as "World"; 7 World Bank regions. |
| 2 | Duplicates on the natural key | no rows | The unique constraint `uq_observation` and the upsert prevent duplicates. |
| 3 | Plausible bounds | all minima/maxima inside the bounds in `clean.py` | e.g. fertility 0.59–8.61 births/woman; health spending 1.2–27.1 % of GDP; incidence ASR 23–183 per 100,000. |
| 4 | Sex codes | FMLE 61,200; BTSX 23,470 | Only known codes. IHME endometriosis data are for females; World Bank data have no sex split, so they are stored as BTSX. `MLE` does not occur. |
| 5 | Missing values / year window | 0 and 0 | Missing values are dropped before loading; all years are in 1990–2023. |
| 6 | Stored vs. last import | equal for all 13 indicators | No rows from earlier imports remain that the last import did not contain. |
| 7 | Countries without health expenditure | 24 economies | Mostly territories and dependencies (e.g. American Samoa, Aruba, Bermuda, Guam, Puerto Rico, Greenland) plus North Korea and Kosovo: the World Bank does not publish this indicator for them. |

Extra check: the lowest GDP per capita values are Iraq 1991 (22.95 current US$) and 1992 (30.25), and Myanmar 1990–1991 (about 51–53). These are low but come from the World Bank series itself (current US$ at official exchange rates in years of war/sanctions or distorted exchange rates), so they were kept.

### Comparison with the source websites (Romania, 2019)

| Indicator | Value in the database | Value on the source website | Source |
|---|---|---|---|
| ENDO_PREV_ASR (prevalence, age-standardized, per 100,000, IHME) | 474.6720 | 474.67 | GBD Results tool, vizhub.healthdata.org/gbd-results |
| NY.GDP.PCAP.CD (GDP per capita, current US$, World Bank) | 12,909.6104 | 12,909.61 | data.worldbank.org |
| SH.XPD.CHEX.GD.ZS (current health expenditure, % of GDP, World Bank) | 5.6992 | 5.699|data.worldbank.org (WHO Global Health Expenditure Database)|

Comment: All three values match the source websites. The only differences come from rounding (the database stores 4 decimals while the websites show 2-3). Compared on 2026-11-13, Romania, 2019.

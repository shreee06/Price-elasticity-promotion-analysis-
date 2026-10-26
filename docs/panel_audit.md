# Panel audit

All numbers come from `scripts/audit_panel.py` and are stored in `evals/results/panel_audit.json`.
Statistics on discounts, usability, overlap and promoted-vs-not use **train weeks only** (1-85); validation and test weeks are untouched.
Estimates here are descriptive associations, not causal effects.

**Sample caveat.** The data covers only 2,500 sampled households of one retailer, so all units and values are sample counts, not store totals.

## Source and cleaning
- Source transactions: 2,595,732 rows, 2,500 households, 92,339 products, 582 stores, 102 weeks (DAY 1-711).
- Week mapping verified: `WEEK_NO = (DAY + 1) // 7 + 1`. Week 1 (days 1-5) and week 102 (days 706-711) are partial; full weeks are 2-101.
- Rule: rows with `QUANTITY <= 0` or `SALES_VALUE <= 0` are dropped (unit price undefined). QUANTITY<=0: 14,466; SALES_VALUE<=0: 18,850; both: 14,399; total dropped: 18,917 rows (4,544 units, 19.28 sales value). Kept: 2,576,815 rows.

## Discount sign convention and price definitions
- `RETAIL_DISC`: 1,303,026 negative, 36 positive, rest zero. `COUPON_MATCH_DISC`: 17,449 negative, 0 positive. `COUPON_DISC`: 36,422 negative, 0 positive. Discounts are stored as negative numbers.
- Shelf price per unit (adopted) = (SALES_VALUE - (RETAIL_DISC + COUPON_MATCH_DISC)) / QUANTITY. On 1,629 coupon rows that have a non-coupon sale of the same product/store/week, this matches that shelf price within 1% in 99.6% of cases (median ratio 1.000).
- The suggested paid formula `SALES_VALUE - (RETAIL_DISC + COUPON_MATCH_DISC + COUPON_DISC)` adds the (negative) coupon back: it exceeds shelf price on 31,424 rows (median ratio 1.184, within 1% in 0.0%). SALES_VALUE therefore does not yet include the manufacturer coupon.
- **Adopted** paid price per unit = (SALES_VALUE + COUPON_DISC) / QUANTITY, i.e. shelf value plus all three (negative) discounts. Rows with non-positive adopted paid value: 2728.
- Panel prices are unit-weighted averages (total value / total units) per product/commodity-week. Retail discount flag: `RETAIL_DISC < -0.005`. Average retail discount depth = total retail discount / total shelf value (value-weighted).
- Commodity-level prices mix products of different sizes, so they are average value per unit, not a like-for-like price.

## Non-merchandise rows (kept in the panels, excluded from every statistic below except reconciliation)
- Fuel (QUANTITY is in thousandths of gallons: one fuel product alone is 83% of all raw units), coupon and placeholder commodities carry `non_merchandise = 1`: 624 products, 98.7% of panel units but 8.5% of sales value. Analysis universe: 91,281 products, 302 commodities.

## Panel size and reconciliation
- Product panel: 1,073,034 rows, 91,905 products, 102 weeks. Commodity panel: 27,453 rows, 307 commodities (COMMODITY_DESC; 36 occur in more than one department; placeholders present: COUPON, COUPON/MISC ITEMS, COUPONS/STORE & MFG, FUEL, NO COMMODITY DESCRIPTION).
- Only weeks with at least one valid sale have a row; absent weeks are missing, not zero.
- Reconciliation to cleaned source rows: units product panel 260,681,078 vs 260,681,078 (exact: True); sales value exact to the cent: True (abs diff 1.86e-09). Commodity panel: units exact True, sales exact True. Cleaned units + dropped units equal source total: True.
- Products with >= 30 active weeks (analysis universe): 11,859; commodities: 284.
- Reference price null (too little history) in product panel: max-8 495,867, median-13 506,610 rows; commodity panel: 1689 and 2199 rows. Rule: at least 4 (max-8) or 6 (median-13) observed prior weeks inside the window.
- Promotion flags: causal_data flags are store-level (`display != 0`, `mailer != 0`). For each product-week we join them to the stores that actually sold it (`share_stores_display/mailer` = flagged selling stores / selling stores, `any_*` = at least one selling store flagged); `*_chain` counts use all stores listed in causal_data. A selling store with no causal record is treated as not flagged: 79.5% of selling product-store-weeks have no causal record. For commodities the share is over selling product-store-week cells.

## How often products are discounted (product-weeks, train)
- Rows: 871,163. Retail (loyalty) discount on any unit: 44.9%; share of units sold with a retail discount: 51.9%; any display: 9.6%; any mailer: 7.3%; any manufacturer coupon unit: 2.5% (units with coupon 1.3%).
- Commodity-weeks: retail discount 73.7%, display 50.0%, mailer 29.9%, coupon 29.7%.
- Average retail discount depth when discounted (product-weeks): median 21.6%, p95 49.6%.

## Distribution of discount depth vs reference (product-weeks, train, non-null)
| Reference | null rows | share depth > 0 | share depth > 10% | median | p75 | p95 | p99 |
|---|---|---|---|---|---|---|---|
| max of prior 8 weeks | 411,560 | 29.4% | 7.9% | 0.0% | 0.0% | 20.1% | 49.8% |
| median of prior 13 weeks | 423,139 | 14.2% | 4.5% | 0.0% | 0.0% | 8.1% | 35.1% |

## Within-product price variation (products with >= 30 active train weeks: 9,948)
- Coefficient of variation of weekly shelf price: median 3.2%, p75 7.9%, p95 22.0%; share of products with CV > 5%: 36.9%.
- Commodities (279): median CV 14.5%.

## Usable promotion variation
Definition: >= 8 train weeks with depth > 10% AND >= 8 train weeks with non-null depth <= 10%; entity also needs >= 30 active train weeks.
| Level | max-8 reference | median-13 reference |
|---|---|---|
| Products | 1,160 of 82,667 (25.0% of train units) | 613 of 82,667 (12.9% of train units) |
| Commodities | 262 of 300 (98.3% of train units) | 198 of 300 (51.9% of train units) |

## Overlap of display/mailer with price cuts (price cut = depth > 10%; product-weeks, train)
- max-8 reference: display flagged rows with a price cut 5.4% (unflagged 8.3%); price-cut rows carrying the flag 9.2%; mailer flagged rows with a price cut 8.7% (unflagged 7.8%); price-cut rows carrying the flag 10.2%; display or mailer together: flagged rows with cut 7.3% vs unflagged 8.0%; price-cut rows with a retail discount on some unit 28.1%.
- median-13 reference: display flagged rows with a price cut 3.9% (unflagged 4.6%); price-cut rows carrying the flag 11.7%; mailer flagged rows with a price cut 4.5% (unflagged 4.5%); price-cut rows carrying the flag 9.5%; display or mailer together: flagged rows with cut 4.4% vs unflagged 4.5%; price-cut rows with a retail discount on some unit 26.5%.

## Weekly volume and seasonality (full weeks 2-101, sample units, non-merchandise excluded)
- Mean weekly units 33,086 (CV 24.3%); mean in weeks 2-53: 29,935, weeks 54-101: 36,499.
- Start-up ramp: the six lowest weeks are [2, 3, 4, 5, 6, 7]. Active households per week average 328 in weeks 2-7 vs 1307 in weeks 30-60; units per active household 25.7 vs 27.5.
- Raw correlation of weekly units between week w and w+52 (48 pairs): 0.104. After dividing by a centered 13-week mean (36 pairs): 0.512.
- Detrended peaks (WEEK_NO, ratio to trend): [(20, 1.194), (16, 1.18), (72, 1.145), (92, 1.14), (59, 1.126), (42, 1.125)]; troughs: [(9, 0.813), (93, 0.838), (48, 0.898), (32, 0.908), (78, 0.913), (57, 0.914)]. Peaks with another peak 52 (+-1) weeks later: [20].
- The dataset has no calendar dates, so holiday weeks are not labelled; the weekly series is in `evals/results/weekly_volume.csv`. Any holiday effect would have to be tied to an externally assumed date anchor, which is not done here.

## Naive promoted vs non-promoted weeks (NOT an elasticity, not causal; train weeks, usable products)
Promoted = price cut > 10% OR display OR mailer. Pooled means mix products of very different sizes, so the within-product ratio is the more informative line. Promotions are not randomised and are confounded with product, season and other promotion channels.
- max-8 reference: 1,160 products; mean units/week promoted 11.71 (n=36,622) vs not promoted 7.02 (n=32,631); within-product ratio of mean units, median 1.28 (IQR 1.03-1.67).
- median-13 reference: 613 products; mean units/week promoted 11.68 (n=14,468) vs not promoted 7.84 (n=21,158); within-product ratio of mean units, median 1.14 (IQR 0.93-1.55).

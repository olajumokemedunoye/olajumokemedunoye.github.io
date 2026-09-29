-- UK Gender Pay Gap analysis (SQLite)
-- Source: gender-pay-gap.service.gov.uk, reporting years 2023/24 and 2024/25.
-- Table gpg is loaded by python/run_analysis.py: one row per employer per year.
-- Gap convention: a positive gap means men's median hourly pay is higher.

-- 0. SIC 2007 sections, keyed on the first two digits of an employer's first SIC code
DROP TABLE IF EXISTS sic_section;
CREATE TABLE sic_section (div_from INTEGER, div_to INTEGER, section TEXT);
INSERT INTO sic_section VALUES
 (1,3,'Agriculture, forestry and fishing'), (5,9,'Mining and quarrying'),
 (10,33,'Manufacturing'), (35,35,'Energy supply'), (36,39,'Water and waste'),
 (41,43,'Construction'), (45,47,'Wholesale and retail'), (49,53,'Transport and storage'),
 (55,56,'Accommodation and food'), (58,63,'Information and communication'),
 (64,66,'Finance and insurance'), (68,68,'Real estate'),
 (69,75,'Professional, scientific and technical'), (77,82,'Administrative and support'),
 (84,84,'Public administration and defence'), (85,85,'Education'),
 (86,88,'Health and social work'), (90,93,'Arts and recreation'),
 (94,96,'Other services'), (97,98,'Households as employers'), (99,99,'Extraterritorial');

DROP VIEW IF EXISTS gpg_clean;
CREATE VIEW gpg_clean AS
SELECT g.*,
       COALESCE(s.section, 'Not classified') AS section
FROM gpg g
LEFT JOIN sic_section s
  ON g.sic_division BETWEEN s.div_from AND s.div_to;

-- 1. Headline by reporting year
-- @name headline
WITH ranked AS (
  SELECT year, median_gap,
         ROW_NUMBER() OVER (PARTITION BY year ORDER BY median_gap) AS rn,
         COUNT(*)     OVER (PARTITION BY year)                     AS n
  FROM gpg_clean
)
SELECT r.year,
       MAX(r.n)                                                        AS employers,
       ROUND(AVG(CASE WHEN r.rn IN ((r.n + 1) / 2, (r.n + 2) / 2) THEN r.median_gap END), 1) AS median_of_median_gaps,
       ROUND(100.0 * SUM(r.median_gap > 0) / MAX(r.n), 1)              AS pct_men_paid_more,
       ROUND(100.0 * SUM(r.median_gap < 0) / MAX(r.n), 1)              AS pct_women_paid_more,
       ROUND(100.0 * SUM(r.median_gap = 0) / MAX(r.n), 1)              AS pct_no_gap
FROM ranked r
GROUP BY r.year;

-- 2. Median gap by employer size, latest year
-- @name by_size
WITH ranked AS (
  SELECT size_band, size_order, median_gap,
         ROW_NUMBER() OVER (PARTITION BY size_band ORDER BY median_gap) AS rn,
         COUNT(*)     OVER (PARTITION BY size_band)                     AS n
  FROM gpg_clean WHERE year = '2024/25' AND size_band <> 'Not Provided'
)
SELECT size_band, MAX(n) AS employers,
       ROUND(AVG(CASE WHEN rn IN ((n + 1) / 2, (n + 2) / 2) THEN median_gap END), 1) AS median_gap
FROM ranked GROUP BY size_band ORDER BY MIN(size_order);

-- 3. Median gap by sector, latest year (sectors with at least 50 employers)
-- @name by_sector
WITH ranked AS (
  SELECT section, median_gap,
         ROW_NUMBER() OVER (PARTITION BY section ORDER BY median_gap) AS rn,
         COUNT(*)     OVER (PARTITION BY section)                     AS n
  FROM gpg_clean WHERE year = '2024/25'
)
SELECT section, MAX(n) AS employers,
       ROUND(AVG(CASE WHEN rn IN ((n + 1) / 2, (n + 2) / 2) THEN median_gap END), 1) AS median_gap
FROM ranked GROUP BY section HAVING MAX(n) >= 50 ORDER BY median_gap DESC;

-- 4. Where women sit in the pay distribution, latest year
-- @name quartiles
SELECT ROUND(AVG(female_lower), 1)        AS women_in_lower_quartile,
       ROUND(AVG(female_lower_middle), 1) AS women_in_lower_middle,
       ROUND(AVG(female_upper_middle), 1) AS women_in_upper_middle,
       ROUND(AVG(female_top), 1)          AS women_in_top_quartile
FROM gpg_clean WHERE year = '2024/25';

-- 5. Same employers in both years: did the gap narrow?
-- @name matched
WITH pairs AS (
  SELECT a.employer_id, a.median_gap AS gap_2324, b.median_gap AS gap_2425
  FROM gpg_clean a JOIN gpg_clean b
    ON a.employer_id = b.employer_id AND a.year = '2023/24' AND b.year = '2024/25'
),
ranked AS (
  SELECT gap_2425 - gap_2324 AS change,
         ROW_NUMBER() OVER (ORDER BY gap_2425 - gap_2324) AS rn, COUNT(*) OVER () AS n
  FROM pairs
)
SELECT MAX(n) AS matched_employers,
       ROUND(100.0 * SUM(change < 0) / MAX(n), 1) AS pct_gap_narrowed,
       ROUND(100.0 * SUM(change > 0) / MAX(n), 1) AS pct_gap_widened,
       ROUND(AVG(CASE WHEN rn IN ((n + 1) / 2, (n + 2) / 2) THEN change END), 2) AS median_change_pts
FROM ranked;

-- 6. Bonus gaps and bonus take-up, latest year (employers paying bonuses to both sexes)
-- @name bonus
WITH ranked AS (
  SELECT median_bonus_gap,
         ROW_NUMBER() OVER (ORDER BY median_bonus_gap) AS rn, COUNT(*) OVER () AS n
  FROM gpg_clean WHERE year = '2024/25' AND male_bonus_pct > 0 AND female_bonus_pct > 0
)
SELECT MAX(n) AS employers_with_bonuses,
       ROUND(AVG(CASE WHEN rn IN ((n + 1) / 2, (n + 2) / 2) THEN median_bonus_gap END), 1) AS median_bonus_gap,
       (SELECT ROUND(AVG(male_bonus_pct), 1)   FROM gpg_clean WHERE year = '2024/25') AS avg_pct_men_receiving,
       (SELECT ROUND(AVG(female_bonus_pct), 1) FROM gpg_clean WHERE year = '2024/25') AS avg_pct_women_receiving
FROM ranked;

-- 7. Reporting compliance
-- @name late
SELECT year,
       ROUND(100.0 * SUM(late) / COUNT(*), 1) AS pct_submitted_late
FROM gpg_clean GROUP BY year;

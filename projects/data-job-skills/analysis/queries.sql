-- The questions asked of the database, in plain SQL.
-- analyze.py runs each named query and adds the statistics.

-- name: totals
SELECT COUNT(*) AS posts, COUNT(DISTINCT month) AS months, MIN(month) AS first_month, MAX(month) AS last_month,
       SUM(junior) AS junior, SUM(senior) AS senior, SUM(remote) AS remote
FROM posts;

-- name: posts_per_month
SELECT month, COUNT(*) AS posts, SUM(junior) AS junior
FROM posts GROUP BY month ORDER BY month;

-- name: role_per_month
SELECT p.month, r.role, COUNT(*) AS posts
FROM posts p JOIN post_roles r USING (post_id)
GROUP BY p.month, r.role ORDER BY p.month;

-- name: role_totals
-- "Any data role" counts a post once even if it names several roles.
SELECT role, COUNT(*) AS posts FROM post_roles GROUP BY role
UNION ALL
SELECT 'Any data role', COUNT(DISTINCT post_id) FROM post_roles;

-- name: skill_by_role
-- How many posts that mention a role also mention each skill.
SELECT r.role, s.skill, COUNT(*) AS posts
FROM post_roles r JOIN post_skills s USING (post_id)
GROUP BY r.role, s.skill;

-- name: skill_any_data_role
SELECT s.skill, COUNT(DISTINCT s.post_id) AS posts
FROM post_skills s
WHERE s.post_id IN (SELECT post_id FROM post_roles)
GROUP BY s.skill;

-- name: skill_totals
SELECT k.skill, k.skill_group, COUNT(s.post_id) AS posts
FROM skills k LEFT JOIN post_skills s USING (skill)
GROUP BY k.skill;

-- name: skill_by_year
-- First twelve months against the last twelve.
SELECT s.skill,
       SUM(CASE WHEN p.month_index < 12 THEN 1 ELSE 0 END) AS first_year,
       SUM(CASE WHEN p.month_index >= 24 THEN 1 ELSE 0 END) AS last_year
FROM post_skills s JOIN posts p USING (post_id)
GROUP BY s.skill;

-- name: posts_by_year
SELECT SUM(CASE WHEN month_index < 12 THEN 1 ELSE 0 END) AS first_year,
       SUM(CASE WHEN month_index >= 24 THEN 1 ELSE 0 END) AS last_year
FROM posts;

-- name: skill_per_month
SELECT p.month, s.skill, COUNT(*) AS posts
FROM post_skills s JOIN posts p USING (post_id)
GROUP BY p.month, s.skill;

-- name: junior_by_role
SELECT r.role, COUNT(*) AS posts, SUM(p.junior) AS junior
FROM post_roles r JOIN posts p USING (post_id)
GROUP BY r.role;

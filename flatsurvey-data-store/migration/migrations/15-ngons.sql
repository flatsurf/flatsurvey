DROP VIEW ngons;
CREATE VIEW flatsurvey.ngons AS
SELECT *,
	ARRAY(select angle::text::int FROM jsonb_array_elements(data->'angles') as angle) as angles,
  (SELECT COUNT(*) FROM jsonb_array_elements(data->'angles')) as vertices
FROM flatsurvey.surface
WHERE data -> 'angles' IS NOT NULL;

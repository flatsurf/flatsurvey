DROP VIEW flatsurvey.ngons;
CREATE VIEW flatsurvey.ngons AS
SELECT *,
	ARRAY(select angle::text::int FROM jsonb_array_elements(data->'angles') as angle) as angles,
  (SELECT COUNT(*) FROM jsonb_array_elements(data->'angles'))::int as vertices
FROM flatsurvey.surface
WHERE data -> 'angles' IS NOT NULL;

GRANT SELECT ON flatsurvey.ngons TO anonymous;
GRANT SELECT ON flatsurvey.orbit_closure_augmented TO anonymous;
GRANT SELECT, INSERT, UPDATE, DELETE ON flatsurvey.ngons TO writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON flatsurvey.orbit_closure_augmented TO writer;

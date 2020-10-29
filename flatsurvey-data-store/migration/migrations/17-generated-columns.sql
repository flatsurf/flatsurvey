DROP VIEW flatsurvey.ngons;
DROP VIEW flatsurvey.orbit_closure_augmented;

CREATE FUNCTION flatsurvey.orbit_closure_dense(oc flatsurvey.orbit_closure) RETURNS bool AS $$
  SELECT (oc.data->>'dense')::bool
$$ LANGUAGE sql STABLE;

GRANT EXECUTE ON FUNCTION flatsurvey.orbit_closure_dense TO anonymous;
GRANT EXECUTE ON FUNCTION flatsurvey.orbit_closure_dense TO writer;

CREATE FUNCTION flatsurvey.surface_vertices(s flatsurvey.surface) RETURNS int AS $$
  SELECT COUNT(*)::int FROM jsonb_array_elements(s.data->'angles')
$$ LANGUAGE sql STABLE;

GRANT EXECUTE ON FUNCTION flatsurvey.surface_vertices TO anonymous;
GRANT EXECUTE ON FUNCTION flatsurvey.surface_vertices TO writer;

CREATE FUNCTION flatsurvey.surface_angles(s flatsurvey.surface) RETURNS int[] AS $$
	SELECT ARRAY(select angle::text::int FROM jsonb_array_elements(s.data->'angles') as angle)
$$ LANGUAGE sql STABLE;
  
GRANT EXECUTE ON FUNCTION flatsurvey.surface_angles TO anonymous;
GRANT EXECUTE ON FUNCTION flatsurvey.surface_angles TO writer;

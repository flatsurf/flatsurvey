CREATE FUNCTION flatsurvey.surface_name(s flatsurvey.surface) RETURNS text AS $$
  SELECT s.data->>'description'
$$ LANGUAGE sql STABLE;

GRANT EXECUTE ON FUNCTION flatsurvey.surface_name TO anonymous;
GRANT EXECUTE ON FUNCTION flatsurvey.surface_name TO writer;

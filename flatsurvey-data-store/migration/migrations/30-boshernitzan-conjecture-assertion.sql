CREATE FUNCTION flatsurvey.boshernitzan_conjecture_assertion(b flatsurvey.boshernitzan_conjecture) RETURNS text AS $$
  SELECT b.data->>'assertion'
$$ LANGUAGE sql STABLE;

GRANT EXECUTE ON FUNCTION flatsurvey.boshernitzan_conjecture_assertion TO anonymous;
GRANT EXECUTE ON FUNCTION flatsurvey.boshernitzan_conjecture_assertion TO writer;

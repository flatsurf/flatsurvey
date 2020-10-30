CREATE FUNCTION flatsurvey.flow_decomposition_cylinders(fd flatsurvey.flow_decomposition) RETURNS int AS $$
  SELECT (fd.data->>'cylinders')::int
$$ LANGUAGE sql STABLE;

GRANT EXECUTE ON FUNCTION flatsurvey.flow_decomposition_cylinders TO anonymous;
GRANT EXECUTE ON FUNCTION flatsurvey.flow_decomposition_cylinders TO writer;

CREATE FUNCTION flatsurvey.flow_decomposition_undetermined(fd flatsurvey.flow_decomposition) RETURNS int AS $$
  SELECT (fd.data->>'undetermined')::int
$$ LANGUAGE sql STABLE;

GRANT EXECUTE ON FUNCTION flatsurvey.flow_decomposition_undetermined TO anonymous;
GRANT EXECUTE ON FUNCTION flatsurvey.flow_decomposition_undetermined TO writer;

CREATE FUNCTION flatsurvey.flow_decomposition_minimal(fd flatsurvey.flow_decomposition) RETURNS int AS $$
  SELECT (fd.data->>'minimal')::int
$$ LANGUAGE sql STABLE;

GRANT EXECUTE ON FUNCTION flatsurvey.flow_decomposition_minimal TO anonymous;
GRANT EXECUTE ON FUNCTION flatsurvey.flow_decomposition_minimal TO writer;

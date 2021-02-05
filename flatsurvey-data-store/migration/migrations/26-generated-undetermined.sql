CREATE FUNCTION flatsurvey.undetermined_interval_exchange_transformation_degree(fd flatsurvey.undetermined_interval_exchange_transformation) RETURNS int AS $$
  SELECT (fd.data->>'degree')::int
$$ LANGUAGE sql STABLE;

GRANT EXECUTE ON FUNCTION flatsurvey.undetermined_interval_exchange_transformation_degree TO anonymous;
GRANT EXECUTE ON FUNCTION flatsurvey.undetermined_interval_exchange_transformation_degree TO writer;

CREATE FUNCTION flatsurvey.undetermined_interval_exchange_transformation_intervals(fd flatsurvey.undetermined_interval_exchange_transformation) RETURNS int AS $$
  SELECT (fd.data->>'intervals')::int
$$ LANGUAGE sql STABLE;

GRANT EXECUTE ON FUNCTION flatsurvey.undetermined_interval_exchange_transformation_intervals TO anonymous;
GRANT EXECUTE ON FUNCTION flatsurvey.undetermined_interval_exchange_transformation_intervals TO writer;

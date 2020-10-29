CREATE VIEW flatsurvey.orbit_closure_augmented AS
	SELECT *, (data->>'dense')::bool as dense
FROM flatsurvey.orbit_closure;

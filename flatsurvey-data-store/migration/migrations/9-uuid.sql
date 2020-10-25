CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

ALTER TABLE flatsurvey.surfaces ALTER COLUMN id SET DEFAULT uuid_generate_v1 ();
ALTER TABLE flatsurvey.orbit_closure ALTER COLUMN id SET DEFAULT uuid_generate_v1 ();
ALTER TABLE flatsurvey.flow_decomposition ALTER COLUMN id SET DEFAULT uuid_generate_v1 ();

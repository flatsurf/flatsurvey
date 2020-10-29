CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

ALTER TABLE flatsurvey.completely_cylinder_periodic ALTER COLUMN id SET DEFAULT uuid_generate_v1 ();


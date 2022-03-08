CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE flatsurvey.cylinder_periodic_asymptotics (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v1 (),
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  surface UUID REFERENCES flatsurvey.surface (id),
  data JSONB NOT NULL
);

GRANT SELECT ON flatsurvey.cylinder_periodic_asymptotics TO anonymous;
GRANT SELECT, INSERT, UPDATE, DELETE ON flatsurvey.cylinder_periodic_asymptotics to writer;

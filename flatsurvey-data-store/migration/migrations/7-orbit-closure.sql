CREATE TABLE flatsurvey.orbit_closure (
  id UUID PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  surface UUID REFERENCES flatsurvey.surfaces (id),
  data JSONB NOT NULL
);

GRANT SELECT ON flatsurvey.orbit_closure TO anonymous;
GRANT SELECT, INSERT, UPDATE, DELETE ON flatsurvey.orbit_closure to writer;

CREATE TABLE flatsurvey.surfaces (
  id UUID PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  data JSONB NOT NULL
);

GRANT SELECT ON flatsurvey.surfaces TO anonymous;
GRANT SELECT, INSERT, UPDATE, DELETE ON flatsurvey.surfaces TO writer;

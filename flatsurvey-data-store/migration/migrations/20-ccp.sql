CREATE TABLE flatsurvey.completely_cylinder_periodic (
  id UUID PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  surface UUID REFERENCES flatsurvey.surface (id),
  data JSONB NOT NULL
);

GRANT SELECT ON flatsurvey.completely_cylinder_periodic TO anonymous;
GRANT SELECT, INSERT, UPDATE, DELETE ON flatsurvey.completely_cylinder_periodic to writer;


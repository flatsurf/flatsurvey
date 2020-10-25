CREATE TABLE flatsurvey.flow_decomposition (
  id UUID PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  surface UUID REFERENCES flatsurvey.surfaces (id),
  data JSONB NOT NULL
);

GRANT SELECT ON flatsurvey.flow_decomposition TO anonymous;
GRANT SELECT, INSERT, UPDATE, DELETE ON flatsurvey.flow_decomposition to writer;


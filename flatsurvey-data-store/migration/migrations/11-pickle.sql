ALTER TABLE flatsurvey.surfaces RENAME TO surface;

CREATE TABLE flatsurvey.pickle (
  id UUID PRIMARY KEY,
  data BYTEA
);

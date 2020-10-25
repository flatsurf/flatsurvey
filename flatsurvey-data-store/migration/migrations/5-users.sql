CREATE TABLE flatsurvey.users (
    id SERIAL PRIMARY KEY,
    email text NOT NULL UNIQUE,
    password text NOT NULL
);

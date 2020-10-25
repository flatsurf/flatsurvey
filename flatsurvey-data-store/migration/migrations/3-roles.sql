CREATE ROLE anonymous;
GRANT anonymous TO current_user;
GRANT USAGE ON SCHEMA flatsurvey TO anonymous;

CREATE ROLE writer;
GRANT writer TO current_user;
GRANT USAGE ON SCHEMA flatsurvey TO writer;

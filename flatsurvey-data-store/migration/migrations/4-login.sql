CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE FUNCTION flatsurvey.SIGNIN(mail TEXT, password TEXT) RETURNS jwt_token AS
$$
DECLARE
        token_information jwt_token;
BEGIN
        SELECT 'writer', id, email
               INTO token_information
               FROM flatsurvey.users
               WHERE users.email = $1
                     AND users.password = crypt($2, users.password);
       RETURN token_information::jwt_token;
end;
$$ LANGUAGE PLPGSQL VOLATILE STRICT SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION flatsurvey.SIGNIN(mail TEXT, password TEXT) TO anonymous;

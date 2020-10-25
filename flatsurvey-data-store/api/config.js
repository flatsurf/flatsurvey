require('dotenv').config();

const url = require('url');

const {
  POSTGRES_CONNECTION,
  JW_SECRET,
  PORT = 3000,
} = process.env;

exports.port = PORT;
exports.schema = 'flatsurvey';

const params = url.parse(process.env.POSTGRES_CONNECTION);
const auth = params.auth.split(':');
exports.pgConfig = {
  user: auth[0],
  password: auth[1],
  host: params.hostname,
  port: params.port,
  database: params.pathname.split('/')[1],
  idleTimeoutMillis: 0.001,
};

exports.graphileConfig = {
  dynamicJson: true,
  graphqlRoute: '/',
  extendedErrors: ['hint', 'detail', 'errcode'],
  jwtSecret: JW_SECRET,
  jwtPgTypeIdentifier: 'public.jwt_token',
  legacyRelations: 'omit',
  pgDefaultRole: 'anonymous',
}

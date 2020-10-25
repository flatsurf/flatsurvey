const handler = require("serverless-express/handler");
const express = require('serverless-express/express');
const { postgraphile } = require('postgraphile');
const Pool = require('pg-pool');
const url = require('url');
const { pgConfig, graphileConfig, schema, port } = require('./config');

const server = express();

server.use(postgraphile(
  new Pool(pgConfig),
  schema,
  {
    ...graphileConfig,
    readCache: "./schema.json",
  },
));

server.listen(port, () => {
  console.log(`Postgraphile started on port ${port}!`);
});

exports.handler = handler(server);

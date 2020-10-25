const { pgConfig, graphileConfig } = require('./config');
const postgraphile = require("postgraphile/build/postgraphile/postgraphile");
const { Pool } = require("pg");
const fs = require("fs");

exports.handler = async (event) => {
  try {
    const pool = new Pool(pgConfig);
    pool.on('error', err => {
      console.error('PostgreSQL client generated error: ', err.message);
    });
    
    const { getGraphQLSchema } = postgraphile.getPostgraphileSchemaBuilder(pool, ["flatsurvey"], {
      ...graphileConfig,
      writeCache: "/tmp/cache"
    });
    await getGraphQLSchema();
    await pool.end();

    return {
      statusCode: 200,
      body: fs.readFileSync("/tmp/cache").toString(),
    };
  } catch(error) {
    return {
      statusCode: 500,
      body: error.toString(),
    }
  }
};

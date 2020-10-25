const { createDb, migrate } = require('postgres-migrations');
const { Client } = require('pg');
const { pgConfig } = require('./config');

exports.handler = async (event) => {
  try {
    const client = new Client(pgConfig);
    await client.connect();

    try {
      await createDb(pgConfig.database, {client});
      await migrate({client}, 'migrations');
    } finally {
      await client.end();
    }

    return {
      statusCode: 200,
      body: "Ok.",
    };
  } catch(error) {
    return {
      statusCode: 500,
      body: error.toString(),
    }
  }
};

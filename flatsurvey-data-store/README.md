To add a new table to the database

export AWS_ACCESS_KEY_ID=<your-key-here>
export AWS_SECRET_ACCESS_KEY=<your-secret-key-here>
cd migration
# Create migrations in migrations/
yarn deploy
yarn migrate
yarn dump-schema
cd ../api
yarn deploy
yarn dump-schema

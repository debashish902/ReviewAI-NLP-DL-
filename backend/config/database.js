const { Pool } = require("pg");
require("dotenv").config();

const connectionString = process.env.DATABASE_URL;

const poolConfig = connectionString
    ? {
          connectionString,
          ssl:
              process.env.PGSSLMODE === "disable"
                  ? false
                  : { rejectUnauthorized: false }
      }
    : {
          user: process.env.DB_USER,
          host: process.env.DB_HOST,
          database: process.env.DB_NAME,
          password: process.env.DB_PASSWORD,
          port: process.env.DB_PORT ? Number(process.env.DB_PORT) : 5432,
          ssl:
              process.env.NODE_ENV === "production"
                  ? { rejectUnauthorized: false }
                  : false
      };

const pool = new Pool(poolConfig);

module.exports = pool;

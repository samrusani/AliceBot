DO
$$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'alicebot_app') THEN
    CREATE ROLE alicebot_app
      LOGIN
      PASSWORD 'alicebot_app'
      NOSUPERUSER
      NOCREATEDB
      NOCREATEROLE
      NOINHERIT;
  END IF;
END
$$;

GRANT CONNECT ON DATABASE alicebot TO alicebot_app;

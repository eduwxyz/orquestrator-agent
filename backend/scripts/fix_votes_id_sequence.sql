-- Ensure votes.id autoincrements in Postgres.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_class
        WHERE relname = 'votes_id_seq'
    ) THEN
        CREATE SEQUENCE votes_id_seq OWNED BY votes.id;
    END IF;
END
$$;

ALTER TABLE votes
    ALTER COLUMN id SET DEFAULT nextval('votes_id_seq');

SELECT setval(
    'votes_id_seq',
    COALESCE((SELECT MAX(id) FROM votes), 0),
    true
);

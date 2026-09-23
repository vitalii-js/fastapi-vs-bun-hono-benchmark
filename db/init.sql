CREATE TABLE IF NOT EXISTS items (
    id          bigserial PRIMARY KEY,
    name        text           NOT NULL,
    price       numeric(10, 2) NOT NULL,
    tags        text[]         NOT NULL DEFAULT '{}',
    created_at  timestamptz    NOT NULL DEFAULT now()
);

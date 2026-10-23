-- Tenant Exchange staging schema snapshot
-- Structure only. Seed data and environment secrets are intentionally omitted.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE public.tenants (
    id uuid PRIMARY KEY,
    slug text NOT NULL,
    name text NOT NULL,
    login text NOT NULL,
    password_hash text NOT NULL,
    inserted_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);

CREATE UNIQUE INDEX tenants_slug_index ON public.tenants (slug);
CREATE UNIQUE INDEX tenants_login_index ON public.tenants (login);

CREATE TABLE public.users (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    name text NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    inserted_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);

CREATE INDEX users_tenant_id_index ON public.users (tenant_id);
CREATE UNIQUE INDEX users_email_index ON public.users (email);

CREATE TABLE public.documents (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    title text NOT NULL,
    body text NOT NULL,
    classification text NOT NULL,
    inserted_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);

CREATE INDEX documents_tenant_id_index ON public.documents (tenant_id);
CREATE UNIQUE INDEX documents_tenant_id_title_index ON public.documents (tenant_id, title);

CREATE TABLE public.sessions (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    token_hash bytea NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    otp_attempts integer NOT NULL DEFAULT 0,
    otp_locked_until timestamp without time zone,
    inserted_at timestamp without time zone NOT NULL
);

CREATE INDEX sessions_tenant_id_index ON public.sessions (tenant_id);

-- The lookup service exposes only this UUID index to the blind lookup role.
CREATE SCHEMA challenge_lookup;

CREATE TABLE challenge_lookup.delivery_index (
    doc_id uuid PRIMARY KEY,
    priority integer NOT NULL DEFAULT 100
);
CREATE UNIQUE INDEX sessions_token_hash_index ON public.sessions (token_hash);

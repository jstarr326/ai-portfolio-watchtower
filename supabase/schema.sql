create table if not exists raw_posts (
    post_id text primary key,
    source_account text not null,
    portfolio text not null,
    post_url text not null,
    text text not null,
    created_at timestamptz not null,
    inserted_at timestamptz not null default now()
);

create table if not exists portfolio_events (
    id uuid primary key default gen_random_uuid(),
    portfolio text not null,
    source_account text not null,
    post_id text not null references raw_posts(post_id) on delete cascade,
    post_url text not null,
    created_at timestamptz not null,
    tickers text[] not null default '{}',
    action text not null,
    event_type text not null,
    allocation_pct numeric,
    thesis_summary text not null default '',
    evidence_quotes text[] not null default '{}',
    confidence numeric not null,
    conviction_score integer not null,
    scoring_reasons text[] not null default '{}',
    alerted_at timestamptz,
    inserted_at timestamptz not null default now(),
    unique (post_id, action, event_type, tickers)
);

create index if not exists portfolio_events_tickers_idx on portfolio_events using gin (tickers);
create index if not exists portfolio_events_created_at_idx on portfolio_events (created_at desc);
create index if not exists portfolio_events_action_idx on portfolio_events (action);

create table if not exists portfolio_holdings (
    id uuid primary key default gen_random_uuid(),
    portfolio text not null,
    ticker text not null,
    status text not null,
    source_account text not null,
    first_seen_at timestamptz not null,
    last_seen_at timestamptz not null,
    last_post_id text not null references raw_posts(post_id) on delete cascade,
    last_post_url text not null,
    last_action text not null,
    latest_allocation_pct numeric,
    latest_thesis text not null default '',
    confidence numeric not null,
    updated_at timestamptz not null default now(),
    unique (portfolio, ticker)
);

create index if not exists portfolio_holdings_ticker_idx on portfolio_holdings (ticker);
create index if not exists portfolio_holdings_status_idx on portfolio_holdings (status);
create index if not exists portfolio_holdings_last_seen_at_idx
    on portfolio_holdings (last_seen_at desc);

create table if not exists weekly_briefs (
    id uuid primary key default gen_random_uuid(),
    period_start timestamptz not null,
    period_end timestamptz not null,
    markdown text not null,
    inserted_at timestamptz not null default now()
);

create index if not exists weekly_briefs_period_idx
    on weekly_briefs (period_start desc, period_end desc);

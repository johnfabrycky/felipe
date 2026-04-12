create table if not exists public.parking_spot_owners (
    user_id text primary key,
    discord_username text not null,
    spot_number integer not null
);

-- Harbor City simulation tables (safe to run alongside other simulations)
create table if not exists hc_submissions (
  team text not null, rnd int not null, moves text not null, points int,
  circ double precision, hardship double precision, trust double precision, score double precision,
  created double precision, primary key (team, rnd));
create table if not exists hc_settings (k text primary key, v text);
create table if not exists hc_reflections (team text primary key, body text, created double precision);
-- The app uses the service_role key stored in Streamlit secrets, which bypasses RLS.
alter table hc_submissions enable row level security;
alter table hc_settings enable row level security;
alter table hc_reflections enable row level security;

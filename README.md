# Harbor City: A Ban on Paper (BSAD 360, Oct 26)

A three-quarter enforcement simulation for pairs. Harbor City (1.2 million people, invented) banned thin plastic bags six months ago, and 80% of bags still circulate. Each quarter a team spends points on six moves (the same menu as the class activity):

| Move | Cost |
|---|---|
| Inspect markets | 3 |
| Check factories and importers | 3 |
| Subsidize substitutes for stall owners | 3 |
| Fines on stall owners | 2 |
| Community "bag marshals" with a local NPO | 2 |
| Public campaign | 1 |

Budget is 10 points in Quarters 1 and 2 and 8 in Quarter 3 (a new council cuts it). Quarter 2 adds smuggling from the neighboring district. Each quarter reports bags still circulating, stall-owner hardship, public trust, and a score (60% bag reduction, 25% low hardship, 15% trust). All numbers are invented teaching assumptions, tuned so the lessons from Rwanda, India, Ireland and England show up: upstream checks and affordable substitutes beat inspection and fines alone, fines without substitutes backfire, community effects build over time, and compliance relapses when effort drops.

## Files
app.py (team view + instructor dashboard), model.py (the model), storage.py (Supabase, with a local SQLite fallback for testing), schema.sql, requirements.txt, secrets.toml.example, .streamlit/config.toml (HAPS colors).

## Set up (about 15 minutes)
1. **GitHub.** New public repo (for example `harbor-city`) with all files, including the `.streamlit` folder. Streamlit's free tier allows only one private app, so make it public. Never upload real secrets.
2. **Supabase.** Reuse your project. SQL Editor > paste `schema.sql` > Run. Tables are prefixed `hc_`, so they will not clash with the Poet Pop tables.
3. **Streamlit Community Cloud.** New app > repo > main file `app.py` > Advanced settings > Secrets: paste the three lines from `secrets.toml.example` with your values (Project URL, service_role key, instructor password).
4. Open the app. Run one test team through all three quarters (Instructor view > "Quarters open to teams" opens each), check the dashboard, then use "Clear all data" before class.
5. Put the link and QR code on slide 18.

## Run of show (about 9 minutes of play, 2:24 to 2:32)
- Open Quarter 1 as you finish the briefing slide. Teams join with a team name (one per pair).
- About 3 minutes per quarter. Open Quarter 2 after most teams finish 1, and Quarter 3 after most finish 2.
- Show the dashboard (bags in circulation, moves chosen) for the debrief at 2:32.

## Debrief prompts
1. Which quarter was hardest, and why? (Smuggling, then the budget cut.)
2. Compare the top and bottom teams' moves. What did the leaders buy once substitutes were affordable?
3. Which real case did your plan resemble: Rwanda, India, or the bag charges?
4. What did you keep after the budget cut, and what did you drop? Link to Brazil: what keeps enforcement going when politics change?

## Balance notes
A sweep of all 133,100 three-quarter plans shows the best totals use factory checks, subsidies, marshals and the campaign, with inspection mixed in; fines alone score below doing nothing. Spending the same points on inspection plus fines plus campaign leaves about 40% of bags circulating at the end. Teams that find the upstream-plus-affordability mix land around 6 to 15%.

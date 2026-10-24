import json, io
import pandas as pd, altair as alt, streamlit as st
from model import MOVES, COST, LABEL, ROUNDS, START, cost_of, step, feedback, headline, reactions
from storage import Store, _secret
import sheets, os
SHEET_URL = "https://docs.google.com/spreadsheets/d/1DwOPsDAOzUhm7NuFwIzglSBxBdMwmSSJ9RAT3zrjudA/edit"

st.set_page_config(page_title="Harbor City: Enforcing the Bag Ban", page_icon="\U0001F6CD", layout="centered")
NAVY, CORAL, GOLD, TEAL, BLUE, VIOLET = "#1F2A44", "#E8695A", "#E3A92B", "#2A9D8F", "#3B6FB6", "#7B5EA7"
st.markdown("""<style>
h1,h2,h3{font-family:Cambria,Georgia,serif;color:#1F2A44}
.card{border-radius:12px;padding:12px 16px;margin:6px 0;color:#fff}
.stButton>button{font-weight:700}
</style>""", unsafe_allow_html=True)

@st.cache_resource
def get_store(): return Store()
store = get_store()

def pic(name, caption=None):
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), name)):
        st.image(os.path.join(os.path.dirname(os.path.abspath(__file__)), name), caption=caption, width="stretch")

ICON = {"inspect": "\U0001F50D", "factory": "\U0001F3ED", "subsidy": "\U0001F4B5", "fines": "\U0001F4DD", "marshals": "\U0001F91D", "campaign": "\U0001F4E3"}

def rank_info(all_rows, q, team):
    qs = sorted([r for r in all_rows if r["rnd"] == q], key=lambda r: -r["score"])
    mine = next((r for r in qs if r["team"] == team), None)
    if not mine: return qs, None
    return qs, 1 + sum(1 for r in qs if r["score"] > mine["score"] + 1e-9)

def replay(rows):
    st_ = dict(START); hist = []; outs = []; befores = []; priors = []
    for r in sorted(rows, key=lambda r: r["rnd"]):
        befores.append(dict(st_)); priors.append([set(h) for h in hist])
        st_, o = step(st_, r["moves"], r["rnd"], hist); hist.append(set(r["moves"])); outs.append(o)
    return st_, outs, befores, priors

def metric_row(o, label=""):
    c1, c2, c3 = st.columns(3)
    c1.metric("Bags still circulating", f"{o['circ']*100:.0f}%")
    c2.metric("Stall-owner hardship", f"{o['hardship']*100:.0f}")
    c3.metric("Public trust", f"{o['trust']*100:.0f}")

_opts = ["Team", "Instructor", "Projector"]
_idx = 2 if st.query_params.get("view") == "projector" else 0
mode = st.sidebar.radio("View", _opts, index=_idx)
st.sidebar.caption("Storage: " + store.mode)

if mode == "Projector":
    st.markdown("<style>.block-container{max-width:1200px} h1{font-size:3rem}</style>", unsafe_allow_html=True)
    @st.fragment(run_every=5)
    def projector():
        rows = store.all_rounds()
        st.title("Harbor City: live results")
        if not rows:
            st.markdown("### Waiting for the first teams to submit Quarter 1...")
            return
        df = pd.DataFrame(rows); df["circ_pct"] = df["circ"] * 100
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Teams playing", df["team"].nunique())
        for col, q in zip((c2, c3, c4), (1, 2, 3)):
            col.metric(f"Finished Quarter {q}", int((df["rnd"] == q).sum()))
        lb = df.groupby("team").agg(quarters=("rnd", "count"), total=("score", "sum"), circ=("circ", "last")).reset_index().sort_values(["total"], ascending=False).head(8)
        lb["total"] = lb["total"].round(0).astype(int); lb["circ"] = (lb["circ"] * 100).round(0).astype(int)
        lb.insert(0, "rank", range(1, len(lb) + 1))
        st.subheader("Leaderboard (total points so far)")
        st.dataframe(lb.rename(columns={"circ": "bags circulating % (latest)", "total": "total points", "quarters": "quarters done"}), hide_index=True, width="stretch")
        avg = df.groupby("rnd")["circ_pct"].mean().reset_index()
        grey = alt.Chart(df).mark_line(color="#9aa4b8", opacity=0.45).encode(x=alt.X("rnd:O", title="Quarter"), y=alt.Y("circ_pct:Q", title="Bags still circulating (%)", scale=alt.Scale(domain=[0, 100])), detail="team:N")
        mean = alt.Chart(avg).mark_line(color=CORAL, strokeWidth=5, point=True).encode(x="rnd:O", y="circ_pct:Q")
        st.subheader("Bags in circulation by quarter (grey = each team, red = class average)")
        st.altair_chart(grey + mean, width="stretch")
    projector()
    st.stop()

if mode == "Instructor":
    st.title("Instructor dashboard")
    pw = st.sidebar.text_input("Instructor password", type="password")
    if pw != (_secret("INSTRUCTOR_PASSWORD") or "harbor"):
        st.info("Enter the instructor password in the sidebar."); st.stop()
    if st.session_state.pop("cleared", False): st.success("All data deleted: teams, results and reflections are cleared from the app and the Google Sheet.")
    st.link_button("Open the projector view (put this on the main screen)", "https://harbor-city-bsad360.streamlit.app/?view=projector")
    st.link_button("Open the Google Sheet (live results and reflections)", SHEET_URL)
    sp_cur = store.get_setting("self_paced", "0") == "1"
    sp_new = st.toggle("Self-paced: teams start each quarter as soon as they finish the last one", value=sp_cur)
    if sp_new != sp_cur: store.set_setting("self_paced", "1" if sp_new else "0"); st.success("Self-paced is ON: all quarters are open." if sp_new else "Self-paced is OFF: you open each quarter with the slider.")
    cur = int(store.get_setting("open_rounds", "0"))
    new = st.select_slider("Quarters open to teams (used when self-paced is off)", options=[0, 1, 2, 3], value=cur, disabled=sp_new)
    if new != cur: store.set_setting("open_rounds", new); st.success(f"Quarters open: {new}")
    rows = store.all_rounds()
    if not rows:
        st.write("No submissions yet.")
        st.subheader("Google Sheet")
        st.caption("Live Google Sheet connected. Rows appear as teams submit." if sheets.enabled() else "Live Google Sheet not connected (add SHEET_WEBHOOK and SHEET_TOKEN in the app secrets).")
        if sheets.enabled() and st.button("Send a test row to the Google Sheet"):
            sheets.push(dict(results=[dict(team="TEST", quarter=0, moves="connection test", points_used=0, bags_circulating_pct=0, hardship=0, trust=0, score=0, updated="test")]), wait=True)
            st.success("Sent. Check the Results tab for a row named TEST, then click Delete everything to remove it.")
        with st.expander("Clear all data"):
            if st.checkbox("Yes, delete every team's data") and st.button("Delete everything"): store.clear(); sheets.push(dict(clear=True), wait=True); st.session_state['cleared'] = True; st.rerun()
        st.stop()
    df = pd.DataFrame(rows); df["circ_pct"] = df["circ"] * 100
    teams = df.groupby("team").agg(rounds=("rnd", "count"), total=("score", "sum"), circ=("circ", "last"), hardship=("hardship", "last"), trust=("trust", "last")).sort_values("total", ascending=False).reset_index()
    lb = teams.copy(); lb["total"] = lb["total"].round(0).astype(int)
    for col in ("circ", "hardship", "trust"): lb[col] = (lb[col] * 100).round(0).astype(int)
    st.subheader("Leaderboard"); st.dataframe(lb.rename(columns={"total": "total score", "circ": "bags circulating % (last)", "hardship": "hardship (last)", "trust": "trust (last)"}), hide_index=True)
    top = list(teams["team"].head(3)); bottom = list(teams["team"].tail(2)); show = set(top + bottom)
    df["label"] = df["team"].where(df["team"].isin(show), "")
    base = alt.Chart(df).encode(x=alt.X("rnd:O", title="Quarter"), y=alt.Y("circ_pct:Q", title="Bags still circulating (%)", scale=alt.Scale(domain=[0, 100])), detail="team:N")
    lines = base.mark_line(color="#9aa4b8", opacity=0.5)
    hi = alt.Chart(df[df["team"].isin(show)]).mark_line(point=True, strokeWidth=3).encode(x="rnd:O", y="circ_pct:Q", color=alt.Color("team:N", legend=None), detail="team:N")
    txt = alt.Chart(df[(df["team"].isin(show)) & (df["rnd"] == df.groupby("team")["rnd"].transform("max"))]).mark_text(align="left", dx=6).encode(x="rnd:O", y="circ_pct:Q", text="team:N", color=alt.Color("team:N", legend=None))
    st.subheader("Bags in circulation by quarter"); st.altair_chart(lines + hi + txt, width="stretch")
    st.caption("Grey lines are all teams; the top 3 and bottom 2 are named.")
    mv = df.explode("moves").dropna(subset=["moves"]); mv["move"] = mv["moves"].map(LABEL)
    cnt = mv.groupby(["rnd", "move"]).size().reset_index(name="teams")
    st.subheader("Moves chosen by quarter")
    st.altair_chart(alt.Chart(cnt).mark_bar(color=TEAL).encode(y=alt.Y("move:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)), x=alt.X("teams:Q", title="Teams choosing it"), row=alt.Row("rnd:O", title="Quarter")).properties(width=380, height=110), width="content")
    refl = store.reflections()
    if refl:
        st.subheader("Reflections"); 
        for r in refl: st.markdown(f"**{r['team']}**: {r['body']}")
    rmap = {r["team"]: r["body"] for r in refl}
    full = df.drop(columns=["circ_pct", "label"]).assign(moves=df["moves"].map(lambda m: ", ".join(LABEL[x] for x in m)))
    full["reflection"] = full["team"].map(rmap).fillna("")
    full = full.sort_values(["team", "rnd"])
    out = io.StringIO(); full.to_csv(out, index=False)
    summ = teams.copy(); summ["reflection"] = summ["team"].map(rmap).fillna("")
    out2 = io.StringIO(); summ.to_csv(out2, index=False)
    st.download_button("Download results by quarter, with reflections (CSV for Google Sheets)", out.getvalue(), "harbor_city_results.csv", "text/csv")
    st.download_button("Download one row per team, with reflections (CSV)", out2.getvalue(), "harbor_city_team_summary.csv", "text/csv")
    st.subheader("Google Sheet")
    if sheets.enabled():
        if st.button("Resync everything to the Google Sheet"):
            res = [sheets.result_row(r["team"], r["rnd"], r["moves"], r["points"], dict(circ=r["circ"], hardship=r["hardship"], trust=r["trust"], score=r["score"]), r.get("created")) for r in rows]
            sheets.push(dict(clear=True, results=res, reflections=[dict(team=r["team"], reflection=r["body"], updated="") for r in refl]), wait=True); st.success("Sheet resynced.")
    else:
        st.caption("Live Google Sheet not connected (add SHEET_WEBHOOK and SHEET_TOKEN in the app secrets).")
    with st.expander("Clear all data"):
        if st.checkbox("Yes, delete every team's data") and st.button("Delete everything"): store.clear(); sheets.push(dict(clear=True), wait=True); st.session_state['cleared'] = True; st.rerun()
    st.stop()

# ---------------- Team view ----------------
st.title("Harbor City: a ban on paper")
st.caption("An invented city of 1.2 million people. All numbers are teaching assumptions.")
team = st.session_state.get("team")
if not team:
    pic("hc_join.jpg", "Harbor City market day. The ban is six months old.")
    st.write("Six months ago Harbor City banned thin plastic bags, but most still circulate. You are the city’s enforcement team. Each quarter you choose how to spend your points. Compare your results with the other teams.")
    name = st.text_input("Team name (one per pair)", max_chars=40)
    if st.button("Start or resume", type="primary") and name.strip():
        st.session_state["team"] = name.strip(); st.rerun()
    st.stop()

rows = store.team_rounds(team)
state, outs, befores, priors = replay(rows)
all_rows = store.all_rounds()
done = len(rows); nxt = done + 1
open_rounds = 3 if store.get_setting("self_paced", "0") == "1" else int(store.get_setting("open_rounds", "0"))
st.markdown(f"**Team:** {team}")
for i, o in enumerate(outs, start=1):
    with st.expander(f"Quarter {i} result: {o['circ']*100:.0f}% of bags still circulating", expanded=(i == done and done < 3)):
        st.write("Moves: " + (", ".join(LABEL[m] for m in rows[i-1]["moves"]) or "none")); metric_row(o)
        st.markdown(f"<div class='card' style='background:{CORAL};font-family:Cambria,Georgia,serif;font-size:1.15rem'>\U0001F4F0 <b>{headline(i, rows[i-1]['moves'], befores[i-1], o)}</b></div>", unsafe_allow_html=True)
        got, nxt_q = feedback(i, rows[i-1]["moves"], befores[i-1], o, priors[i-1], ROUNDS[i]["budget"])
        st.markdown("**What happened**\n\n" + "\n".join(f"- {g}" for g in got))
        st.markdown("**What people are saying**\n\n" + "\n".join(f"> \u201c{q}\u201d  \n> *{who}*\n" for who, q in reactions(i, rows[i-1]["moves"], befores[i-1], o)))
        peers = [r for r in all_rows if r["rnd"] == i]
        if len(peers) >= 2:
            avg = sum(r["circ"] for r in peers) / len(peers) * 100
            better = sum(1 for r in peers if r["circ"] < o["circ"] - 1e-9)
            st.markdown(f"**Compared with the class** ({len(peers)} teams so far): average {avg:.0f}% of bags circulating; yours {o['circ']*100:.0f}%. "
                        f"{better} team{'s' if better != 1 else ''} did better on circulation this quarter.")
        if i < 3:
            st.markdown("**Think about before the next quarter**\n\n" + "\n".join(f"- {q}" for q in nxt_q))

if done >= 1:
    @st.fragment(run_every=10)
    def leaderboard(q, me):
        qs, rk = rank_info(store.all_rounds(), q, me)
        st.subheader(f"Class leaderboard: Quarter {q}")
        medals = ["\U0001F947", "\U0001F948", "\U0001F949"]
        for i, r in enumerate(qs[:3]):
            mark = "  **(you)**" if r["team"] == me else ""
            st.markdown(f"{medals[i]} **{r['team']}**: {r['score']:.0f} points, {r['circ']*100:.0f}% of bags still circulating{mark}")
        if rk and rk > 3:
            mine = next(r for r in qs if r["team"] == me)
            st.markdown(f"**You are #{rk} of {len(qs)} teams** this quarter: {mine['score']:.0f} points, {mine['circ']*100:.0f}% of bags circulating.")
        st.caption(f"{len(qs)} team{'s' if len(qs) != 1 else ''} have finished Quarter {q}. This updates every few seconds.")
    leaderboard(done, team)

if done >= 3:
    pic("hc_done.jpg")
    st.success(f"All three quarters complete. Total score: {sum(o['score'] for o in outs):.0f}")
    st.subheader("Reflection")
    st.write("Which real case did your plan most resemble: Rwanda, India, or the bag charges in Ireland and England? Why?")
    ex = {r["team"]: r["body"] for r in store.reflections()}.get(team, "")
    body = st.text_area("Your answer", value=ex, height=120)
    if st.button("Save reflection") and body.strip(): store.save_reflection(team, body.strip()); sheets.push(dict(reflections=[dict(team=team, reflection=body.strip(), updated=__import__('time').strftime('%Y-%m-%d %H:%M:%S'))]), wait=True); st.success("Saved. Watch the main screen.")
    st.stop()

if nxt > open_rounds:
    st.info(f"Waiting for the instructor to open Quarter {nxt}.")
    @st.fragment(run_every=5)
    def waiter():
        if store.get_setting("self_paced", "0") == "1" or int(store.get_setting("open_rounds", "0")) >= nxt: st.rerun()
    waiter(); st.stop()

R = ROUNDS[nxt]
st.header(f"{R['name']}: {R['budget']} points")
pic({1: "hc_q1.jpg", 2: "hc_q2.jpg", 3: "hc_q3.jpg"}[nxt])
st.markdown(f"<div class='card' style='background:{NAVY}'>{R['event']}</div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
cur_circ = state["s"] * (1 - state["c"])
c1.metric("Bags circulating now", f"{cur_circ*100:.0f}%"); c2.metric("Substitute affordability", f"{state['a']*100:.0f}"); c3.metric("Public trust", f"{state['t']*100:.0f}")
chosen = []
for k, name_, cost in MOVES:
    if st.checkbox(f"{ICON[k]}  {name_}  ({cost} pts)", key=f"{team}_{nxt}_{k}"): chosen.append(k)
used = cost_of(chosen)
st.progress(min(used / R["budget"], 1.0), text=f"Points used: {used} of {R['budget']}")
if used > R["budget"]: st.error("Over budget. Remove a move.")
if st.button(f"Submit {R['name']}", type="primary", disabled=used > R["budget"]):
    hist = [set(r["moves"]) for r in rows]
    _, o = step(state, chosen, nxt, hist)
    store.save_round(team, nxt, chosen, used, o)
    sheets.push(dict(results=[sheets.result_row(team, nxt, chosen, used, o)]), wait=True); st.rerun()

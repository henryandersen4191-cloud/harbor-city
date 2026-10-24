import json, io
import pandas as pd, altair as alt, streamlit as st
from model import MOVES, COST, LABEL, ROUNDS, START, cost_of, step, feedback
from storage import Store, _secret

st.set_page_config(page_title="Harbor City: A Ban on Paper", page_icon="\U0001F6CD", layout="centered")
NAVY, CORAL, GOLD, TEAL, BLUE, VIOLET = "#1F2A44", "#E8695A", "#E3A92B", "#2A9D8F", "#3B6FB6", "#7B5EA7"
st.markdown("""<style>
h1,h2,h3{font-family:Cambria,Georgia,serif;color:#1F2A44}
.card{border-radius:12px;padding:12px 16px;margin:6px 0;color:#fff}
.stButton>button{font-weight:700}
</style>""", unsafe_allow_html=True)

@st.cache_resource
def get_store(): return Store()
store = get_store()

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

mode = st.sidebar.radio("View", ["Team", "Instructor"])
st.sidebar.caption("Storage: " + store.mode)

if mode == "Instructor":
    st.title("Instructor dashboard")
    pw = st.sidebar.text_input("Instructor password", type="password")
    if pw != (_secret("INSTRUCTOR_PASSWORD") or "harbor"):
        st.info("Enter the instructor password in the sidebar."); st.stop()
    cur = int(store.get_setting("open_rounds", "0"))
    new = st.select_slider("Quarters open to teams", options=[0, 1, 2, 3], value=cur)
    if new != cur: store.set_setting("open_rounds", new); st.success(f"Quarters open: {new}")
    rows = store.all_rounds()
    if not rows: st.write("No submissions yet."); st.stop()
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
    with st.expander("Clear all data"):
        if st.checkbox("Yes, delete every team's data") and st.button("Delete everything"): store.clear(); st.rerun()
    st.stop()

# ---------------- Team view ----------------
st.title("Harbor City: a ban on paper")
st.caption("An invented city of 1.2 million people. All numbers are teaching assumptions.")
team = st.session_state.get("team")
if not team:
    st.write("Six months ago Harbor City banned thin plastic bags, but most still circulate. You are the city’s enforcement team. Each quarter you choose how to spend your points. Compare your results with the other teams.")
    name = st.text_input("Team name (one per pair)", max_chars=40)
    if st.button("Start or resume", type="primary") and name.strip():
        st.session_state["team"] = name.strip(); st.rerun()
    st.stop()

rows = store.team_rounds(team)
state, outs, befores, priors = replay(rows)
all_rows = store.all_rounds()
done = len(rows); nxt = done + 1
open_rounds = int(store.get_setting("open_rounds", "0"))
st.markdown(f"**Team:** {team}")
for i, o in enumerate(outs, start=1):
    with st.expander(f"Quarter {i} result: {o['circ']*100:.0f}% of bags still circulating", expanded=(i == done and done < 3)):
        st.write("Moves: " + (", ".join(LABEL[m] for m in rows[i-1]["moves"]) or "none")); metric_row(o)
        got, nxt_q = feedback(i, rows[i-1]["moves"], befores[i-1], o, priors[i-1], ROUNDS[i]["budget"])
        st.markdown("**What happened**\n\n" + "\n".join(f"- {g}" for g in got))
        peers = [r for r in all_rows if r["rnd"] == i]
        if len(peers) >= 2:
            avg = sum(r["circ"] for r in peers) / len(peers) * 100
            better = sum(1 for r in peers if r["circ"] < o["circ"] - 1e-9)
            st.markdown(f"**Compared with the class** ({len(peers)} teams so far): average {avg:.0f}% of bags circulating; yours {o['circ']*100:.0f}%. "
                        f"{better} team{'s' if better != 1 else ''} did better on circulation this quarter.")
        if i < 3:
            st.markdown("**Think about before the next quarter**\n\n" + "\n".join(f"- {q}" for q in nxt_q))

if done >= 3:
    st.success(f"All three quarters complete. Total score: {sum(o['score'] for o in outs):.0f}")
    st.subheader("Reflection")
    st.write("Which real case did your plan most resemble: Rwanda, India, or the bag charges in Ireland and England? Why?")
    ex = {r["team"]: r["body"] for r in store.reflections()}.get(team, "")
    body = st.text_area("Your answer", value=ex, height=120)
    if st.button("Save reflection") and body.strip(): store.save_reflection(team, body.strip()); st.success("Saved. Watch the main screen.")
    st.stop()

if nxt > open_rounds:
    st.info(f"Waiting for the instructor to open Quarter {nxt}.")
    @st.fragment(run_every=5)
    def waiter():
        if int(store.get_setting("open_rounds", "0")) >= nxt: st.rerun()
    waiter(); st.stop()

R = ROUNDS[nxt]
st.header(f"{R['name']}: {R['budget']} points")
st.markdown(f"<div class='card' style='background:{NAVY}'>{R['event']}</div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
cur_circ = state["s"] * (1 - state["c"])
c1.metric("Bags circulating now", f"{cur_circ*100:.0f}%"); c2.metric("Substitute affordability", f"{state['a']*100:.0f}"); c3.metric("Public trust", f"{state['t']*100:.0f}")
chosen = []
for k, name_, cost in MOVES:
    if st.checkbox(f"{name_}  ({cost} pts)", key=f"{team}_{nxt}_{k}"): chosen.append(k)
used = cost_of(chosen)
st.progress(min(used / R["budget"], 1.0), text=f"Points used: {used} of {R['budget']}")
if used > R["budget"]: st.error("Over budget. Remove a move.")
if st.button(f"Submit {R['name']}", type="primary", disabled=used > R["budget"]):
    hist = [set(r["moves"]) for r in rows]
    _, o = step(state, chosen, nxt, hist)
    store.save_round(team, nxt, chosen, used, o); st.rerun()

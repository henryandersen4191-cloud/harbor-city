"""Storage: Supabase when SUPABASE_URL/KEY secrets exist, else local SQLite (testing only)."""
import json, os, sqlite3, time

def _secret(name):
    try:
        import streamlit as st
        if name in st.secrets: return st.secrets[name]
    except Exception: pass
    return os.environ.get(name)

class Store:
    def __init__(self):
        url, key = _secret("SUPABASE_URL"), _secret("SUPABASE_KEY")
        self.remote = None
        if url and key:
            from supabase import create_client
            self.remote = create_client(url, key)
        else:
            self.db = sqlite3.connect(os.environ.get("HC_DB", "hc_local.db"), check_same_thread=False)
            self.db.executescript("""
            create table if not exists hc_submissions(team text, rnd int, moves text, points int, circ real, hardship real, trust real, score real, created real, primary key(team, rnd));
            create table if not exists hc_settings(k text primary key, v text);
            create table if not exists hc_reflections(team text primary key, body text, created real);""")
    @property
    def mode(self): return "Supabase" if self.remote else "Local test database (not shared)"

    def get_setting(self, k, default="0"):
        if self.remote:
            r = self.remote.table("hc_settings").select("v").eq("k", k).execute().data
            return r[0]["v"] if r else default
        r = self.db.execute("select v from hc_settings where k=?", (k,)).fetchone()
        return r[0] if r else default
    def set_setting(self, k, v):
        if self.remote: self.remote.table("hc_settings").upsert({"k": k, "v": str(v)}).execute()
        else:
            self.db.execute("insert or replace into hc_settings values(?,?)", (k, str(v))); self.db.commit()

    def save_round(self, team, rnd, moves, points, o):
        row = dict(team=team, rnd=rnd, moves=json.dumps(sorted(moves)), points=points, circ=o["circ"], hardship=o["hardship"], trust=o["trust"], score=o["score"], created=time.time())
        if self.remote: self.remote.table("hc_submissions").upsert(row, on_conflict="team,rnd").execute()
        else:
            self.db.execute("insert or replace into hc_submissions values(?,?,?,?,?,?,?,?,?)", tuple(row[k] for k in ("team","rnd","moves","points","circ","hardship","trust","score","created"))); self.db.commit()

    def team_rounds(self, team):
        if self.remote:
            rows = self.remote.table("hc_submissions").select("*").eq("team", team).order("rnd").execute().data
        else:
            cur = self.db.execute("select team,rnd,moves,points,circ,hardship,trust,score,created from hc_submissions where team=? order by rnd", (team,))
            rows = [dict(zip(("team","rnd","moves","points","circ","hardship","trust","score","created"), r)) for r in cur.fetchall()]
        for r in rows: r["moves"] = json.loads(r["moves"])
        return rows

    def all_rounds(self):
        if self.remote:
            rows = self.remote.table("hc_submissions").select("*").order("created").execute().data
        else:
            cur = self.db.execute("select team,rnd,moves,points,circ,hardship,trust,score,created from hc_submissions")
            rows = [dict(zip(("team","rnd","moves","points","circ","hardship","trust","score","created"), r)) for r in cur.fetchall()]
        for r in rows: r["moves"] = json.loads(r["moves"]) if isinstance(r["moves"], str) else r["moves"]
        return rows

    def save_reflection(self, team, body):
        row = dict(team=team, body=body, created=time.time())
        if self.remote: self.remote.table("hc_reflections").upsert(row, on_conflict="team").execute()
        else:
            self.db.execute("insert or replace into hc_reflections values(?,?,?)", (team, body, row["created"])); self.db.commit()
    def reflections(self):
        if self.remote: return self.remote.table("hc_reflections").select("*").execute().data
        cur = self.db.execute("select team, body, created from hc_reflections")
        return [dict(zip(("team","body","created"), r)) for r in cur.fetchall()]

    def clear(self):
        if self.remote:
            for t, col in (("hc_submissions","team"),("hc_reflections","team")):
                self.remote.table(t).delete().neq(col, "").execute()
            self.remote.table("hc_settings").delete().neq("k", "").execute()
        else:
            self.db.executescript("delete from hc_submissions; delete from hc_reflections; delete from hc_settings;"); self.db.commit()

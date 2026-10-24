"""Optional live push to a Google Sheet through an Apps Script web app (secrets SHEET_WEBHOOK, SHEET_TOKEN)."""
import threading, time
from storage import _secret
from model import LABEL

def enabled():
    return bool(_secret("SHEET_WEBHOOK") and _secret("SHEET_TOKEN"))

def _post(payload):
    try:
        import requests
        payload = dict(payload, token=_secret("SHEET_TOKEN"))
        requests.post(_secret("SHEET_WEBHOOK"), json=payload, timeout=15)
    except Exception:
        pass  # the sheet is a convenience; never break the game

def push(payload, wait=False):
    if not enabled(): return
    if wait: _post(payload)
    else: threading.Thread(target=_post, args=(payload,), daemon=True).start()

def result_row(team, rnd, moves, points, o, ts=None):
    return dict(team=team, quarter=rnd, moves=", ".join(LABEL[m] for m in moves), points_used=points,
                bags_circulating_pct=round(o["circ"] * 100), hardship=round(o["hardship"] * 100),
                trust=round(o["trust"] * 100), score=round(o["score"]), updated=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts or time.time())) + " UTC")

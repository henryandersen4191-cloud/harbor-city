"""Harbor City enforcement model (BSAD 360, Oct 26). Invented teaching numbers. Pure Python."""
MOVES = [
    ("inspect",  "Inspect markets", 3),
    ("factory",  "Check factories and importers", 3),
    ("subsidy",  "Subsidize substitutes for stall owners", 3),
    ("fines",    "Fines on stall owners", 2),
    ("marshals", "Community “bag marshals” with a local NPO", 2),
    ("campaign", "Public campaign", 1),
]
COST = {k: c for k, _, c in MOVES}
LABEL = {k: n for k, n, _ in MOVES}
ROUNDS = {
    1: dict(name="Quarter 1", budget=7, event="Six months after the ban, 80% of bags still circulate. Stall owners say substitutes cost three times as much."),
    2: dict(name="Quarter 2", budget=7, event="Bags are being smuggled in from the neighboring district. Importers who are not checked start to refill the supply."),
    3: dict(name="Quarter 3", budget=5,  event="A new council cuts the enforcement budget to 5 points. Keep what works going with less."),
}
START = dict(c=0.20, s=1.00, a=0.33, t=0.50)  # stall compliance, bag supply, affordability, public trust

def clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def cost_of(moves):
    return sum(COST[m] for m in moves)

def step(state, moves, rnd, history_moves):
    """Advance one quarter. history_moves: list of earlier move-sets (prior rounds)."""
    moves = set(moves)
    I, F, S, P, M, C = (1 if k in moves else 0 for k in ("inspect","factory","subsidy","fines","marshals","campaign"))
    c, s, a, t = state["c"], state["s"], state["a"], state["t"]
    prior_I = sum(1 for h in history_moves if "inspect" in h)
    prior_M = sum(1 for h in history_moves if "marshals" in h)
    # supply upstream: factory checks cut supply; smuggling in quarter 2+ refills it unless importers are checked
    s = s * (1 - 0.35 * F)
    if rnd >= 2:
        s = s + 0.15 * (1 - 0.6 * F)
    s = clip(s, 0.05, 1.0)
    # affordability: subsidy closes the cost gap for good
    a0 = a
    a = clip(a + 0.35 * S)
    # stall compliance
    inspect_eff = 0.18 * I * (1 + 0.8 * P) * (0.8 ** prior_I)      # inspectors are few and stalls adapt
    fine_only = 0.04 * P * (1 - I)                                  # fines with nobody checking barely bite
    afford = 0.20 * S * (1 - a0) / 0.67 + 0.05 * a * (1 if (I or P) else 0)  # first subsidy matters most; gap closes for good
    marsh = 0.12 * M * (0.5 + 0.5 * t) * (1 + 0.25 * prior_M)       # community norms build over time
    camp = 0.06 * C * (1 + 1.5 * M)                                 # campaigns work best with local messengers
    backlash = 0.06 * P * (1 - a) * (1 - S)                         # fines on stalls that cannot afford substitutes
    dc = inspect_eff + fine_only + afford + marsh + camp - backlash
    c = clip(c * 0.88 + 0.60 * dc, 0.0, 0.90)                                # compliance relapses 12% a quarter
    circ = clip(s * (1 - c))
    hardship = clip(0.10 + (1 - a) * (0.35 * c + 0.25 * I + 0.20 * P))
    t = clip(t + 0.07 * M + 0.04 * C + 0.03 * S - 0.15 * max(0.0, hardship - 0.35) - 0.08 * (t - 0.5))
    score = 100 * (0.60 * (1 - circ) + 0.25 * (1 - hardship) + 0.15 * t)
    new = dict(c=c, s=s, a=a, t=t)
    out = dict(circ=circ, hardship=hardship, trust=t, score=score, compliance=c, supply=s, afford=a)
    return new, out

def play(plan):
    """plan: list of move-sets for rounds 1..3. Returns list of outputs."""
    st = dict(START); hist = []; outs = []
    for i, mv in enumerate(plan, start=1):
        st, o = step(st, mv, i, hist); hist.append(set(mv)); outs.append(o)
    return outs

def all_plans(budget):
    keys = [k for k, _, _ in MOVES]; res = []
    for mask in range(1 << len(keys)):
        mv = {keys[i] for i in range(len(keys)) if mask >> i & 1}
        if cost_of(mv) <= budget: res.append(frozenset(mv))
    return res

def feedback(rnd, moves, before, out, prior_moves, budget):
    """Plain-language feedback for one quarter. before = state before the quarter; out = step() output.
    Returns (what_happened: list[str], think_next: list[str])."""
    mv = set(moves)
    b_circ = before["s"] * (1 - before["c"])
    a_circ = out["circ"]
    prior_I = sum(1 for h in prior_moves if "inspect" in h)
    prior_M = sum(1 for h in prior_moves if "marshals" in h)
    got = []
    d = (b_circ - a_circ) * 100
    if abs(d) < 1:
        got.append(f"Bags circulating barely moved: {b_circ*100:.0f}% to {a_circ*100:.0f}%.")
    elif d > 0:
        got.append(f"Bags circulating fell from {b_circ*100:.0f}% to {a_circ*100:.0f}%.")
    else:
        got.append(f"Bags circulating rose from {b_circ*100:.0f}% to {a_circ*100:.0f}%.")
    # upstream supply
    if "factory" in mv:
        got.append("Upstream: checks on factories and importers cut the supply of bags" + (" and blocked most of the smuggling." if rnd >= 2 else "."))
    elif rnd >= 2:
        got.append("Upstream: you did not check importers, so smuggled bags refilled the supply.")
    else:
        got.append("Upstream: no checks on factories or importers, so bags kept flowing in.")
    # stalls
    if "subsidy" in mv:
        got.append(f"Subsidies narrowed the cost gap; substitute affordability is now {out['afford']*100:.0f}.")
    elif out["afford"] < 0.6:
        got.append("Substitutes still cost far more than bags, so stall owners have little reason to switch.")
    if "inspect" in mv:
        got.append("Inspections raised compliance" + (", but stalls adapt and repeat inspections work less each time." if prior_I else ", though inspectors are few."))
    if "fines" in mv and "inspect" not in mv:
        got.append("Fines without inspections rarely bite, because nobody is checking.")
    if "fines" in mv and "subsidy" not in mv and out["afford"] < 0.6:
        got.append("Fining stall owners who cannot afford substitutes caused hardship and cost public trust.")
    if "marshals" in mv:
        got.append("Local bag marshals built community norms" + (", and the effect grows the longer you keep them." if prior_M else "; this works slowly but compounds."))
    if "campaign" in mv:
        got.append("The campaign worked better with local messengers." if "marshals" in mv else "A campaign alone does little without local messengers.")
    if not (mv & {"inspect", "fines", "marshals", "campaign", "subsidy"}):
        got.append("With no pressure on stalls, compliance relapses about 12% a quarter.")
    if out["hardship"] > 0.40:
        got.append(f"Stall-owner hardship is high ({out['hardship']*100:.0f}).")
    if out["trust"] < before["t"] - 0.01:
        got.append("Public trust fell.")
    left = budget - cost_of(mv)
    if left > 0:
        got.append(f"You left {left} point{'s' if left != 1 else ''} unspent.")
    nxt = []
    if rnd == 1:
        nxt = ["Next quarter smuggling begins. Where do the bags actually come from?",
               "Which of your moves will still be working in six months, and which fade?"]
    elif rnd == 2:
        nxt = ["The budget drops to 5 points. Which moves have lasting effects, and which need to be repeated?",
               "Did anything you did hurt stall owners or public trust?"]
    else:
        nxt = ["Which one move would you keep if the budget were cut again?"]
    return got, nxt

def headline(rnd, moves, before, out):
    """One newspaper-style headline for the quarter."""
    mv = set(moves)
    circ, hard, trust, aff = out["circ"], out["hardship"], out["trust"], out["afford"]
    if rnd >= 2 and "factory" not in mv and circ > 0.40:
        return "Smuggled bags flood Harbor City markets"
    if "fines" in mv and "subsidy" not in mv and hard > 0.45:
        return "Stall owners protest as fines bite"
    if circ < 0.15:
        return "Harbor City's markets go nearly bag-free"
    if "subsidy" in mv and "factory" in mv and circ < 0.35:
        return "Cheaper substitutes and port checks turn the tide"
    if "marshals" in mv and trust >= 0.55:
        return "Neighborhood bag marshals win public trust"
    if circ < 0.30:
        return "Bag use plunges across Harbor City"
    if "inspect" in mv and not (mv & {"factory", "subsidy"}):
        return "Inspectors on every corner, but bags still in sight"
    if trust < before["t"] - 0.01:
        return "Public confidence in the bag ban slips"
    if rnd == 3:
        return "Budget cut puts Harbor City's ban to the test"
    return "Harbor City's bag ban: progress is slow"

def reactions(rnd, moves, before, out):
    """Three short stakeholder quotes: (who, quote)."""
    mv = set(moves)
    if "subsidy" in mv and "marshals" in mv:
        so = "The substitutes cost something I can live with, and my neighbors asked me to switch. I did."
    elif "subsidy" in mv:
        so = "The substitutes finally cost something I can live with."
    elif "marshals" in mv:
        so = "A neighbor asked me to stop using bags. That meant more than any inspector."
    elif "fines" in mv and out["afford"] < 0.6:
        so = "You fine me for a bag I cannot afford to replace."
    elif "inspect" in mv:
        so = "The inspectors come by, but the alternatives still cost too much."
    else:
        so = "Nobody checks and nothing has changed for me."
    if "marshals" in mv:
        npo = "Local volunteers are building a habit. It takes time, but it sticks."
    elif "campaign" in mv:
        npo = "Posters help only when people hear the message from someone they trust."
    else:
        npo = "We would help, but nobody has asked us to."
    if "factory" in mv:
        imp = "Checks at the port slowed my shipment, and the bags are harder to move now."
    elif rnd >= 2:
        imp = "Nobody stopped my truck. Business as usual."
    else:
        imp = "The ban is on paper. Nobody is watching the docks."
    return [("A stall owner", so), ("A local NPO volunteer leader", npo), ("An importer", imp)]

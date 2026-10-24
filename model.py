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
    1: dict(name="Quarter 1", budget=10, event="Six months after the ban, 80% of bags still circulate. Stall owners say substitutes cost three times as much."),
    2: dict(name="Quarter 2", budget=10, event="Bags are being smuggled in from the neighboring district. Importers who are not checked start to refill the supply."),
    3: dict(name="Quarter 3", budget=8,  event="A new council cuts the enforcement budget to 8 points. Keep what works going with less."),
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

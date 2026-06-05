
from __future__ import annotations
import json, random, math
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

SCHEMA_VERSION = "2026-06-05-v5-spotify"
POINTS_EXACT_SCORE = 3
POINTS_OUTCOME = 1
POINTS_CHAMPION = 5

GROUPS: Dict[str, List[str]] = {
    "A": ["Mexico", "South Africa", "Korea Republic", "Czechia"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Türkiye"],
    "E": ["Germany", "Curaçao", "Côte d'Ivoire", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "IR Iran", "New Zealand"],
    "H": ["Spain", "Cabo Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "Congo DR", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}
PAIRINGS_IDX = [(0, 1), (2, 3), (3, 1), (0, 2), (3, 0), (1, 2)]
ROUND_OF_32 = [
    (73, "2A", "2B"), (74, "1E", "3A/B/C/D/F"), (75, "1F", "2C"), (76, "1C", "2F"),
    (77, "1I", "3C/D/F/G/H"), (78, "2E", "2I"), (79, "1A", "3C/E/F/H/I"),
    (80, "1L", "3E/H/I/J/K"), (81, "1D", "3B/E/F/I/J"), (82, "1G", "3A/E/H/I/J"),
    (83, "2K", "2L"), (84, "1H", "2J"), (85, "1B", "3E/F/G/I/J"),
    (86, "1J", "2H"), (87, "1K", "3D/E/I/J/L"), (88, "2D", "2G"),
]
NEXT_ROUNDS = {
    "Åttedelsfinaler": [(89, 74, 77), (90, 73, 75), (91, 83, 84), (92, 81, 82), (93, 76, 78), (94, 79, 80), (95, 86, 88), (96, 85, 87)],
    "Kvartfinaler": [(97, 89, 90), (98, 93, 94), (99, 91, 92), (100, 95, 96)],
    "Semifinaler": [(101, 97, 98), (102, 99, 100)],
    "Bronsefinale": [(103, 101, 102)],
    "Finale": [(104, 101, 102)],
}
PHASE_ORDER = ["16-delsfinaler", "Åttedelsfinaler", "Kvartfinaler", "Semifinaler", "Bronsefinale", "Finale"]

TEAM_STRENGTH = {
    "Spain": 0.175, "France": 0.169, "England": 0.128, "Portugal": 0.098, "Brazil": 0.098,
    "Argentina": 0.096, "Germany": 0.064, "Netherlands": 0.047, "Norway": 0.030, "Belgium": 0.025,
    "Colombia": 0.024, "Japan": 0.020, "Uruguay": 0.015, "Morocco": 0.015, "USA": 0.015,
    "Switzerland": 0.012, "Türkiye": 0.012, "Mexico": 0.012, "Croatia": 0.012, "Senegal": 0.010,
    "Ecuador": 0.010, "Sweden": 0.008, "Canada": 0.007, "Paraguay": 0.007, "Austria": 0.007,
    "Scotland": 0.004, "Bosnia and Herzegovina": 0.004, "Czechia": 0.003, "Egypt": 0.003,
    "Côte d'Ivoire": 0.003, "Algeria": 0.0025, "Ghana": 0.0025, "Australia": 0.002,
    "Korea Republic": 0.002, "South Africa": 0.0015, "Qatar": 0.0015, "IR Iran": 0.0015,
    "Tunisia": 0.0015, "Congo DR": 0.0012, "Uzbekistan": 0.0012, "Panama": 0.0012,
    "Iraq": 0.0012, "Saudi Arabia": 0.0012, "New Zealand": 0.0012, "Jordan": 0.0012,
    "Haiti": 0.0012, "Curaçao": 0.0010, "Cabo Verde": 0.0010,
}

def now_iso() -> str: return datetime.now().isoformat(timespec="seconds")

def build_group_matches() -> List[dict]:
    matches, n = [], 1
    for group, teams in GROUPS.items():
        for a, b in PAIRINGS_IDX:
            matches.append({"match_no": n, "phase": "Gruppespill", "group": group, "team_a": teams[a], "team_b": teams[b]})
            n += 1
    return matches
GROUP_MATCHES = build_group_matches()

def new_prediction(participant: str = "") -> dict:
    return {"schema_version": SCHEMA_VERSION, "type": "participant_prediction", "participant": participant, "created_at": now_iso(), "updated_at": now_iso(), "group_scores": {}, "third_slot_overrides": {}, "knockout_predictions": {}, "champion": ""}

def new_actual_results() -> dict:
    return {"schema_version": SCHEMA_VERSION, "type": "actual_results", "updated_at": now_iso(), "group_scores": {}, "third_slot_overrides": {}, "knockout_results": {}, "champion": ""}

def normalize_score(obj: Optional[dict]) -> dict:
    obj = obj or {}
    return {"team_a": obj.get("team_a", ""), "team_b": obj.get("team_b", ""), "goals_a": obj.get("goals_a", obj.get("home")), "goals_b": obj.get("goals_b", obj.get("away")), "winner": obj.get("winner", "")}

def get_outcome(a: int, b: int) -> str: return "H" if a > b else "B" if b > a else "U"

def winner_from_score(team_a: str, team_b: str, goals_a, goals_b, manual_winner: str = "") -> str:
    if goals_a is None or goals_b is None: return ""
    goals_a, goals_b = int(goals_a), int(goals_b)
    if goals_a > goals_b: return team_a
    if goals_b > goals_a: return team_b
    return manual_winner if manual_winner in [team_a, team_b] else ""

def strength(team: str) -> float: return TEAM_STRENGTH.get(team, 0.001)

def poisson(lam: float, rng: random.Random) -> int:
    lam = max(0.05, min(lam, 4.5)); L, k, p = math.exp(-lam), 0, 1.0
    while p > L:
        k += 1; p *= rng.random()
    return k - 1

def expected_goals(team_a: str, team_b: str, knockout: bool = False) -> tuple[float, float]:
    sa, sb = strength(team_a), strength(team_b)
    diff = math.log((sa + 0.002) / (sb + 0.002))
    base = 1.18 if not knockout else 1.08
    return max(0.25, min(3.2, base + 0.32 * diff)), max(0.25, min(3.2, base - 0.32 * diff))

def random_score(team_a: str, team_b: str, rng: random.Random, knockout: bool = False) -> dict:
    la, lb = expected_goals(team_a, team_b, knockout)
    ga, gb = poisson(la, rng), poisson(lb, rng)
    winner = winner_from_score(team_a, team_b, ga, gb, "")
    if knockout and ga == gb:
        pa = strength(team_a) / (strength(team_a) + strength(team_b) + 1e-9)
        winner = team_a if rng.random() < pa else team_b
    return {"team_a": team_a, "team_b": team_b, "goals_a": int(ga), "goals_b": int(gb), "winner": winner}

def group_table(group: str, scores: dict) -> pd.DataFrame:
    rows = [{"Lag": t, "Seed": i, "S": 0, "V": 0, "U": 0, "T": 0, "MF": 0, "MM": 0, "MS": 0, "P": 0} for i, t in enumerate(GROUPS[group], 1)]
    table = pd.DataFrame(rows).set_index("Lag")
    for match in [m for m in GROUP_MATCHES if m["group"] == group]:
        s = normalize_score(scores.get(str(match["match_no"])))
        if s["goals_a"] is None or s["goals_b"] is None: continue
        a, b, ga, gb = match["team_a"], match["team_b"], int(s["goals_a"]), int(s["goals_b"])
        table.loc[a, ["S", "MF", "MM"]] += [1, ga, gb]
        table.loc[b, ["S", "MF", "MM"]] += [1, gb, ga]
        if ga > gb:
            table.loc[a, ["V", "P"]] += [1, 3]; table.loc[b, "T"] += 1
        elif gb > ga:
            table.loc[b, ["V", "P"]] += [1, 3]; table.loc[a, "T"] += 1
        else:
            table.loc[a, ["U", "P"]] += [1, 1]; table.loc[b, ["U", "P"]] += [1, 1]
    table["MS"] = table["MF"] - table["MM"]
    table = table.reset_index().sort_values(["P", "MS", "MF", "Seed"], ascending=[False, False, False, True]).reset_index(drop=True)
    table.insert(0, "Plass", range(1, len(table) + 1))
    return table

def qualifiers(group_scores: dict) -> dict:
    tables = {g: group_table(g, group_scores) for g in GROUPS}
    winners, runners, thirds = {}, {}, []
    for g, table in tables.items():
        winners[g], runners[g] = table.iloc[0]["Lag"], table.iloc[1]["Lag"]
        third = table.iloc[2]
        thirds.append({"group": g, "team": third["Lag"], "P": int(third["P"]), "MS": int(third["MS"]), "MF": int(third["MF"]), "Seed": int(third["Seed"])})
    thirds_df = pd.DataFrame(thirds).sort_values(["P", "MS", "MF", "Seed"], ascending=[False, False, False, True]).reset_index(drop=True)
    return {"tables": tables, "winners": winners, "runners_up": runners, "thirds": thirds_df, "advancing_thirds": thirds_df.head(8).copy()}

def slot_allowed_map() -> Dict[str, List[str]]:
    out = {}
    for _, a, b in ROUND_OF_32:
        for seed in (a, b):
            if seed.startswith("3"): out[seed] = seed[1:].split("/")
    return out

def find_third_slot_assignment(advancing_groups: List[str], allowed: Dict[str, List[str]]) -> Dict[str, str]:
    slots = list(allowed.keys()); slots_sorted = sorted(slots, key=lambda s: len([g for g in allowed[s] if g in advancing_groups]))
    assign, used = {}, set()
    def backtrack(i: int) -> bool:
        if i == len(slots_sorted): return True
        slot = slots_sorted[i]
        for g in [x for x in allowed[slot] if x in advancing_groups and x not in used]:
            assign[slot] = g; used.add(g)
            if backtrack(i + 1): return True
            used.remove(g); assign.pop(slot, None)
        return False
    backtrack(0)
    return {s: assign.get(s, "") for s in slots}

def resolve_seed(seed: str, q: dict, overrides: dict) -> str:
    if seed.startswith("1") and len(seed) == 2: return q["winners"].get(seed[1], "")
    if seed.startswith("2") and len(seed) == 2: return q["runners_up"].get(seed[1], "")
    if seed.startswith("3"):
        adv = q["advancing_thirds"]["group"].tolist()
        group = overrides.get(seed) or find_third_slot_assignment(adv, slot_allowed_map()).get(seed, "")
        if not group: return ""
        row = q["advancing_thirds"].loc[q["advancing_thirds"]["group"] == group]
        return "" if row.empty else row.iloc[0]["team"]
    return seed

def loser_of(match: dict) -> str:
    a, b, w = match.get("team_a", ""), match.get("team_b", ""), match.get("winner", "")
    return b if w == a else a if w == b else ""

def compute_bracket(group_scores: dict, third_slot_overrides: dict, knockout_scores: dict) -> Dict[int, dict]:
    q, bracket = qualifiers(group_scores), {}
    for no, seed_a, seed_b in ROUND_OF_32:
        a, b, s = resolve_seed(seed_a, q, third_slot_overrides), resolve_seed(seed_b, q, third_slot_overrides), normalize_score(knockout_scores.get(str(no)))
        bracket[no] = {"match_no": no, "phase": "16-delsfinaler", "seed_a": seed_a, "seed_b": seed_b, "team_a": a, "team_b": b, "goals_a": s["goals_a"], "goals_b": s["goals_b"], "winner": winner_from_score(a, b, s["goals_a"], s["goals_b"], s["winner"])}
    for phase, matches in NEXT_ROUNDS.items():
        for no, prev_a, prev_b in matches:
            a, b = (loser_of(bracket.get(prev_a, {})), loser_of(bracket.get(prev_b, {}))) if phase == "Bronsefinale" else (bracket.get(prev_a, {}).get("winner", ""), bracket.get(prev_b, {}).get("winner", ""))
            s = normalize_score(knockout_scores.get(str(no)))
            bracket[no] = {"match_no": no, "phase": phase, "seed_a": ("T" if phase == "Bronsefinale" else "V") + str(prev_a), "seed_b": ("T" if phase == "Bronsefinale" else "V") + str(prev_b), "team_a": a, "team_b": b, "goals_a": s["goals_a"], "goals_b": s["goals_b"], "winner": winner_from_score(a, b, s["goals_a"], s["goals_b"], s["winner"])}
    return bracket

def fill_try_luck(data: dict, knockout_key: str = "knockout_predictions", seed: Optional[int] = None) -> dict:
    rng = random.Random(seed if seed is not None else random.SystemRandom().randint(1, 10**12))
    participant = data.get("participant", ""); kind = data.get("type", "participant_prediction")
    data.clear(); data.update(new_actual_results() if knockout_key == "knockout_results" else new_prediction(participant))
    data["type"] = kind
    if participant: data["participant"] = participant
    for m in GROUP_MATCHES:
        data["group_scores"][str(m["match_no"])] = random_score(m["team_a"], m["team_b"], rng, knockout=False)
    data["third_slot_overrides"] = {}
    for phase in PHASE_ORDER:
        bracket = compute_bracket(data["group_scores"], data["third_slot_overrides"], data[knockout_key])
        for no, m in sorted([(no, x) for no, x in bracket.items() if x["phase"] == phase]):
            if m["team_a"] and m["team_b"]:
                data[knockout_key][str(no)] = random_score(m["team_a"], m["team_b"], rng, knockout=True)
    bracket = compute_bracket(data["group_scores"], data["third_slot_overrides"], data[knockout_key])
    data["champion"] = bracket.get(104, {}).get("winner", ""); data["updated_at"] = now_iso()
    return data

def all_matches_for_scoring(data: dict, actual: bool = False) -> Dict[str, dict]:
    ko_key = "knockout_results" if actual else "knockout_predictions"
    bracket, out = compute_bracket(data.get("group_scores", {}), data.get("third_slot_overrides", {}), data.get(ko_key, {})), {}
    for m in GROUP_MATCHES:
        key = str(m["match_no"]); s = normalize_score(data.get("group_scores", {}).get(key))
        out[key] = {"match_no": m["match_no"], "phase": "Gruppespill", "team_a": m["team_a"], "team_b": m["team_b"], "goals_a": s["goals_a"], "goals_b": s["goals_b"], "winner": winner_from_score(m["team_a"], m["team_b"], s["goals_a"], s["goals_b"], s["winner"])}
    for no, m in bracket.items(): out[str(no)] = m
    return out

def score_one_match(pred: dict, actual: dict) -> int:
    if not pred or not actual or pred.get("goals_a") is None or pred.get("goals_b") is None or actual.get("goals_a") is None or actual.get("goals_b") is None: return 0
    pa, pb, aa, ab = pred.get("team_a", ""), pred.get("team_b", ""), actual.get("team_a", ""), actual.get("team_b", "")
    pga, pgb, aga, agb = int(pred["goals_a"]), int(pred["goals_b"]), int(actual["goals_a"]), int(actual["goals_b"])
    if pa == aa and pb == ab: pass
    elif pa == ab and pb == aa: pga, pgb = pgb, pga
    else: return 0
    return POINTS_EXACT_SCORE if (pga, pgb) == (aga, agb) else POINTS_OUTCOME if get_outcome(pga, pgb) == get_outcome(aga, agb) else 0

def format_score(m: dict) -> str:
    return "" if not m or m.get("goals_a") is None or m.get("goals_b") is None else f"{m.get('goals_a')} - {m.get('goals_b')}"

def score_prediction(prediction: dict, actual_results: dict) -> dict:
    pred_matches, actual_matches, rows, total = all_matches_for_scoring(prediction, False), all_matches_for_scoring(actual_results, True), [], 0
    for no in range(1, 105):
        key = str(no); pts = score_one_match(pred_matches.get(key, {}), actual_matches.get(key, {})); total += pts
        rows.append({"Kamp": no, "Fase": actual_matches.get(key, {}).get("phase", ""), "Poeng": pts, "Pred lag": f"{pred_matches.get(key, {}).get('team_a','')} - {pred_matches.get(key, {}).get('team_b','')}", "Pred resultat": format_score(pred_matches.get(key, {})), "Fasit lag": f"{actual_matches.get(key, {}).get('team_a','')} - {actual_matches.get(key, {}).get('team_b','')}", "Fasit resultat": format_score(actual_matches.get(key, {}))})
    bonus = POINTS_CHAMPION if prediction.get("champion") and prediction.get("champion") == actual_results.get("champion") else 0
    return {"participant": prediction.get("participant", "Ukjent"), "match_points": total, "champion_bonus": bonus, "total": total + bonus, "details": rows}

def load_json_bytes(uploaded_file) -> dict:
    return json.loads(uploaded_file.getvalue().decode("utf-8"))

def download_json(data: dict) -> str:
    data = dict(data); data["updated_at"] = now_iso(); return json.dumps(data, ensure_ascii=False, indent=2)

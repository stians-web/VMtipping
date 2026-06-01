
from __future__ import annotations
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

SCHEMA_VERSION = "2026-06-01-v3"
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

# FIFA Round of 32 = norsk 16-delsfinaler.
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


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def build_group_matches() -> List[dict]:
    matches = []
    n = 1
    for group, teams in GROUPS.items():
        for a, b in PAIRINGS_IDX:
            matches.append({"match_no": n, "phase": "Gruppespill", "group": group, "team_a": teams[a], "team_b": teams[b]})
            n += 1
    return matches

GROUP_MATCHES = build_group_matches()


def new_prediction(participant: str = "") -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "participant_prediction",
        "participant": participant,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "group_scores": {},
        "third_slot_overrides": {},
        "knockout_predictions": {},
        "champion": "",
    }


def new_actual_results() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "actual_results",
        "updated_at": now_iso(),
        "group_scores": {},
        "third_slot_overrides": {},
        "knockout_results": {},
        "champion": "",
    }


def normalize_score(obj: Optional[dict]) -> dict:
    obj = obj or {}
    return {
        "team_a": obj.get("team_a", ""),
        "team_b": obj.get("team_b", ""),
        "goals_a": obj.get("goals_a", obj.get("home")),
        "goals_b": obj.get("goals_b", obj.get("away")),
        "winner": obj.get("winner", ""),
    }


def get_outcome(a: int, b: int) -> str:
    return "H" if a > b else "B" if b > a else "U"


def winner_from_score(team_a: str, team_b: str, goals_a, goals_b, manual_winner: str = "") -> str:
    if goals_a is None or goals_b is None:
        return ""
    goals_a, goals_b = int(goals_a), int(goals_b)
    if goals_a > goals_b:
        return team_a
    if goals_b > goals_a:
        return team_b
    return manual_winner if manual_winner in [team_a, team_b] else ""


def group_table(group: str, scores: dict) -> pd.DataFrame:
    rows = []
    for seed, team in enumerate(GROUPS[group], start=1):
        rows.append({"Lag": team, "Seed": seed, "S": 0, "V": 0, "U": 0, "T": 0, "MF": 0, "MM": 0, "MS": 0, "P": 0})
    table = pd.DataFrame(rows).set_index("Lag")
    for match in [m for m in GROUP_MATCHES if m["group"] == group]:
        key = str(match["match_no"])
        s = normalize_score(scores.get(key))
        if s["goals_a"] is None or s["goals_b"] is None:
            continue
        a, b = match["team_a"], match["team_b"]
        ga, gb = int(s["goals_a"]), int(s["goals_b"])
        table.loc[a, ["S", "MF", "MM"]] += [1, ga, gb]
        table.loc[b, ["S", "MF", "MM"]] += [1, gb, ga]
        if ga > gb:
            table.loc[a, ["V", "P"]] += [1, 3]
            table.loc[b, "T"] += 1
        elif gb > ga:
            table.loc[b, ["V", "P"]] += [1, 3]
            table.loc[a, "T"] += 1
        else:
            table.loc[a, ["U", "P"]] += [1, 1]
            table.loc[b, ["U", "P"]] += [1, 1]
    table["MS"] = table["MF"] - table["MM"]
    table = table.reset_index().sort_values(["P", "MS", "MF", "Seed"], ascending=[False, False, False, True]).reset_index(drop=True)
    table.insert(0, "Plass", range(1, len(table) + 1))
    return table


def qualifiers(group_scores: dict) -> dict:
    tables = {g: group_table(g, group_scores) for g in GROUPS}
    winners, runners, thirds = {}, {}, []
    for g, table in tables.items():
        winners[g] = table.iloc[0]["Lag"]
        runners[g] = table.iloc[1]["Lag"]
        third = table.iloc[2]
        thirds.append({"group": g, "team": third["Lag"], "P": int(third["P"]), "MS": int(third["MS"]), "MF": int(third["MF"]), "Seed": int(third["Seed"])})
    thirds_df = pd.DataFrame(thirds).sort_values(["P", "MS", "MF", "Seed"], ascending=[False, False, False, True]).reset_index(drop=True)
    return {"tables": tables, "winners": winners, "runners_up": runners, "thirds": thirds_df, "advancing_thirds": thirds_df.head(8).copy()}


def slot_allowed_map() -> Dict[str, List[str]]:
    out = {}
    for _, a, b in ROUND_OF_32:
        for seed in (a, b):
            if seed.startswith("3"):
                out[seed] = seed[1:].split("/")
    return out


def find_third_slot_assignment(advancing_groups: List[str], allowed: Dict[str, List[str]]) -> Dict[str, str]:
    slots = list(allowed.keys())
    slots_sorted = sorted(slots, key=lambda s: len([g for g in allowed[s] if g in advancing_groups]))
    assign, used = {}, set()
    def backtrack(i: int) -> bool:
        if i == len(slots_sorted):
            return True
        slot = slots_sorted[i]
        for g in [x for x in allowed[slot] if x in advancing_groups and x not in used]:
            assign[slot] = g; used.add(g)
            if backtrack(i+1):
                return True
            used.remove(g); assign.pop(slot, None)
        return False
    backtrack(0)
    return {s: assign.get(s, "") for s in slots}


def resolve_seed(seed: str, q: dict, overrides: dict) -> str:
    if seed.startswith("1") and len(seed) == 2:
        return q["winners"].get(seed[1], "")
    if seed.startswith("2") and len(seed) == 2:
        return q["runners_up"].get(seed[1], "")
    if seed.startswith("3"):
        adv = q["advancing_thirds"]["group"].tolist()
        auto = find_third_slot_assignment(adv, slot_allowed_map())
        group = overrides.get(seed) or auto.get(seed, "")
        if not group:
            return ""
        row = q["advancing_thirds"].loc[q["advancing_thirds"]["group"] == group]
        return "" if row.empty else row.iloc[0]["team"]
    return seed


def loser_of(match: dict) -> str:
    a, b, w = match.get("team_a", ""), match.get("team_b", ""), match.get("winner", "")
    if w == a:
        return b
    if w == b:
        return a
    return ""


def compute_bracket(group_scores: dict, third_slot_overrides: dict, knockout_scores: dict) -> Dict[int, dict]:
    q = qualifiers(group_scores)
    bracket = {}
    for no, seed_a, seed_b in ROUND_OF_32:
        a, b = resolve_seed(seed_a, q, third_slot_overrides), resolve_seed(seed_b, q, third_slot_overrides)
        s = normalize_score(knockout_scores.get(str(no)))
        bracket[no] = {"match_no": no, "phase": "16-delsfinaler", "seed_a": seed_a, "seed_b": seed_b, "team_a": a, "team_b": b, "goals_a": s["goals_a"], "goals_b": s["goals_b"], "winner": winner_from_score(a, b, s["goals_a"], s["goals_b"], s["winner"])}
    for phase, matches in NEXT_ROUNDS.items():
        for no, prev_a, prev_b in matches:
            if phase == "Bronsefinale":
                a, b = loser_of(bracket.get(prev_a, {})), loser_of(bracket.get(prev_b, {}))
            else:
                a, b = bracket.get(prev_a, {}).get("winner", ""), bracket.get(prev_b, {}).get("winner", "")
            s = normalize_score(knockout_scores.get(str(no)))
            bracket[no] = {"match_no": no, "phase": phase, "seed_a": ("T" if phase == "Bronsefinale" else "V") + str(prev_a), "seed_b": ("T" if phase == "Bronsefinale" else "V") + str(prev_b), "team_a": a, "team_b": b, "goals_a": s["goals_a"], "goals_b": s["goals_b"], "winner": winner_from_score(a, b, s["goals_a"], s["goals_b"], s["winner"])}
    return bracket


def all_matches_for_scoring(data: dict, actual: bool = False) -> Dict[str, dict]:
    ko_key = "knockout_results" if actual else "knockout_predictions"
    bracket = compute_bracket(data.get("group_scores", {}), data.get("third_slot_overrides", {}), data.get(ko_key, {}))
    out = {}
    for m in GROUP_MATCHES:
        key = str(m["match_no"])
        s = normalize_score(data.get("group_scores", {}).get(key))
        out[key] = {"match_no": m["match_no"], "phase": "Gruppespill", "team_a": m["team_a"], "team_b": m["team_b"], "goals_a": s["goals_a"], "goals_b": s["goals_b"], "winner": winner_from_score(m["team_a"], m["team_b"], s["goals_a"], s["goals_b"], s["winner"])}
    for no, m in bracket.items():
        out[str(no)] = m
    return out


def score_one_match(pred: dict, actual: dict) -> int:
    if not pred or not actual:
        return 0
    if pred.get("goals_a") is None or pred.get("goals_b") is None or actual.get("goals_a") is None or actual.get("goals_b") is None:
        return 0
    pa, pb = pred.get("team_a", ""), pred.get("team_b", "")
    aa, ab = actual.get("team_a", ""), actual.get("team_b", "")
    pga, pgb = int(pred["goals_a"]), int(pred["goals_b"])
    aga, agb = int(actual["goals_a"]), int(actual["goals_b"])
    if pa == aa and pb == ab:
        pass
    elif pa == ab and pb == aa:
        pga, pgb = pgb, pga
    else:
        return 0
    if pga == aga and pgb == agb:
        return POINTS_EXACT_SCORE
    if get_outcome(pga, pgb) == get_outcome(aga, agb):
        return POINTS_OUTCOME
    return 0


def format_score(m: dict) -> str:
    return "" if not m or m.get("goals_a") is None or m.get("goals_b") is None else f"{m.get('goals_a')} - {m.get('goals_b')}"


def score_prediction(prediction: dict, actual_results: dict) -> dict:
    pred_matches = all_matches_for_scoring(prediction, actual=False)
    actual_matches = all_matches_for_scoring(actual_results, actual=True)
    rows, total = [], 0
    for no in range(1, 105):
        key = str(no)
        pts = score_one_match(pred_matches.get(key, {}), actual_matches.get(key, {}))
        total += pts
        rows.append({"Kamp": no, "Fase": actual_matches.get(key, {}).get("phase", ""), "Poeng": pts, "Pred lag": f"{pred_matches.get(key, {}).get('team_a','')} - {pred_matches.get(key, {}).get('team_b','')}", "Pred resultat": format_score(pred_matches.get(key, {})), "Fasit lag": f"{actual_matches.get(key, {}).get('team_a','')} - {actual_matches.get(key, {}).get('team_b','')}", "Fasit resultat": format_score(actual_matches.get(key, {}))})
    bonus = POINTS_CHAMPION if prediction.get("champion") and prediction.get("champion") == actual_results.get("champion") else 0
    return {"participant": prediction.get("participant", "Ukjent"), "match_points": total, "champion_bonus": bonus, "total": total + bonus, "details": rows}


def load_json_bytes(uploaded_file) -> dict:
    return json.loads(uploaded_file.getvalue().decode("utf-8"))


def download_json(data: dict) -> str:
    data = dict(data)
    data["updated_at"] = now_iso()
    return json.dumps(data, ensure_ascii=False, indent=2)

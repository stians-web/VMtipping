
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
import json
from pathlib import Path

import pandas as pd

SCHEMA_VERSION = "2026-05-20-v2"

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

# Kamprekkefølge per gruppe. Hvis du ønsker eksakt dato/stadion kan dette utvides med offisiell kampkalender.
PAIRINGS_IDX = [(0, 1), (2, 3), (3, 1), (0, 2), (3, 0), (1, 2)]

# FIFA-slotter for første utslagsrunde. På norsk heter Round of 32 = 16-delsfinaler.
ROUND_OF_32 = [
    (73, "2A", "2B"),
    (74, "1E", "3A/B/C/D/F"),
    (75, "1F", "2C"),
    (76, "1C", "2F"),
    (77, "1I", "3C/D/F/G/H"),
    (78, "2E", "2I"),
    (79, "1A", "3C/E/F/H/I"),
    (80, "1L", "3E/H/I/J/K"),
    (81, "1D", "3B/E/F/I/J"),
    (82, "1G", "3A/E/H/I/J"),
    (83, "2K", "2L"),
    (84, "1H", "2J"),
    (85, "1B", "3E/F/G/I/J"),
    (86, "1J", "2H"),
    (87, "1K", "3D/E/I/J/L"),
    (88, "2D", "2G"),
]

# Korrekte norske navn:
# Round of 32 = 16-delsfinaler, Round of 16 = åttedelsfinaler.
NEXT_ROUNDS = {
    "Åttedelsfinaler": [(89, 74, 77), (90, 73, 75), (91, 83, 84), (92, 81, 82), (93, 76, 78), (94, 79, 80), (95, 86, 88), (96, 85, 87)],
    "Kvartfinaler": [(97, 89, 90), (98, 93, 94), (99, 91, 92), (100, 95, 96)],
    "Semifinaler": [(101, 97, 98), (102, 99, 100)],
    "Bronsefinale": [(103, 101, 102)],
    "Finale": [(104, 101, 102)],
}

PHASE_ORDER = ["16-delsfinaler", "Åttedelsfinaler", "Kvartfinaler", "Semifinaler", "Bronsefinale", "Finale"]

POINTS_EXACT_SCORE = 3
POINTS_OUTCOME = 1
POINTS_CHAMPION = 5


def build_group_matches() -> List[dict]:
    matches = []
    match_no = 1
    for group, teams in GROUPS.items():
        for home_idx, away_idx in PAIRINGS_IDX:
            matches.append({
                "match_no": match_no,
                "phase": "Gruppespill",
                "group": group,
                "team_a": teams[home_idx],
                "team_b": teams[away_idx],
                "seed_a": "",
                "seed_b": "",
            })
            match_no += 1
    return matches

GROUP_MATCHES = build_group_matches()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_prediction(participant: str) -> dict:
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


def normalise_score_obj(obj: Optional[dict]) -> dict:
    obj = obj or {}
    return {
        "goals_a": obj.get("goals_a", obj.get("home")),
        "goals_b": obj.get("goals_b", obj.get("away")),
        "winner": obj.get("winner", ""),
        "team_a": obj.get("team_a", ""),
        "team_b": obj.get("team_b", ""),
    }


def is_complete_score(obj: Optional[dict]) -> bool:
    s = normalise_score_obj(obj)
    return s["goals_a"] is not None and s["goals_b"] is not None


def get_outcome(goals_a: int, goals_b: int) -> str:
    if goals_a > goals_b:
        return "H"
    if goals_a < goals_b:
        return "B"
    return "U"


def winner_from_score(team_a: str, team_b: str, goals_a: Optional[int], goals_b: Optional[int], manual_winner: str = "") -> str:
    if goals_a is None or goals_b is None:
        return ""
    if goals_a > goals_b:
        return team_a
    if goals_b > goals_a:
        return team_b
    return manual_winner if manual_winner in [team_a, team_b] else ""


def group_table(group: str, group_scores: dict) -> pd.DataFrame:
    rows = []
    for seed, team in enumerate(GROUPS[group], start=1):
        rows.append({"Lag": team, "Seed": seed, "S": 0, "V": 0, "U": 0, "T": 0, "MF": 0, "MM": 0, "MS": 0, "P": 0})
    table = pd.DataFrame(rows).set_index("Lag")

    for match in [m for m in GROUP_MATCHES if m["group"] == group]:
        key = str(match["match_no"])
        score = normalise_score_obj(group_scores.get(key))
        if score["goals_a"] is None or score["goals_b"] is None:
            continue
        a, b = match["team_a"], match["team_b"]
        ga, gb = int(score["goals_a"]), int(score["goals_b"])
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
    # Forenklet, deterministisk tiebreak for tippekonkurranse: P, målforskjell, mål for, seed.
    table = table.reset_index().sort_values(["P", "MS", "MF", "Seed"], ascending=[False, False, False, True])
    table.insert(0, "Plass", range(1, len(table) + 1))
    return table


def all_group_tables(group_scores: dict) -> Dict[str, pd.DataFrame]:
    return {g: group_table(g, group_scores) for g in GROUPS}


def qualifiers(group_scores: dict) -> dict:
    tables = all_group_tables(group_scores)
    winners, runners_up, thirds = {}, {}, []
    for group, table in tables.items():
        winners[group] = table.iloc[0]["Lag"]
        runners_up[group] = table.iloc[1]["Lag"]
        third = table.iloc[2]
        thirds.append({
            "group": group,
            "team": third["Lag"],
            "P": int(third["P"]),
            "MS": int(third["MS"]),
            "MF": int(third["MF"]),
            "Seed": int(third["Seed"]),
        })
    thirds_df = pd.DataFrame(thirds).sort_values(["P", "MS", "MF", "Seed"], ascending=[False, False, False, True]).reset_index(drop=True)
    advancing_thirds = thirds_df.head(8).copy()
    return {"tables": tables, "winners": winners, "runners_up": runners_up, "thirds": thirds_df, "advancing_thirds": advancing_thirds}


def slot_allowed_map() -> Dict[str, List[str]]:
    slots = {}
    for _, a, b in ROUND_OF_32:
        for seed in [a, b]:
            if seed.startswith("3"):
                slots[seed] = seed[1:].split("/")
    return slots


def find_third_slot_assignment(advancing_groups: List[str], slot_allowed: Dict[str, List[str]]) -> Dict[str, str]:
    slots = list(slot_allowed.keys())
    slots_sorted = sorted(slots, key=lambda s: len([g for g in slot_allowed[s] if g in advancing_groups]))
    assignment, used = {}, set()

    def backtrack(i: int) -> bool:
        if i == len(slots_sorted):
            return True
        slot = slots_sorted[i]
        for group in [g for g in slot_allowed[slot] if g in advancing_groups and g not in used]:
            assignment[slot] = group
            used.add(group)
            if backtrack(i + 1):
                return True
            used.remove(group)
            assignment.pop(slot, None)
        return False

    if not backtrack(0):
        return {slot: "" for slot in slots}
    return {slot: assignment.get(slot, "") for slot in slots}


def resolve_seed(seed: str, q: dict, third_slot_overrides: dict) -> str:
    if seed.startswith("1") and len(seed) == 2:
        return q["winners"].get(seed[1], "")
    if seed.startswith("2") and len(seed) == 2:
        return q["runners_up"].get(seed[1], "")
    if seed.startswith("3"):
        adv_groups = q["advancing_thirds"]["group"].tolist()
        auto = find_third_slot_assignment(adv_groups, slot_allowed_map())
        group = third_slot_overrides.get(seed) or auto.get(seed, "")
        if not group:
            return ""
        row = q["advancing_thirds"].loc[q["advancing_thirds"]["group"] == group]
        return "" if row.empty else row.iloc[0]["team"]
    return seed


def compute_bracket(group_scores: dict, third_slot_overrides: dict, knockout_scores: dict) -> Dict[int, dict]:
    q = qualifiers(group_scores)
    bracket: Dict[int, dict] = {}
    for match_no, seed_a, seed_b in ROUND_OF_32:
        team_a = resolve_seed(seed_a, q, third_slot_overrides)
        team_b = resolve_seed(seed_b, q, third_slot_overrides)
        pred = normalise_score_obj(knockout_scores.get(str(match_no)))
        winner = winner_from_score(team_a, team_b, pred["goals_a"], pred["goals_b"], pred["winner"])
        bracket[match_no] = {
            "match_no": match_no,
            "phase": "16-delsfinaler",
            "seed_a": seed_a,
            "seed_b": seed_b,
            "team_a": team_a,
            "team_b": team_b,
            "goals_a": pred["goals_a"],
            "goals_b": pred["goals_b"],
            "winner": winner,
        }

    for phase, matches in NEXT_ROUNDS.items():
        for match_no, prev_a, prev_b in matches:
            if phase == "Bronsefinale":
                team_a = loser_of(bracket.get(prev_a, {}))
                team_b = loser_of(bracket.get(prev_b, {}))
            else:
                team_a = bracket.get(prev_a, {}).get("winner", "")
                team_b = bracket.get(prev_b, {}).get("winner", "")
            pred = normalise_score_obj(knockout_scores.get(str(match_no)))
            winner = winner_from_score(team_a, team_b, pred["goals_a"], pred["goals_b"], pred["winner"])
            bracket[match_no] = {
                "match_no": match_no,
                "phase": phase,
                "seed_a": f"{'T' if phase == 'Bronsefinale' else 'V'}{prev_a}",
                "seed_b": f"{'T' if phase == 'Bronsefinale' else 'V'}{prev_b}",
                "team_a": team_a,
                "team_b": team_b,
                "goals_a": pred["goals_a"],
                "goals_b": pred["goals_b"],
                "winner": winner,
            }
    return bracket


def loser_of(match: dict) -> str:
    a, b, w = match.get("team_a", ""), match.get("team_b", ""), match.get("winner", "")
    if not w:
        return ""
    if w == a:
        return b
    if w == b:
        return a
    return ""


def all_matches_for_scoring(data: dict, actual: bool = False) -> Dict[str, dict]:
    group_scores = data.get("group_scores", {})
    ko_key = "knockout_results" if actual else "knockout_predictions"
    bracket = compute_bracket(group_scores, data.get("third_slot_overrides", {}), data.get(ko_key, {}))
    out = {}
    for match in GROUP_MATCHES:
        key = str(match["match_no"])
        score = normalise_score_obj(group_scores.get(key))
        out[key] = {
            "match_no": match["match_no"],
            "phase": "Gruppespill",
            "team_a": match["team_a"],
            "team_b": match["team_b"],
            "goals_a": score["goals_a"],
            "goals_b": score["goals_b"],
            "winner": winner_from_score(match["team_a"], match["team_b"], score["goals_a"], score["goals_b"], score.get("winner", "")),
        }
    for match_no, m in bracket.items():
        out[str(match_no)] = m
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

    # Samme kamp, samme side.
    if pa == aa and pb == ab:
        pass
    # Samme kamp, motsatt side. Snu tipsmålene.
    elif pa == ab and pb == aa:
        pga, pgb = pgb, pga
    else:
        return 0

    if pga == aga and pgb == agb:
        return POINTS_EXACT_SCORE
    if get_outcome(pga, pgb) == get_outcome(aga, agb):
        return POINTS_OUTCOME
    return 0


def score_prediction(prediction: dict, actual_results: dict) -> dict:
    pred_matches = all_matches_for_scoring(prediction, actual=False)
    actual_matches = all_matches_for_scoring(actual_results, actual=True)
    rows = []
    total = 0
    for match_no in range(1, 105):
        key = str(match_no)
        pts = score_one_match(pred_matches.get(key, {}), actual_matches.get(key, {}))
        total += pts
        rows.append({
            "Kamp": match_no,
            "Fase": actual_matches.get(key, {}).get("phase", pred_matches.get(key, {}).get("phase", "")),
            "Poeng": pts,
            "Pred lag": f"{pred_matches.get(key, {}).get('team_a','')} - {pred_matches.get(key, {}).get('team_b','')}",
            "Pred resultat": format_score(pred_matches.get(key, {})),
            "Fasit lag": f"{actual_matches.get(key, {}).get('team_a','')} - {actual_matches.get(key, {}).get('team_b','')}",
            "Fasit resultat": format_score(actual_matches.get(key, {})),
        })
    champion_bonus = POINTS_CHAMPION if prediction.get("champion") and prediction.get("champion") == actual_results.get("champion") else 0
    total += champion_bonus
    return {"participant": prediction.get("participant", "Ukjent"), "match_points": total - champion_bonus, "champion_bonus": champion_bonus, "total": total, "details": rows}


def format_score(m: dict) -> str:
    if not m or m.get("goals_a") is None or m.get("goals_b") is None:
        return ""
    return f"{m.get('goals_a')} - {m.get('goals_b')}"


def load_json_bytes(uploaded_file) -> dict:
    return json.loads(uploaded_file.getvalue().decode("utf-8"))


def download_json(data: dict) -> str:
    data = dict(data)
    data["updated_at"] = now_iso()
    return json.dumps(data, ensure_ascii=False, indent=2)

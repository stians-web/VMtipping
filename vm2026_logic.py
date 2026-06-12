
from __future__ import annotations
import json, random, math
from datetime import datetime
from typing import Dict, List
import pandas as pd

SCHEMA_VERSION = "2026-06-12-v7-1-complete"
POINTS_EXACT_SCORE = 3
POINTS_OUTCOME = 1
POINTS_CHAMPION = 5
FINISHED_STATUS_CODES = {"FT", "AET", "PEN"}

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
TEAM_STRENGTH = {"Spain":.175,"France":.169,"England":.128,"Portugal":.098,"Brazil":.098,"Argentina":.096,"Germany":.064,"Netherlands":.047,"Norway":.030,"Belgium":.025,"Colombia":.024,"Japan":.020,"Uruguay":.015,"Morocco":.015,"USA":.015,"Switzerland":.012,"Türkiye":.012,"Mexico":.012,"Croatia":.012,"Senegal":.010,"Ecuador":.010,"Sweden":.008,"Canada":.007,"Paraguay":.007,"Austria":.007,"Scotland":.004,"Bosnia and Herzegovina":.004,"Czechia":.003,"Egypt":.003,"Côte d'Ivoire":.003,"Algeria":.0025,"Ghana":.0025,"Australia":.002,"Korea Republic":.002,"South Africa":.0015,"Qatar":.0015,"IR Iran":.0015,"Tunisia":.0015,"Congo DR":.0012,"Uzbekistan":.0012,"Panama":.0012,"Iraq":.0012,"Saudi Arabia":.0012,"New Zealand":.0012,"Jordan":.0012,"Haiti":.0012,"Curaçao":.001,"Cabo Verde":.001}
TEAM_ALIASES = {"South Korea":"Korea Republic","Czech Republic":"Czechia","Turkey":"Türkiye","Turkiye":"Türkiye","Ivory Coast":"Côte d'Ivoire","Cote d'Ivoire":"Côte d'Ivoire","DR Congo":"Congo DR","Cape Verde":"Cabo Verde","Iran":"IR Iran","United States":"USA","U.S.A.":"USA","Bosnia & Herzegovina":"Bosnia and Herzegovina"}

def now_iso(): return datetime.now().isoformat(timespec="seconds")
def canonical_team(name): return TEAM_ALIASES.get((name or "").strip(), (name or "").strip())
def build_group_matches():
    out=[]; n=1
    for g, teams in GROUPS.items():
        for a,b in PAIRINGS_IDX:
            out.append({"match_no":n,"phase":"Gruppespill","group":g,"team_a":teams[a],"team_b":teams[b]}); n+=1
    return out
GROUP_MATCHES = build_group_matches()

def new_prediction(participant=""):
    return {"schema_version":SCHEMA_VERSION,"type":"participant_prediction","participant":participant,"created_at":now_iso(),"updated_at":now_iso(),"group_scores":{},"third_slot_overrides":{},"knockout_predictions":{},"champion":""}
def new_actual_results():
    return {"schema_version":SCHEMA_VERSION,"type":"actual_results","updated_at":now_iso(),"group_scores":{},"third_slot_overrides":{},"knockout_results":{},"champion":"","api_last_updated":""}
def normalize_score(obj):
    obj=obj or {}
    return {"team_a":obj.get("team_a",""),"team_b":obj.get("team_b",""),"goals_a":obj.get("goals_a",obj.get("home")),"goals_b":obj.get("goals_b",obj.get("away")),"winner":obj.get("winner",""),"played":bool(obj.get("played",False)),"date":obj.get("date",""),"status":obj.get("status",""),"api_fixture_id":obj.get("api_fixture_id")}
def get_outcome(a,b): return "H" if a>b else "B" if b>a else "U"
def winner_from_score(a,b,ga,gb,manual=""):
    if ga is None or gb is None: return ""
    ga,gb=int(ga),int(gb)
    if ga>gb: return a
    if gb>ga: return b
    return manual if manual in [a,b] else ""
def strength(team): return TEAM_STRENGTH.get(team,.001)
def poisson(lam,rng):
    lam=max(.05,min(lam,4.5)); L=math.exp(-lam); k=0; p=1.0
    while p>L: k+=1; p*=rng.random()
    return k-1
def random_score(a,b,rng,knockout=False):
    diff=math.log((strength(a)+.002)/(strength(b)+.002)); base=1.08 if knockout else 1.18
    ga=poisson(max(.25,min(3.2,base+.32*diff)),rng); gb=poisson(max(.25,min(3.2,base-.32*diff)),rng)
    w=winner_from_score(a,b,ga,gb,"")
    if knockout and ga==gb:
        pa=strength(a)/(strength(a)+strength(b)+1e-9); w=a if rng.random()<pa else b
    return {"team_a":a,"team_b":b,"goals_a":int(ga),"goals_b":int(gb),"winner":w,"played":False}

def group_table(g,scores):
    rows=[{"Lag":t,"Seed":i,"S":0,"V":0,"U":0,"T":0,"MF":0,"MM":0,"MS":0,"P":0} for i,t in enumerate(GROUPS[g],1)]
    tab=pd.DataFrame(rows).set_index("Lag")
    for m in [x for x in GROUP_MATCHES if x["group"]==g]:
        s=normalize_score(scores.get(str(m["match_no"])))
        if s["goals_a"] is None or s["goals_b"] is None: continue
        a,b,ga,gb=m["team_a"],m["team_b"],int(s["goals_a"]),int(s["goals_b"])
        tab.loc[a,["S","MF","MM"]]+=[1,ga,gb]; tab.loc[b,["S","MF","MM"]]+=[1,gb,ga]
        if ga>gb: tab.loc[a,["V","P"]]+=[1,3]; tab.loc[b,"T"]+=1
        elif gb>ga: tab.loc[b,["V","P"]]+=[1,3]; tab.loc[a,"T"]+=1
        else: tab.loc[a,["U","P"]]+=[1,1]; tab.loc[b,["U","P"]]+=[1,1]
    tab["MS"]=tab["MF"]-tab["MM"]
    tab=tab.reset_index().sort_values(["P","MS","MF","Seed"],ascending=[False,False,False,True]).reset_index(drop=True)
    tab.insert(0,"Plass",range(1,len(tab)+1)); return tab

def qualifiers(group_scores):
    tables={g:group_table(g,group_scores) for g in GROUPS}; winners={}; runners={}; thirds=[]
    for g,t in tables.items():
        winners[g]=t.iloc[0]["Lag"]; runners[g]=t.iloc[1]["Lag"]; th=t.iloc[2]
        thirds.append({"group":g,"team":th["Lag"],"P":int(th["P"]),"MS":int(th["MS"]),"MF":int(th["MF"]),"Seed":int(th["Seed"])})
    third=pd.DataFrame(thirds).sort_values(["P","MS","MF","Seed"],ascending=[False,False,False,True]).reset_index(drop=True)
    return {"tables":tables,"winners":winners,"runners_up":runners,"thirds":third,"advancing_thirds":third.head(8).copy()}
def slot_allowed_map():
    out={}
    for _,a,b in ROUND_OF_32:
        for seed in (a,b):
            if seed.startswith("3"): out[seed]=seed[1:].split("/")
    return out
def find_third_slot_assignment(adv,allowed):
    slots=sorted(list(allowed.keys()),key=lambda s:len([g for g in allowed[s] if g in adv])); ass={}; used=set()
    def bt(i):
        if i==len(slots): return True
        slot=slots[i]
        for g in [x for x in allowed[slot] if x in adv and x not in used]:
            ass[slot]=g; used.add(g)
            if bt(i+1): return True
            used.remove(g); ass.pop(slot,None)
        return False
    bt(0); return {s:ass.get(s,"") for s in allowed}
def resolve_seed(seed,q,over):
    if seed.startswith("1") and len(seed)==2: return q["winners"].get(seed[1],"")
    if seed.startswith("2") and len(seed)==2: return q["runners_up"].get(seed[1],"")
    if seed.startswith("3"):
        adv=q["advancing_thirds"]["group"].tolist(); group=over.get(seed) or find_third_slot_assignment(adv,slot_allowed_map()).get(seed,"")
        row=q["advancing_thirds"].loc[q["advancing_thirds"]["group"]==group]
        return "" if row.empty else row.iloc[0]["team"]
    return seed
def loser_of(m):
    a,b,w=m.get("team_a",""),m.get("team_b",""),m.get("winner",""); return b if w==a else a if w==b else ""
def compute_bracket(group_scores,over,ko):
    q=qualifiers(group_scores); br={}
    for no,sa,sb in ROUND_OF_32:
        a,b=resolve_seed(sa,q,over),resolve_seed(sb,q,over); s=normalize_score(ko.get(str(no)))
        br[no]={"match_no":no,"phase":"16-delsfinaler","seed_a":sa,"seed_b":sb,"team_a":a,"team_b":b,"goals_a":s["goals_a"],"goals_b":s["goals_b"],"winner":winner_from_score(a,b,s["goals_a"],s["goals_b"],s["winner"]),"played":s["played"],"date":s["date"],"status":s["status"]}
    for phase,matches in NEXT_ROUNDS.items():
        for no,pa,pb in matches:
            a,b=(loser_of(br.get(pa,{})),loser_of(br.get(pb,{}))) if phase=="Bronsefinale" else (br.get(pa,{}).get("winner",""),br.get(pb,{}).get("winner",""))
            s=normalize_score(ko.get(str(no)))
            br[no]={"match_no":no,"phase":phase,"seed_a":("T" if phase=="Bronsefinale" else "V")+str(pa),"seed_b":("T" if phase=="Bronsefinale" else "V")+str(pb),"team_a":a,"team_b":b,"goals_a":s["goals_a"],"goals_b":s["goals_b"],"winner":winner_from_score(a,b,s["goals_a"],s["goals_b"],s["winner"]),"played":s["played"],"date":s["date"],"status":s["status"]}
    return br
def fill_try_luck(data,knockout_key="knockout_predictions",seed=None):
    rng=random.Random(seed if seed is not None else random.SystemRandom().randint(1,10**12)); participant=data.get("participant",""); kind=data.get("type","participant_prediction")
    data.clear(); data.update(new_actual_results() if knockout_key=="knockout_results" else new_prediction(participant)); data["type"]=kind
    if participant: data["participant"]=participant
    for m in GROUP_MATCHES: data["group_scores"][str(m["match_no"])]=random_score(m["team_a"],m["team_b"],rng,False)
    for phase in PHASE_ORDER:
        br=compute_bracket(data["group_scores"],data["third_slot_overrides"],data[knockout_key])
        for no,m in sorted([(n,x) for n,x in br.items() if x["phase"]==phase]):
            if m["team_a"] and m["team_b"]: data[knockout_key][str(no)]=random_score(m["team_a"],m["team_b"],rng,True)
    data["champion"]=compute_bracket(data["group_scores"],data["third_slot_overrides"],data[knockout_key]).get(104,{}).get("winner",""); return data

def all_matches_for_scoring(data,actual=False):
    ko_key="knockout_results" if actual else "knockout_predictions"; out={}; br=compute_bracket(data.get("group_scores",{}),data.get("third_slot_overrides",{}),data.get(ko_key,{}))
    for m in GROUP_MATCHES:
        key=str(m["match_no"]); s=normalize_score(data.get("group_scores",{}).get(key))
        out[key]={"match_no":m["match_no"],"phase":"Gruppespill","team_a":m["team_a"],"team_b":m["team_b"],"goals_a":s["goals_a"],"goals_b":s["goals_b"],"winner":winner_from_score(m["team_a"],m["team_b"],s["goals_a"],s["goals_b"],s["winner"]),"played":s["played"],"date":s["date"],"status":s["status"]}
    for no,m in br.items(): out[str(no)]=m
    return out
def score_one_match(pred,act):
    if not act or not act.get("played", False): return 0
    if not pred or pred.get("goals_a") is None or pred.get("goals_b") is None or act.get("goals_a") is None or act.get("goals_b") is None: return 0
    pa,pb,aa,ab=pred.get("team_a",""),pred.get("team_b",""),act.get("team_a",""),act.get("team_b",""); pga,pgb,aga,agb=int(pred["goals_a"]),int(pred["goals_b"]),int(act["goals_a"]),int(act["goals_b"])
    if pa==aa and pb==ab: pass
    elif pa==ab and pb==aa: pga,pgb=pgb,pga
    else: return 0
    return POINTS_EXACT_SCORE if (pga,pgb)==(aga,agb) else POINTS_OUTCOME if get_outcome(pga,pgb)==get_outcome(aga,agb) else 0
def format_score(m): return "" if not m or m.get("goals_a") is None or m.get("goals_b") is None else f"{m.get('goals_a')} - {m.get('goals_b')}"
def score_prediction(prediction,actual_results):
    pm,am=all_matches_for_scoring(prediction,False),all_matches_for_scoring(actual_results,True); rows=[]; total=0; corrected=0
    for no in range(1,105):
        key=str(no); act=am.get(key,{}); pts=score_one_match(pm.get(key,{}),act); total+=pts; corrected += 1 if act.get("played",False) else 0
        rows.append({"Kamp":no,"Fase":act.get("phase",""),"Spilt":"Ja" if act.get("played",False) else "Nei","Poeng":pts,"Pred lag":f"{pm.get(key,{}).get('team_a','')} - {pm.get(key,{}).get('team_b','')}","Pred resultat":format_score(pm.get(key,{})),"Fasit lag":f"{act.get('team_a','')} - {act.get('team_b','')}","Fasit resultat":format_score(act),"Status":act.get("status","")})
    bonus=POINTS_CHAMPION if actual_results.get("champion") and prediction.get("champion")==actual_results.get("champion") else 0
    return {"participant":prediction.get("participant","Ukjent"),"match_points":total,"champion_bonus":bonus,"total":total+bonus,"corrected_matches":corrected,"details":rows}
def load_json_bytes(uploaded_file): return json.loads(uploaded_file.getvalue().decode("utf-8"))
def download_json(data): data=dict(data); data["updated_at"]=now_iso(); return json.dumps(data,ensure_ascii=False,indent=2)
def apply_api_fixtures(actual, fixtures):
    updated=0; skipped=0; all_app_matches={}
    for m in GROUP_MATCHES: all_app_matches[(canonical_team(m["team_a"]), canonical_team(m["team_b"]))]=(str(m["match_no"]),"group_scores")
    ko=compute_bracket(actual.get("group_scores",{}), actual.get("third_slot_overrides",{}), actual.get("knockout_results",{}))
    for no,m in ko.items():
        if m.get("team_a") and m.get("team_b"): all_app_matches[(canonical_team(m["team_a"]), canonical_team(m["team_b"]))]=(str(no),"knockout_results")
    for fx in fixtures:
        try:
            f=fx.get("fixture",{}); teams=fx.get("teams",{}); goals=fx.get("goals",{})
            home=canonical_team(teams.get("home",{}).get("name","")); away=canonical_team(teams.get("away",{}).get("name",""))
            key=(home,away); rev=(away,home); match=all_app_matches.get(key) or all_app_matches.get(rev)
            if not match: skipped+=1; continue
            match_no,bucket=match; swapped = key not in all_app_matches and rev in all_app_matches
            status=f.get("status",{}).get("short",""); played=status in FINISHED_STATUS_CODES
            gh,ga=goals.get("home"),goals.get("away")
            if swapped: gh,ga=ga,gh; home,away=away,home
            obj={"team_a":home,"team_b":away,"goals_a":gh if played else None,"goals_b":ga if played else None,"played":played,"status":status,"date":f.get("date",""),"api_fixture_id":f.get("id"),"winner":""}
            if played: obj["winner"]=winner_from_score(home,away,gh,ga,"")
            actual.setdefault(bucket,{})[match_no]=obj; updated+=1
        except Exception: skipped+=1
    actual["api_last_updated"]=now_iso(); return {"updated":updated,"skipped":skipped}

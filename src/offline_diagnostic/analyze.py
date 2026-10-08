"""Rule-based trajectory diagnostic: explicit input paths; no model/environment calls."""
from pathlib import Path
import json,csv,re,math,statistics as st,hashlib,collections
import argparse
_cli=argparse.ArgumentParser(description=__doc__)
_cli.add_argument("--input-dir",type=Path,required=True,help="Saved full evaluation directory; raw traces remain external.")
_cli.add_argument("--output-dir",type=Path,required=True)
_cli.add_argument("--inherit-memory",type=Path,required=True)
_cli.add_argument("--reset-memory",type=Path,required=True)
_args=_cli.parse_args()
SRC=_args.input_dir.resolve()
ROOT=SRC
OUT=_args.output_dir.resolve()
OUT.mkdir(parents=True,exist_ok=True)
ARMS=("inherit","reset")
def load(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(l) for l in Path(p).read_text().splitlines()]
def dump(name,x):(OUT/name).write_text(json.dumps(x,indent=2,ensure_ascii=False)+"\n")
def jsonl(name,x):
    with (OUT/name).open("w") as f:
        for r in x:f.write(json.dumps(r,ensure_ascii=False)+"\n")
def tsv(name,x):
    keys=list(dict.fromkeys(k for r in x for k in r))
    with (OUT/name).open("w") as f:
        w=csv.DictWriter(f,fieldnames=keys,delimiter="\t");w.writeheader()
        for r in x:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else "NA" if v is None else v for k,v in r.items()})
def norm(s):return " ".join(str(s).lower().split())
def tokenize(s):
    s=norm(s).replace("women's","women").replace("men's","men").replace("womens","women").replace("mens","men")
    return set(re.findall(r"\w+",s))
def jac(a,b):return len(a&b)/len(a|b) if a|b else 1.0
def parsed(text):
    m=re.search(r"Action:\s*(.*?)\s*$",text,re.I|re.S);a=m.group(1).strip() if m else text.strip()
    p=re.fullmatch(r"(search|click)\[(.*)\]",a,re.I|re.S)
    return (p.group(1).lower(),p.group(2).strip(),a) if p else ("other",a,a)
def parts(s):return [t.strip() for t in s.split("[SEP]")]
def pool(s):return set(re.findall(r"\bB[A-Z0-9]{9}\b",s))
def page(s):
    p=parts(s)
    if "Purchased" in p:return "PURCHASE"
    if any(t.startswith("Price:") for t in p) and "Buy Now" in p:return "PRODUCT_MAIN"
    if any(re.search(r"Page \d+ \(Total results:",t) for t in p):return "SEARCH_RESULTS"
    if "< Prev" in p and "Back to Search" in p:return "PRODUCT_DETAIL"
    if "Search" in p:return "SEARCH_HOME"
    return "UNKNOWN"
LABELS={"color","size","fit type","item shape","style","pattern","flavor name","scent","material","item package quantity","number of items","configuration","package type","finish type","shape","flavor","style name","size name","color name"}
label_re="|".join(re.escape(s) for s in sorted(LABELS,key=len,reverse=True))
def requirements(s):
    text=s.split("Instruction: [SEP]",1)[-1].split("[SEP] Search",1)[0].strip()
    rx=r"\b("+label_re+r"):\s*(.*?)(?=,\s*and (?:"+label_re+r"):|,\s*and price lower than|$)"
    return {norm(m.group(1)):norm(m.group(2)) for m in re.finditer(rx,text,re.I)}
def product_data(s):
    p=parts(s);i=next((i for i,t in enumerate(p) if t.startswith("Price:")),None)
    if i is None:return None
    groups={};key=None;start=p.index("< Prev")+1 if "< Prev" in p else 0
    for val in p[start:i-1]:
        if norm(val) in LABELS:key=norm(val);groups[key]=[]
        elif key:groups[key].append(val)
    prices=[float(v) for v in re.findall(r"\$([0-9]+(?:\.[0-9]+)?)",p[i])]
    return {"title":p[i-1],"groups":groups,"price_min":min(prices) if prices else None,"price_max":max(prices) if prices else None}
CLASS_PATTERNS={
"computer armoires":r"\b(armoire|computer cabinet|computer workstation)\b",
"dried fruits & raisins":r"\b(raisin|raisins|dried fruit|dried apricot|dried cherry|dried cherries|dried cranberry|dried cranberries)\b",
"home office furniture sets":r"\b(furniture|table|desk|chair|stool)\b",
"men's dress shirts":r"\b(shirt|shirts)\b","men's henleys":r"\bhenley\b",
"men's loafers & slip-ons":r"\b(loafer|loafers|slip.on|moccasin|moccasins)\b",
"men's shirts":r"\b(shirt|shirts|t.shirt|t.shirts)\b","men's shorts":r"\bshorts\b",
"men's sleep & lounge":r"\b(pajama|pajamas|sleepwear|loungewear|pjs)\b",
"men's sweaters":r"\b(sweater|sweaters|pullover|pullovers)\b",
"men's t-shirts":r"\b(t.shirt|t.shirts|tee|tees)\b",
"men's t-shirts & tanks":r"\b(t.shirt|t.shirts|tee|tees|tank|tanks)\b",
"men's tuxedo shirts":r"\b(tuxedo|dress shirt)\b","scrubs & body treatments":r"\b(scrub|scrubs|body treatment|exfoliat)\b",
"sofa tables":r"\b(table|tables|console)\b","throw blankets":r"\b(blanket|blankets|throw)\b",
"wall art":r"\b(wall art|canvas|poster|painting|print|artwork)\b",
"window coverings":r"\b(curtain|curtains|drape|drapes|blind|blinds|window shade)\b",
"women's activewear":r"\b(shirt|shirts|activewear|sport|sports|running|athletic|workout)\b",
"women's jumpsuits, rompers & overalls":r"\b(jumpsuit|jumpsuits|romper|rompers|overall|overalls|onesie|onesies)\b",
"women's oxfords":r"\b(oxford|oxfords)\b","women's pants":r"\b(pants|trousers|jeans|leggings)\b",
"women's pumps":r"\b(pump|pumps|heel|heels)\b","women's shorts":r"\bshorts\b",
"women's tops, tees & blouses":r"\b(top|tops|tee|tees|t.shirt|t.shirts|blouse|blouses|sweatshirt|sweatshirts)\b"}
def class_evidence(cat,title):
    t=norm(title);w=bool(re.search(r"\bwomen(?:s|'s)?\b",t));m=bool(re.search(r"\bmen(?:s|'s)?\b",t))
    if (cat.startswith("women") and m and not w) or (cat.startswith("men") and w and not m):return "EXPLICIT_GENDER_MISMATCH"
    return "CLASS_COMPATIBLE" if re.search(CLASS_PATTERNS[cat],t,re.I) else "UNKNOWN"
def purchase(s):
    p=parts(s)
    if "Purchased" not in p:return None
    i=p.index("Purchased");j=p.index("options",i)
    opts=json.loads(p[j+1]) if p[j+1].startswith("{") else {}
    return {"asin":p[i+2],"options":{norm(k):norm(v) for k,v in opts.items()}}
DOUBT=re.compile(r"(?:cannot|can't|couldn't|not|no|unclear|uncertain|doesn't|does not|lack).{0,100}(?:confirm|reflect|appl|select|visib)|(?:select|option|variant).{0,90}(?:unclear|not confirm|not reflect|not appl|isn't|not visib)",re.I)
def doubt(t):return bool(DOUBT.search(t) and re.search(r"select|option|variant|appl|reflect",t,re.I))
M=load(SRC/"manifest.json");original_pairs=rows(SRC/"paired_results.jsonl")
assert len(original_pairs)==50 and len(rows(SRC/"execution_order.jsonl"))==100
expected_order=[(p,a) for p in range(1,51) for a in (ARMS if p%2 else tuple(reversed(ARMS)))]
assert [(r["position"],r["arm"]) for r in rows(SRC/"execution_order.jsonl")]==expected_order
proven={}
for pair in original_pairs:
    for arm in ARMS:
        for s in rows(SRC/"episodes"/f'{pair["position"]:02d}'/arm/"action_audit.jsonl"):
            if s["done"] and s["reward"]==1:proven[pair["idx"]]=purchase(s["state"])["asin"]
episodes=[];all_steps=[];option_events=[];loop_rows=[];purchase_events=[];visits_out=[]

for pair in original_pairs:
    pos=pair["position"];idx=pair["idx"];cat=M["tasks"][pos-1]["query_cat"]
    for arm in ARMS:
        d=SRC/"episodes"/f"{pos:02d}"/arm
        c=load(d/"completion.json");raw=rows(d/"action_audit.jsonl")
        conv=load(next((d/"conversations").glob("*.json")))["conversation"]
        responses=rows(d/"response_audit.jsonl");prompts=rows(d/"prompt_audit.jsonl")
        assert len(raw)==len(responses)==len(prompts)==c["model_calls"]
        assert all(r["initial_prompt_sha256"]==M["preflight"]["initial_prompt_hashes"][arm] for r in prompts)
        assert all(r["memory_sha256"]==M["preflight"]["memory_hashes"][arm] for r in prompts)
        for a,r in zip(raw,responses):assert a["action_response"]==r["content"]
        req=requirements(c["task_description"])
        assert req,"Task option parsing failed "+str(idx)
        limit=re.search(r"price lower than ([0-9.]+)",c["task_description"])
        budget=float(limit.group(1)) if limit else None
        before=conv[2]["content"];current=None;last=None;visit=None;steps=[];vlist=[];infos={}
        count=collections.Counter();seen_actions=set();opened=[];opts=[];buys=[];exit_steps=[];progress=set()
        for s in raw:
            n=s["round"];kind,value,act=parsed(s["action_response"]);bn=page(before);an=page(s["state"])
            thought=s["action_response"].split("Action:",1)[0]
            row={"task_id":c["task_id"],"stream_position":pos,"arm":arm,"step":n,"action":act,"action_kind":kind,
                 "value":value,"thought":thought,"observation_before":before,"observation_after":s["state"],
                 "page_before":bn,"page_after":an,"text_changed":before!=s["state"],"reward":s["reward"],"done":s["done"],
                 "asin_before":current,"option_group":None,"option_available":None,"selection_doubt":doubt(thought),
                 "progress":False}
            canon=norm(act);row["repeated_identical_action"]=canon in seen_actions
            count["repeated_identical_actions"]+=canon in seen_actions;seen_actions.add(canon)
            count["unchanged_action_events"]+=before==s["state"]
            if kind=="search":count["search_actions"]+=1
            if kind=="click" and value in ("Description","Features","Reviews"):count["verification_actions"]+=1
            if kind=="click" and re.fullmatch(r"B[A-Z0-9]{9}",value):
                count["product_open_attempts"]+=1
                pdata=product_data(s["state"])
                if an=="PRODUCT_MAIN" and pdata:
                    count["product_page_opens"]+=1
                    count["product_revisits"]+=value in opened
                    row["product_revisit"]=value in opened;row["opened_asin"]=value
                    fresh=value not in opened;opened.append(value);current=value;last=value
                    pdata["class_evidence"]=class_evidence(cat,pdata["title"])
                    pdata["requested_values_available"]={k:v in [norm(x) for x in pdata["groups"].get(k,[])] for k,v in req.items()}
                    pdata["all_requested_values_available"]=all(pdata["requested_values_available"].values())
                    pdata["budget_not_explicitly_violated"]=budget is None or pdata["price_min"] is None or pdata["price_min"]<budget
                    pdata["entire_price_range_below_budget"]=budget is None or (pdata["price_max"] is not None and pdata["price_max"]<budget)
                    pdata["proven_by_successful_paired_purchase"]=proven.get(idx)==value
                    pdata["candidate_eligible"]=pdata["class_evidence"]=="CLASS_COMPATIBLE" and pdata["all_requested_values_available"] and pdata["budget_not_explicitly_violated"]
                    infos[value]=pdata
                    visit={"task_id":c["task_id"],"arm":arm,"asin":value,"open_step":n,"selection_intents":{},"detail_tabs_seen":[],"leave_step":None}
                    vlist.append(visit);row["progress"]=fresh
                else:count["failed_product_open_attempts"]+=1
            if current and kind=="click" and value not in ("Description","Features","Reviews","Buy Now","Back to Search","< Prev","Next >"):
                groups=product_data(before)["groups"] if bn=="PRODUCT_MAIN" and product_data(before) else infos.get(current,{}).get("groups",{})
                matching=[k for k,vals in groups.items() if norm(value) in [norm(x) for x in vals]]
                if len(matching)==1:
                    group=matching[0];available=bn=="PRODUCT_MAIN" and norm(value) in [norm(x) for x in groups[group]]
                    row["option_group"]=group;row["option_available"]=available;count["option_clicks"]+=1
                    ev={"task_id":c["task_id"],"stream_position":pos,"arm":arm,"step":n,"action":act,"asin":current,"option_group":group,
                        "option_value":norm(value),"required_value_match":req.get(group)==norm(value),"control_visible":available,
                        "observation_before":before,"observation_after":s["state"],"text_changed":before!=s["state"],
                        "episode_reward":c["reward"],"episode_success":c["success"],"terminal_purchase":c["terminated_purchase"]}
                    opts.append(ev)
                    if available and visit:
                        new=visit["selection_intents"].get(group)!=norm(value)
                        visit["selection_intents"][group]=norm(value)
                        if new and req.get(group)==norm(value):row["progress"]=True
                elif value.lower() in LABELS:
                    row["non_option_header_click"]=True;count["non_option_header_clicks"]+=1
            if current and kind=="click" and value in ("Description","Features","Reviews") and visit:
                if value not in visit["detail_tabs_seen"] and before!=s["state"]:row["progress"]=True
                visit["detail_tabs_seen"].append(value)
            if kind=="click" and value=="Buy Now":
                count["buy_now_actions"]+=1
                visible="Buy Now" in parts(before);count["unavailable_buy_attempts"]+=not visible
                pr=purchase(s["state"])
                ev={"task_id":c["task_id"],"stream_position":pos,"arm":arm,"step":n,"asin":current,
                    "control_visible":visible,"text_changed":before!=s["state"],"terminal":s["done"],"reward":s["reward"],
                    "observation_before":before,"observation_after":s["state"],"purchase_summary":pr}
                buys.append(ev);purchase_events.append(ev)
                if pr:last=pr["asin"]
            if kind=="click" and norm(value) not in [norm(x) for x in parts(before)] and before==s["state"]:
                count["unlisted_unchanged_clicks"]+=1;row["unlisted_unchanged_click"]=True
            if bn.startswith("PRODUCT") and an.startswith("SEARCH"):
                count["returns_product_to_search"]+=1
                leave={"step":n,"asin":current,"selection_intents":visit["selection_intents"].copy() if visit else {},
                       "issued_all_required":bool(visit and all(visit["selection_intents"].get(k)==v for k,v in req.items())),
                       "plausible":infos.get(current,{}).get("class_evidence")=="CLASS_COMPATIBLE"}
                exit_steps.append(leave)
                if visit:visit.update(leave_step=n,issued_all_required_before_leave=leave["issued_all_required"])
                current=None;visit=None
            if row["progress"]:progress.add(n)
            row["asin_after"]=current;steps.append(row);all_steps.append(row);before=s["state"]
        for ev in opts:
            later=[b for b in buys if b["step"]>ev["step"] and b["terminal"] and b["purchase_summary"] and b["purchase_summary"]["asin"]==ev["asin"]]
            confirmation=next((b for b in later if b["purchase_summary"]["options"].get(ev["option_group"])==ev["option_value"]),None)
            ev["later_purchase_confirmation_step"]=confirmation["step"] if confirmation else None
            ev["later_purchase_reward"]=confirmation["reward"] if confirmation else None
            ev["confirmation_matches_value"]=confirmation is not None
            visible_confirm=bool(re.search(r"\bselected\b",ev["observation_after"],re.I) and ev["option_value"] in norm(ev["observation_after"]))
            ev["visibility_status"]=("UNCHANGED_LATER_CONFIRMED" if confirmation else "UNCHANGED_UNCONFIRMED") if not ev["text_changed"] else ("VISIBLE_SELECTION_CONFIRMED" if visible_confirm else "TEXT_CHANGED_UNCONFIRMED")
            doubt_steps=[r["step"] for r in steps if r["step"]>ev["step"] and r["selection_doubt"] and r["asin_before"]==ev["asin"]]
            leave=next((x["step"] for x in exit_steps if x["step"]>ev["step"] and x["asin"]==ev["asin"]),None)
            ev["later_selection_doubt_steps"]=doubt_steps;ev["later_leave_step"]=leave
            ev["unchanged_doubt_then_leave_or_cap"]=not ev["text_changed"] and bool(doubt_steps) and (leave is not None or c["round_limit_reached"]) and not c["terminated_purchase"]
            ev["buy_followed_unchanged_option"]=not ev["text_changed"] and any(b["step"]>ev["step"] and b["asin"]==ev["asin"] for b in buys)
            option_events.append(ev)
        loops=[]
        for a,b in zip(steps,steps[1:]):
            kinds=[]
            if a["action_kind"]==b["action_kind"]=="search":
                qj=jac(tokenize(a["value"]),tokenize(b["value"]));pa=pool(a["observation_after"]);pb=pool(b["observation_after"])
                pj=jac(pa,pb) if pa and pb else None
                if pj is not None and ((qj>=.6 and pj>=.5) or pj>=.8):kinds.append("SEARCH_REFORMULATION_STAGNATION")
            else:qj=pj=None
            if norm(a["action"])==norm(b["action"]) and not b["text_changed"]:kinds.append("IDENTICAL_NO_TEXT_CHANGE")
            if kinds:loops.append({"kinds":kinds,"steps":[a["step"],b["step"]],"query_jaccard":qj,"result_pool_jaccard":pj})
        for v in vlist:
            if v.get("leave_step") and v["asin"] in opened[:opened.index(v["asin"])]:
                pass
            earlier=[x for x in vlist if x["asin"]==v["asin"] and x["open_step"]<v["open_step"]]
            if earlier:
                previous=earlier[-1]
                loops.append({"kinds":["PRODUCT_REOPEN"],"steps":list(range(previous["open_step"],v["open_step"]+1)),"asin":v["asin"]})
            if v.get("leave_step"):
                option_steps=[e["step"] for e in opts if e["asin"]==v["asin"] and v["open_step"]<e["step"]<v["leave_step"]]
                if option_steps:loops.append({"kinds":["PRODUCT_OPTION_SEARCH"],"steps":list(range(v["open_step"],v["leave_step"]+1)),"asin":v["asin"]})
        for e in opts:
            if e["unchanged_doubt_then_leave_or_cap"]:
                end=e["later_leave_step"] or len(steps)
                loops.append({"kinds":["OPTION_DOUBT_NO_BUY"],"steps":list(range(e["step"],end+1)),"asin":e["asin"]})
        loop_steps=set(x for l in loops for x in l["steps"])
        late=steps[-4:];late_search=sum(s["action_kind"]=="search" for s in late)
        late_verify=sum(s["option_group"] is not None or (s["action_kind"]=="click" and s["value"] in ("Features","Description","Reviews")) for s in late)
        search_stagnation_pairs=sum("SEARCH_REFORMULATION_STAGNATION" in l["kinds"] and max(l["steps"])>=len(steps)-3 for l in loops)
        late_search_loop=late_search>=3 and not any(s["progress"] for s in late) and search_stagnation_pairs>=2
        plausible=[a for a,p in infos.items() if p["class_evidence"]=="CLASS_COMPATIBLE"]
        eligible=[a for a,p in infos.items() if p["candidate_eligible"]]
        def score(a):
            p=infos[a];return (3 if p["proven_by_successful_paired_purchase"] else 2 if p["candidate_eligible"] else 1 if a in plausible else 0)
        best=max(infos,key=lambda a:(score(a),-next(v["open_step"] for v in vlist if v["asin"]==a))) if infos else None
        if best and score(best)==0:best=None
        first_best=next((v["open_step"] for v in vlist if v["asin"]==best),None)
        issued_all_visits=[v for v in vlist if all(v["selection_intents"].get(k)==x for k,x in req.items())]
        strong_correct_no_buy=not buys and any(v["asin"]==proven.get(idx) for v in issued_all_visits)
        plausible_allopts_no_buy=not buys and any(v["asin"] in eligible for v in issued_all_visits)
        strong_option_loop=any(e["unchanged_doubt_then_leave_or_cap"] and e["required_value_match"] and e["asin"] in plausible for e in opts)
        wrong_commit=any(b["asin"] in infos and infos[b["asin"]]["class_evidence"]=="EXPLICIT_GENDER_MISMATCH" for b in buys)
        if c["success"]:primary="SUCCESS"
        elif c["terminated_purchase"]:primary="WRONG_PRODUCT_COMMITMENT" if wrong_commit else "PREMATURE_BUY"
        elif strong_option_loop:primary="OPTION_VISIBILITY_LOOP"
        elif strong_correct_no_buy or plausible_allopts_no_buy:primary="CORRECT_PRODUCT_NO_BUY"
        elif late_search_loop:primary="SEARCH_LOOP"
        elif wrong_commit:primary="WRONG_PRODUCT_COMMITMENT"
        elif count["unavailable_buy_attempts"]:primary="OTHER_AMBIGUOUS"
        elif progress and c["round_limit_reached"]:primary="BUDGET_LIMIT_AFTER_PROGRESS"
        elif not plausible:primary="PRODUCT_NOT_FOUND"
        else:primary="OTHER_AMBIGUOUS"
        tags=[]
        if not plausible:tags.append("NO_CLASS_COMPATIBLE_PRODUCT_INSPECTED")
        if loops:tags.append("LOOP_HEURISTIC")
        if late_search_loop:tags.append("LATE_SEARCH_STAGNATION")
        if strong_option_loop:tags.append("UNCHANGED_OPTION_EXPLICIT_DOUBT")
        if count["unavailable_buy_attempts"]:tags.append("PURCHASE_CONTROL_MISMATCH")
        if c["round_limit_reached"]:tags.append("ROUND_CAP")
        if strong_correct_no_buy:tags.append("PAIRED_SUCCESS_PROVEN_PRODUCT_NO_BUY")
        if plausible_allopts_no_buy:tags.append("CLASS_COMPATIBLE_REQUIRED_OPTIONS_ISSUED_NO_BUY")
        if exit_steps:tags.append("PRODUCT_TO_SEARCH")
        if any(not e["text_changed"] for e in opts):tags.append("UNCHANGED_OPTION_TEXT")
        final_info=infos.get(current or last,{})
        purchase_path=page(before)=="PRODUCT_MAIN" and current in eligible and "Buy Now" in parts(before)
        selection=visit["selection_intents"] if visit else {}
        remaining_controls=sum(selection.get(k)!=v for k,v in req.items())+1 if purchase_path else None
        ep={"task_id":c["task_id"],"task_idx":idx,"stream_position":pos,"arm":arm,"execution_order":"/".join(ARMS if pos%2 else tuple(reversed(ARMS))),
            "arm_order_in_pair":(ARMS if pos%2 else tuple(reversed(ARMS))).index(arm)+1,
            "reward":c["reward"],"success":c["success"],"rounds":len(steps),"model_calls":c["model_calls"],"terminal_purchase":c["terminated_purchase"],
            "round_limit_hit":c["round_limit_reached"],"search_actions":count["search_actions"],"product_page_opens":count["product_page_opens"],
            "product_open_attempts":count["product_open_attempts"],"failed_product_open_attempts":count["failed_product_open_attempts"],
            "option_clicks":count["option_clicks"],"buy_now_actions":count["buy_now_actions"],"repeated_identical_actions":count["repeated_identical_actions"],
            "returns_product_to_search":count["returns_product_to_search"],"unique_products_opened":len(set(opened)),
            "final_product_asin":last,"current_product_asin":current,"final_product_class_match":final_info.get("class_evidence","NOT_INFERABLE"),
            "unchanged_option_incidence":any(not e["text_changed"] for e in opts),"unchanged_option_events":sum(not e["text_changed"] for e in opts),
            "buy_after_unchanged_option":any(e["buy_followed_unchanged_option"] for e in opts),
            "left_after_required_options":any(e["issued_all_required"] for e in exit_steps),
            "left_after_any_option":any(e["selection_intents"] for e in exit_steps),
            "product_revisited":count["product_revisits"]>0,"product_revisits":count["product_revisits"],
            "late_search_or_verification_dominated":late_search+late_verify>=3 and not c["terminated_purchase"],
            "verification_actions":count["verification_actions"],"unavailable_buy_attempts":count["unavailable_buy_attempts"],
            "non_option_header_clicks":count["non_option_header_clicks"],"unlisted_unchanged_clicks":count["unlisted_unchanged_clicks"],
            "loop_incidence":bool(loops),"loop_count":len(loops),"loop_rounds_union":len(loop_steps),"primary_failure_mode":primary,
            "secondary_tags":tags,"last_four_search_actions":late_search,"last_four_verification_actions":late_verify,
            "progress_steps":sorted(progress),"evidence_best_asin":best,"first_best_product_step":first_best,
            "rounds_after_first_best_product":len(steps)-first_best if first_best is not None else None,
            "plausible_products":plausible,"eligible_candidates":eligible,"required_options":req,"product_evidence":infos,
            "strong_correct_product_no_buy":strong_correct_no_buy,"plausible_options_no_buy":plausible_allopts_no_buy,
            "option_visibility_doubt_chain":strong_option_loop,"final_page":page(before),
            "ends_immediately_after_option":steps[-1]["option_group"] is not None,
            "ends_after_return_from_plausible":any(e["plausible"] for e in exit_steps) and page(before).startswith("SEARCH"),
            "plausible_purchase_controls_remaining":purchase_path,"minimum_unissued_controls_plus_buy":remaining_controls,
            "trace_directory":str(d.relative_to(ROOT))}
        episodes.append(ep);visits_out+=vlist
        loop_rows.append({"task_id":c["task_id"],"arm":arm,"loop_count":len(loops),"loop_rounds_union":len(loop_steps),
                          "loop_incidence":bool(loops),"loops":loops,"late_search_loop":late_search_loop})
assert len(episodes)==100 and sum(e["model_calls"] for e in episodes)==980
assert sum(e["success"] for e in episodes)==1 and sum(e["round_limit_hit"] for e in episodes)==96
assert sum(e["buy_now_actions"] for e in episodes)==15 and sum(e["terminal_purchase"] for e in episodes)==4
assert sum(not b["control_visible"] and not b["terminal"] and not b["text_changed"] for b in purchase_events)==11
assert {a:sum(e["unavailable_buy_attempts"] for e in episodes if e["arm"]==a) for a in ARMS}=={"inherit":7,"reset":4}
jsonl("episode_diagnostics.jsonl",episodes);tsv("episode_diagnostics.tsv",episodes)
jsonl("step_diagnostics.jsonl",all_steps);tsv("option_visibility_events.tsv",option_events);jsonl("option_visibility_events.jsonl",option_events)
tsv("purchase_visibility_events.tsv",purchase_events);tsv("loop_diagnostics.tsv",loop_rows);jsonl("product_visits.jsonl",visits_out)

taxonomy={
 "SUCCESS":{"definition":"Saved success=true; excluded from the failure denominator."},
 "PRODUCT_NOT_FOUND":{"definition":"No class-compatible product page actually opened and no higher-priority signature. Does not mean the catalog lacks a correct product."},
 "WRONG_PRODUCT_COMMITMENT":{"definition":"A purchase attempt occurs on a product with an explicit gender contradiction in the title; conservative, no title-subtype guesses."},
 "OPTION_VISIBILITY_LOOP":{"definition":"Class-compatible product; required-value option click; identical observation; a later selection-specific doubt while on that product; subsequent departure or cap, with no terminal purchase."},
 "SEARCH_LOOP":{"definition":"At least 3 Search actions in the last 4 rounds, no newly inspected ASIN/new required option/detail tab in those rounds, and at least 2 late stagnant-search transitions."},
 "CORRECT_PRODUCT_NO_BUY":{"definition":"No Buy Now attempt; all requested option-click intents issued within one visit on either the paired-success-proven ASIN or a class-compatible candidate exposing exact requested labels without an explicit price violation. The broad label includes plausible products; separate proof fields prevent equating plausibility with correctness."},
 "PREMATURE_BUY":{"definition":"A terminal partial/zero-reward purchase. Required-option clicks/attribute proof may be absent; this label describes incomplete purchase, not a proven causal reason for partial reward."},
 "BUDGET_LIMIT_AFTER_PROGRESS":{"definition":"Cap hit after an observed new product inspection, newly changed detail view or first required option-click intent; no more specific signature dominates."},
 "OTHER_AMBIGUOUS":{"definition":"Insufficient semantic evidence or a nonterminal attempt to use an absent purchase control; secondary tags state the observed issue."}}
precedence=["SUCCESS","terminal purchase: WRONG_PRODUCT_COMMITMENT if explicit gender contradiction else PREMATURE_BUY",
 "OPTION_VISIBILITY_LOOP","CORRECT_PRODUCT_NO_BUY","SEARCH_LOOP","WRONG_PRODUCT_COMMITMENT",
 "OTHER_AMBIGUOUS if unavailable Buy Now attempt","BUDGET_LIMIT_AFTER_PROGRESS","PRODUCT_NOT_FOUND","OTHER_AMBIGUOUS"]
dump("failure_taxonomy.json",{"version":1,"category_definitions":taxonomy,"precedence":precedence,
 "interpretation":"Mutually exclusive observable failure signatures; not causal allocations. Secondary tags overlap. Missing gold attributes stay unknown.",
 "failure_denominator":99,"class_patterns":CLASS_PATTERNS,"strong_correct_product_evidence":"Only successful paired purchase transfer (task 5590) proves a task/product association."})
definitions={
 "row_unit":"One completed episode; comparisons use one matched task pair, never 100 independent observations.",
 "task_id":"completion.json task_id; stream_position is 1-based released order; execution_order derived and checked against saved execution_order.jsonl.",
 "reward_success_rounds_model_calls":"Saved completion outcomes; rounds=len(action_audit), verified equal to response/prompt/usage counts.",
 "terminal_purchase":"Saved done=true purchase summary, distinct from an issued click[Buy Now].",
 "round_limit_hit":"Saved completion.round_limit_reached; success at round 10 is not cap-censored.",
 "search_actions":"Parsed search[...] responses, including nonprogressing attempts; no claim all attempts executed.",
 "product_page_opens":"ASIN click followed by actual PRODUCT_MAIN observation (Price token plus Buy Now); invalid/nonlisted ASIN attempts counted separately.",
 "option_clicks":"A click whose value uniquely belongs to an option group in the current main page or last known current product. control_visible marks actual current availability. Header clicks like click[color] are excluded.",
 "buy_now_actions":"All click[Buy Now] attempts. unavailable_buy_attempts counts attempts with Buy Now absent from exact SEP-delimited pre-action tokens.",
 "verification_actions":"Description, Features or Reviews click attempts; not proof verification succeeded.",
 "repeated_identical_actions":"Number of actions with lowercased/whitespace-collapsed strings already seen anywhere earlier. Repeated pagination with new observations is counted here but not automatically a loop.",
 "returns_product_to_search":"Realized PRODUCT_MAIN/DETAIL -> SEARCH_HOME/RESULTS transition, regardless of action label.",
 "unique_products_opened_product_revisits":"Unique successfully opened ASINs; each subsequent successful opening of an already opened ASIN is a revisit.",
 "final_product_asin":"Last successfully opened or purchased ASIN, even if episode ends searching. current_product_asin and final_page distinguish current location.",
 "final_product_class_match":"Regex title compatibility using manifest task query_cat and explicit gender contradictions. Unknown remains unknown; compatible does not mean all constraints satisfied.",
 "unchanged_option_events_incidence":"Exact observation string equality before/after identified option clicks, and whether any occurs.",
 "buy_after_unchanged_option":"A later purchase attempt on the same ASIN after an unchanged option event, not necessarily immediately next round.",
 "left_after_required_options":"At a realized product->search transition all required exact option values had been clicked in that visit; intent only unless purchase summary confirms application.",
 "left_after_any_option":"Realized departure after at least one visible option-value click intent in that visit.",
 "late_search_or_verification_dominated":"At least 3 of final 4 actions are Search/option/detail-tab clicks and there was no terminal purchase. Descriptive, not automatically a loop.",
 "loop_incidence_count_rounds_union":"Any heuristic loop; count of potentially overlapping loop events; union of their action-step indices counts rounds without double counting.",
 "search_loop_heuristic":"Consecutive Searches: query-token Jaccard>=0.6 and returned ASIN-set Jaccard>=0.5, or returned ASIN-set Jaccard>=0.8 regardless of query. ASIN pools must both be nonempty. Query/pool changes can still have hidden value; this is a proxy.",
 "other_loop_heuristics":"Consecutive identical action with unchanged text; reopening a previously opened ASIN (interval includes intervening actions); product->option->search; unchanged-option->selection-doubt->leave/cap. Pagination progressing to new text alone is not a loop.",
 "observable_progress":"First opening of a new ASIN, first changed view of a detail tab in a visit, or first required-value click intent in a visit. It does not establish full task correctness.",
 "evidence_best_product":"Among inspected ASINs: paired-success-proven > class-compatible with exact requested labels and no explicit price violation > class-compatible. Earliest first opening breaks ties. No compatible evidence yields NA.",
 "rounds_after_first_best_product":"Total action rounds minus first successful opening step of evidence-best inspected ASIN. NA when no evidentially plausible ASIN; paired comparisons disclose complete-pair denominator.",
 "strong_correct_product_no_buy":"No Buy Now attempt plus all required option clicks in a visit on the ASIN proven by the other arm's successful purchase. Does not prove every click was applied in the nonpurchase trace.",
 "plausible_options_no_buy":"No Buy Now attempt plus all requested exact option-click intents on class-compatible candidate exposing those labels and no explicit price-minimum contradiction. Additional attributes/variant price can remain unverified.",
 "plausible_purchase_controls_remaining":"At cap, PRODUCT_MAIN with visible Buy Now, class-compatible candidate and all requested values available, no explicit price-minimum contradiction. A mechanically available path, not a predicted success.",
 "minimum_unissued_controls_plus_buy":"On that page, number of required option values not yet clicked in this visit + 1 buy control. Not a simulated continuation.",
 "ends_immediately_after_option":"Last saved action was an identified option-value click; overlaps final_page.",
 "ends_after_return_from_plausible":"At least one class-compatible product was left and the episode ends on a search page; historical rather than immediate departure.",
 "option_confirmation":"Later terminal purchase of same ASIN lists same group/value. Confirms eventual value, not which repeated click applied it.",
 "selection_doubt":"Rule-based regex for negated/unclear confirmation/application/visibility plus selection/option/variant words in Thought. Used descriptively, never as causality.",
 "unchanged_doubt_chain":"Unchanged option event followed by selection doubt on same product and departure or cap, without terminal purchase.",
 "correctness_limit":"No external catalog, gold trajectories, new actions, server state, model calls or production source was inspected. Product-class labels are proxies; only task 5590 has successful paired product proof.",
 "hopelessness":"Saved traces cannot establish that remaining catalog search is impossible. Early failed terminal purchases are distinguished from unprovably hopeless capped episodes."}
dump("feature_definitions.json",definitions)
by={(e["task_idx"],e["arm"]):e for e in episodes}
compare_fields=["search_actions","option_clicks","buy_now_actions","product_page_opens","product_revisits","repeated_identical_actions",
 "unchanged_option_events","rounds_after_first_best_product","left_after_required_options","left_after_any_option",
 "loop_incidence","loop_count","loop_rounds_union","verification_actions","unavailable_buy_attempts","rounds"]
pairs=[]
for source in original_pairs:
    idx=source["idx"];i=by[idx,"inherit"];z=by[idx,"reset"]
    r={"task_id":i["task_id"],"stream_position":i["stream_position"],"inherit_primary":i["primary_failure_mode"],"reset_primary":z["primary_failure_mode"],
       "same_primary_mode":i["primary_failure_mode"]==z["primary_failure_mode"],"both_failed":not i["success"] and not z["success"]}
    for f in compare_fields:r.update({f+"_inherit":i[f],f+"_reset":z[f],f+"_delta_reset_minus_inherit":z[f]-i[f] if i[f] is not None and z[f] is not None else None})
    r["purchase_attempt_incidence_inherit"]=i["buy_now_actions"]>0;r["purchase_attempt_incidence_reset"]=z["buy_now_actions"]>0
    r["purchase_attempt_incidence_delta"]=int(z["buy_now_actions"]>0)-int(i["buy_now_actions"]>0)
    pairs.append(r)
tsv("paired_failure_modes.tsv",pairs);jsonl("paired_failure_modes.jsonl",pairs)
family=["search_actions","option_clicks","buy_now_actions","product_revisits","repeated_identical_actions","loop_incidence","unchanged_option_incidence","left_after_required_options"]
def exact_sign(positive,negative):
    n=positive+negative;k=min(positive,negative)
    return min(1.0,2*sum(math.comb(n,j) for j in range(k+1))/2**n) if n else 1.0
statistics={}
for f in compare_fields+["unchanged_option_incidence","purchase_attempt_incidence"]:
    valid=[(i[f],z[f]) if f!="purchase_attempt_incidence" else (i["buy_now_actions"]>0,z["buy_now_actions"]>0)
           for source in original_pairs for i,z in [(by[source["idx"],"inherit"],by[source["idx"],"reset"])]
           if f=="purchase_attempt_incidence" or (i[f] is not None and z[f] is not None)]
    ds=[float(z)-float(i) for i,z in valid];positive=sum(d>0 for d in ds);negative=sum(d<0 for d in ds)
    row={"complete_pairs":len(valid),"inherit_mean":st.mean(float(i) for i,z in valid) if valid else None,
         "inherit_median":st.median(float(i) for i,z in valid) if valid else None,
         "reset_mean":st.mean(float(z) for i,z in valid) if valid else None,"reset_median":st.median(float(z) for i,z in valid) if valid else None,
         "paired_mean_difference":st.mean(ds) if ds else None,"paired_median_difference":st.median(ds) if ds else None,
         "reset_greater_pairs":positive,"inherit_greater_pairs":negative,"equal_pairs":len(ds)-positive-negative}
    if f in family:row["exact_two_sided_sign_p"]=exact_sign(positive,negative)
    if f in ("loop_incidence","unchanged_option_incidence","left_after_required_options","left_after_any_option","purchase_attempt_incidence"):
        row["binary_table"]={"both_true":sum(bool(i) and bool(z) for i,z in valid),"inherit_only":sum(bool(i) and not bool(z) for i,z in valid),
                             "reset_only":sum(bool(z) and not bool(i) for i,z in valid),"both_false":sum(not bool(i) and not bool(z) for i,z in valid)}
    statistics[f]=row
ranked=sorted(family,key=lambda f:statistics[f]["exact_two_sided_sign_p"]);last_p=0
for j,f in enumerate(ranked):
    last_p=max(last_p,min(1.0,statistics[f]["exact_two_sided_sign_p"]*(len(ranked)-j)))
    statistics[f]["holm_adjusted_p"]=last_p
counts={a:dict(collections.Counter(e["primary_failure_mode"] for e in episodes if e["arm"]==a)) for a in ARMS}
failures={a:sum(not e["success"] for e in episodes if e["arm"]==a) for a in ARMS}
proportions={a:{k:{"count":v,"fraction_of_failures":v/failures[a]} for k,v in counts[a].items() if k!="SUCCESS"} for a in ARMS}
no_buy={a:{"paired_success_proven_count":sum(e["strong_correct_product_no_buy"] for e in episodes if e["arm"]==a),
 "paired_success_proven_task_ids":[e["task_id"] for e in episodes if e["arm"]==a and e["strong_correct_product_no_buy"]],
 "class_compatible_options_issued_count":sum(e["plausible_options_no_buy"] for e in episodes if e["arm"]==a),
 "class_compatible_options_issued_task_ids":[e["task_id"] for e in episodes if e["arm"]==a and e["plausible_options_no_buy"]],
 "all_end_at_cap":all(e["round_limit_hit"] for e in episodes if e["arm"]==a and (e["plausible_options_no_buy"] or e["strong_correct_product_no_buy"])),
 "visibility_ambiguity_preceded_count":sum(e["unchanged_option_incidence"] and (e["plausible_options_no_buy"] or e["strong_correct_product_no_buy"]) for e in episodes if e["arm"]==a)} for a in ARMS}
option_stats={a:{"events":sum(e["arm"]==a for e in option_events),"unchanged_events":sum(e["arm"]==a and not e["text_changed"] for e in option_events),
 "episodes_with_unchanged":sum(e["arm"]==a and e["unchanged_option_incidence"] for e in episodes),
 "visibility_status":dict(collections.Counter(e["visibility_status"] for e in option_events if e["arm"]==a)),
 "explicit_doubt_chain_episodes":sum(e["arm"]==a and e["option_visibility_doubt_chain"] for e in episodes),
 "non_option_header_clicks":sum(e["non_option_header_clicks"] for e in episodes if e["arm"]==a)} for a in ARMS}
cap={a:{"capped_episodes":sum(e["arm"]==a and e["round_limit_hit"] for e in episodes),
 "final_page":dict(collections.Counter(e["final_page"] for e in episodes if e["arm"]==a and e["round_limit_hit"])),
 "immediately_after_option":sum(e["arm"]==a and e["round_limit_hit"] and e["ends_immediately_after_option"] for e in episodes),
 "after_leaving_plausible_product":sum(e["arm"]==a and e["round_limit_hit"] and e["ends_after_return_from_plausible"] for e in episodes),
 "mechanically_plausible_purchase_path":sum(e["arm"]==a and e["round_limit_hit"] and e["plausible_purchase_controls_remaining"] for e in episodes),
 "never_inspected_class_compatible":sum(e["arm"]==a and e["round_limit_hit"] and not e["plausible_products"] for e in episodes)} for a in ARMS}
sensitivity=[]
for threshold in (.5,.6,.7,.8):
    flags={};roundsets={};lateflags={}
    for ep in episodes:
        ss=[s for s in all_steps if s["task_id"]==ep["task_id"] and s["arm"]==ep["arm"]]
        ls=[]
        for a,b in zip(ss,ss[1:]):
            if a["action_kind"]==b["action_kind"]=="search":
                pa=pool(a["observation_after"]);pb=pool(b["observation_after"])
                if pa and pb and ((jac(tokenize(a["value"]),tokenize(b["value"]))>=threshold and jac(pa,pb)>=.5) or jac(pa,pb)>=.8):ls.append([a["step"],b["step"]])
        flags[ep["task_id"],ep["arm"]]=bool(ls)
        lateflags[ep["task_id"],ep["arm"]]=ep["last_four_search_actions"]>=3 and not any(s["progress"] for s in ss[-4:]) and sum(max(x)>=len(ss)-3 for x in ls)>=2
    sensitivity.append({"query_jaccard_threshold":threshold,"search_stagnation_episode_count":{a:sum(v for (t,arm),v in flags.items() if arm==a) for a in ARMS},
                        "late_search_loop_count":{a:sum(v for (t,arm),v in lateflags.items() if arm==a) for a in ARMS}})
memory={a:[re.sub(r"^\d+\.\s*","",line) for line in (_args.inherit_memory if a=="inherit" else _args.reset_memory).read_text().splitlines()] for a in ARMS}
assert sorted(memory["inherit"])==sorted(memory["reset"]) and len(memory["inherit"])==36
rule_ranks=[]
for rank,text in enumerate(memory["inherit"],1):
    rr=memory["reset"].index(text)+1
    themes=[]
    if re.search(r"search|quer",text,re.I):themes.append("search_strategy")
    if re.search(r"verif|confirm|requirement|constraint",text,re.I):themes.append("constraint_verification")
    if re.search(r"option|variant|select",text,re.I):themes.append("option_verification")
    if re.search(r"buy|purchas|commit|terminal",text,re.I):themes.append("purchase_caution")
    rule_ranks.append({"inherit_rank":rank,"reset_rank":rr,"rank_delta_reset_minus_inherit":rr-rank,"themes":themes,"text":text})
tsv("memory_rule_rank_themes.tsv",rule_ranks)
out={
 "scope":"Exploratory offline diagnostics; no new calls/actions. Causes remain hypotheses; primary labels are auditable signatures.",
 "episodes":100,"matched_pairs":50,"original_success_result":load(SRC/"results_summary.json")["paired_outcomes"],
 "failure_counts":counts,"failure_denominators":failures,"failure_fractions":proportions,
 "same_primary_mode_all_pairs":sum(r["same_primary_mode"] for r in pairs),
 "different_primary_mode_all_pairs":sum(not r["same_primary_mode"] for r in pairs),
 "same_mode_both_failed_pairs":sum(r["same_primary_mode"] and r["both_failed"] for r in pairs),
 "different_mode_both_failed_pairs":sum(not r["same_primary_mode"] and r["both_failed"] for r in pairs),
 "paired_statistics":statistics,"test_family":family,"test_method":"Exact two-sided sign test on nonzero matched-task differences, ties excluded; binary equivalent to exact McNemar. All 8 exploratory p-values reported with Holm correction.",
 "option_visibility":option_stats,"correct_or_plausible_product_no_buy":no_buy,"cap_censoring":cap,
 "proven_nonterminal_hopeless_before_round_10":0,"hopelessness_note":"No saved trace proves remaining catalog search impossible. Three early failed terminal purchases are known terminal failures, not evidence capped episodes were hopeless.",
 "loop_sensitivity":sensitivity,
 "loop_incidence_arm_only_task_ids":{a:[r["task_id"] for r in pairs if by[int(r["task_id"].split("_")[-1]),a]["loop_incidence"] and not by[int(r["task_id"].split("_")[-1]),ARMS[1-ARMS.index(a)]]["loop_incidence"]] for a in ARMS},
 "purchase_audit":{"attempts":15,"terminal":4,"unlisted_nonterminal_unchanged":11,"inherit_attempts":8,"reset_attempts":7,"inherit_unavailable":7,"reset_unavailable":4},
 "rank_movement":sorted(rule_ranks,key=lambda r:abs(r["rank_delta_reset_minus_inherit"]),reverse=True),
 "evidence_level":2,"exploratory_only":True}
dump("summary_statistics.json",out)

print(json.dumps({k:v for k,v in out.items() if k not in ("rank_movement",)},indent=2))

"""Replay one saved pre-EDIT state using the separately obtained patched upstream."""
import argparse,importlib.util,json,math
from pathlib import Path
def replay(state,rules):
    pre=[tuple(r) for r in state["pre_edit_rules"]];op=tuple(state["parsed_operation"])
    branches={}
    for policy in ("inherit","reset"):
        events=[]
        post=rules.update_rules(pre,[op],list_full=state["list_full"],expel_edit_count_policy=policy,edit_events=events,step=state["source_step"])
        assert len(events)==1
        target=next((i+1,c) for i,(text,c) in enumerate(post) if text==op[1])
        branches[policy]={"count":target[1],"rank":target[0],"rules":post,"event":events[0]}
    i,z=branches["inherit"],branches["reset"]
    return {"source":f'{state["source_run"]} step {state["source_step"]} / rule index {state["source_event"]["rule_index"]}',
      "old_count":state["old_count"],"edit_change":state["edit_change"],"inherit_count":i["count"],"reset_count":z["count"],
      "inherit_rank":i["rank"],"reset_rank":z["rank"],"rule_count":len(i["rules"]),
      "identical_text_sets":sorted(t for t,c in i["rules"])==sorted(t for t,c in z["rules"]),
      "rule_numbers_changed":sum(a!=b for a,b in zip([t for t,c in i["rules"]],[t for t,c in z["rules"]])),
      "removal_resistance":{"full_list_remove_strength":3,"inherit_calls_to_remove":math.ceil(i["count"]/3),"reset_calls_to_remove":math.ceil(z["count"]/3),
        "inherit_calls_to_remove_nonfull":i["count"],"reset_calls_to_remove_nonfull":z["count"],
        "assumption":"Same rule repeatedly targeted; no intervening updates."},
      "evidence_level":2},branches
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--state",type=Path,required=True)
    p.add_argument("--rules-file",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--memory-dir",type=Path);a=p.parse_args()
    spec=importlib.util.spec_from_file_location("audited_expel_rules",a.rules_file);rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
    report,branches=replay(json.loads(a.state.read_text()),rules)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+"\n")
    if a.memory_dir:
        a.memory_dir.mkdir(parents=True,exist_ok=True)
        for policy,b in branches.items():(a.memory_dir/f"{policy}.txt").write_text(rules.render_rules(b["rules"]))
    print(json.dumps({k:v for k,v in report.items() if k!="removal_resistance"},indent=2))
if __name__=="__main__":main()

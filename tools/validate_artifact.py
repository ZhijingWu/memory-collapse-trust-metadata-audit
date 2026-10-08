"""Validate public results, metadata, relative links and source syntax offline."""
import argparse,csv,importlib.util,json,math,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def read(path):return json.loads((ROOT/path).read_text())
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--upstream",type=Path);a=p.parse_args()
    security=module("security_scan","tools/security_scan.py").scan(ROOT);assert security["passed"],security["findings"]
    for path in ROOT.rglob("*.py"):compile(path.read_text(),str(path),"exec")
    frozen=read("results/mechanism/frozen_pre_edit_state.json");expected=read("results/mechanism/shared_pre_edit_replay.json")
    branches={}
    for policy,count in [("inherit",frozen["old_count"]+1),("reset",2)]:
        rr=[list(r) for r in frozen["pre_edit_rules"]];rr[frozen["source_event"]["rule_index"]-1]=[frozen["parsed_operation"][1],count]
        rr.sort(key=lambda r:r[1],reverse=True);branches[policy]=rr
        rank=next(i+1 for i,r in enumerate(rr) if r[0]==frozen["parsed_operation"][1])
        assert rank==expected[policy+"_rank"] and count==expected[policy+"_count"]
    assert len(branches["inherit"])==36 and sorted(t for t,c in branches["inherit"])==sorted(t for t,c in branches["reset"])
    aa,pairs=module("stochasticity","src/stochasticity/analyze.py").analyze(read("results/stochasticity/lexical_features.json")["runs"])
    saved=read("results/stochasticity/summary.json")
    for group,g in aa["groups"].items():
        for metric,d in g["metrics"].items():
            for k,v in d.items():
                old=saved["groups"][group]["metrics"][metric][k]
                assert old is None if v is None else math.isclose(v,old,abs_tol=1e-12)
    assert len(pairs)==15 and all(r["first_divergence_step"]==1 and r["divergence_before_either_first_edit"] for r in pairs)
    cm=module("paired","src/controlled_eval/analyze_pairs.py")
    outcomes=cm.analyze(list(csv.DictReader((ROOT/"results/controlled_eval/paired_results_summary.csv").open())))
    observed=read("results/controlled_eval/summary.json")
    assert outcomes["paired_outcomes"]==observed["paired_outcomes"]
    assert outcomes["aggregate"]["inherit"]["successes"]==0 and outcomes["aggregate"]["reset"]["successes"]==1
    assert outcomes["exact_two_sided_mcnemar_binomial_p"]==1 and sum(x["cap_hits"] for x in outcomes["aggregate"].values())==96
    off=module("offline_summary","src/offline_diagnostic/summarize.py").summarize(list(csv.DictReader((ROOT/"results/offline_diagnostic/episode_features.csv").open())))
    reference=read("results/offline_diagnostic/summary.json")
    assert off["failure_counts"]==reference["failure_counts"]
    for f,stats in off["paired_statistics"].items():
        for k,v in stats.items():assert math.isclose(v,reference["paired_statistics"][f][k],abs_tol=1e-12),(f,k)
    options=list(csv.DictReader((ROOT/"results/offline_diagnostic/option_events_summary.csv").open()))
    purchases=list(csv.DictReader((ROOT/"results/offline_diagnostic/purchase_attempts_summary.csv").open()))
    assert len(options)==14 and all(r["text_changed"]=="False" and r["before_text_sha256"]==r["after_text_sha256"] for r in options)
    assert sum(bool(r["later_purchase_confirmation_step"]) for r in options)==3
    assert len(purchases)==15 and sum(r["terminal"]=="True" for r in purchases)==4
    assert sum(r["control_visible"]=="False" and r["terminal"]=="False" and r["before_text_sha256"]==r["after_text_sha256"] for r in purchases)==11
    broken=[]
    for md in ROOT.rglob("*.md"):
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)",md.read_text()):
            if re.match(r"(?:https?://|mailto:|#)",link):continue
            path=link.split("#",1)[0]
            if path and not (md.parent/path).exists():broken.append((str(md.relative_to(ROOT)),link))
    assert not broken,broken
    readme=(ROOT/"README.md").read_text()
    for value in ["old count 29","count 30/rank 2","count 2/rank 15","pooled A/A 0.5732","A/B 0.5735",
                  "inherit 0/50","reset 1/50","p = 1.0","96/100","11/15","14 genuine option"]:assert value in readme,value
    assert "Zhijing Wu" in (ROOT/"LICENSE").read_text() and "CC BY 4.0" in (ROOT/"upstream/README.md").read_text()
    cff_status="structure checked without optional YAML"
    try:
        import yaml
        cff=yaml.safe_load((ROOT/"CITATION.cff").read_text())
        assert cff["cff-version"]=="1.2.0" and cff["authors"]==[{"given-names":"Zhijing","family-names":"Wu"}]
        assert len(cff["references"][0]["authors"])==7 and cff["license"]=="MIT";cff_status="YAML syntax and citation attribution checked"
    except ImportError:pass
    if a.upstream:
        import os
        env=os.environ.copy();env["AUDIT_UPSTREAM"]=str(a.upstream.resolve());env["PYTHONDONTWRITEBYTECODE"]="1"
        subprocess.run([sys.executable,str(ROOT/"tests/test_expel_policy.py"),"-v"],env=env,check=True)
    print(json.dumps({"passed":True,"replay_counts":[30,2],"replay_ranks":[2,15],"lexical_pairs":15,
       "controlled_task_pairs":50,"offline_episodes":100,"option_events":14,"purchase_attempts":15,
       "relative_links":"all resolve","citation":cff_status,"security":security},indent=2))
if __name__=="__main__":main()

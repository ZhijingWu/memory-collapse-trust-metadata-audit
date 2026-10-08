"""Recompute all 15 descriptive comparisons from compact lexical features."""
import argparse,csv,itertools,json,math,statistics as st
from pathlib import Path
def dist(x):
    return {"n":len(x),"mean":st.mean(x) if x else None,"median":st.median(x) if x else None,
      "min":min(x) if x else None,"max":max(x) if x else None,"population_sd":st.pstdev(x) if x else None}
def jaccard(a,b):return len(a&b)/len(a|b) if a|b else 1
def analyze(runs):
    pairs=[]
    for x,y in itertools.combinations(runs,2):
        a,b=runs[x],runs[y];sa,sb=a["summary"],b["summary"]
        first=next((int(i) for i,h in a["step_sequence_sha256"].items() if h!=b["step_sequence_sha256"].get(i)),None)
        ea=sa["first_edit_step"] or math.inf;eb=sb["first_edit_step"] or math.inf
        ra,rb=set(a["ordered_rule_sha256"]),set(b["ordered_rule_sha256"]);common=ra&rb
        order=sorted(common,key=a["ordered_rule_sha256"].index);pos={t:b["ordered_rule_sha256"].index(t) for t in common}
        n=len(common)*(len(common)-1)//2;bad=sum(pos[u]>pos[v] for i,u in enumerate(order) for v in order[i+1:])
        concord=1-bad/n if n else None
        ta,tb=a["token_counts"],b["token_counts"];lj=jaccard(set(ta),set(tb))
        denominator=math.sqrt(sum(v*v for v in ta.values())*sum(v*v for v in tb.values()))
        cosine=sum(v*tb.get(k,0) for k,v in ta.items())/denominator if denominator else float(ta==tb)
        group="inherit_AA" if a["policy"]==b["policy"]=="inherit" else "reset_AA" if a["policy"]==b["policy"]=="reset" else "AB"
        pairs.append({"run_a":x,"run_b":y,"group":group,"first_divergence_step":first,"divergence_before_either_first_edit":first is not None and first<min(ea,eb),
          "first_edit_a":sa["first_edit_step"],"first_edit_b":sb["first_edit_step"],
          "exact_rule_jaccard":jaccard(ra,rb),"exact_rule_distance":1-jaccard(ra,rb),
          "lexical_token_jaccard":lj,"lexical_token_jaccard_distance":1-lj,"lexical_count_cosine":cosine,"lexical_count_cosine_distance":1-cosine,
          "shared_exact_rule_strings":len(common),"order_comparable_pairs":n,"order_concordance":concord,"ordering_distance":1-concord if concord is not None else None,
          "absolute_edit_count_difference":abs(sa["edit_count"]-sb["edit_count"]),
          "absolute_rule_count_difference":abs(sa["final_rule_count"]-sb["final_rule_count"]),
          "absolute_memory_chars_difference":abs(sa["memory_chars"]-sb["memory_chars"]),
          "absolute_mean_old_count_difference":abs(sa["old_count"]["mean"]-sb["old_count"]["mean"]),
          "absolute_mean_edit_change_difference":abs(sa["edit_change"]["mean"]-sb["edit_change"]["mean"])})
    fields=[k for k in pairs[0] if k.endswith("_distance") or k.startswith("absolute_")]
    groups={}
    for g in ("inherit_AA","reset_AA","pooled_AA","AB"):
        rr=[r for r in pairs if r["group"]==g or g=="pooled_AA" and r["group"]!="AB"]
        groups[g]={"n_pairs":len(rr),"before_edit_divergence_pairs":sum(r["divergence_before_either_first_edit"] for r in rr),
                   "metrics":{f:dist([r[f] for r in rr if r[f] is not None]) for f in fields}}
    return {"groups":groups,"note":"Three builds per policy; pair distances are dependent. Lexical distance is not semantic correctness."},pairs
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--features",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);a=p.parse_args()
    report,pairs=analyze(json.loads(a.features.read_text())["runs"]);a.output_dir.mkdir(parents=True,exist_ok=True)
    (a.output_dir/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
    with (a.output_dir/"pairwise_summary.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
    print(json.dumps({g:v["metrics"]["lexical_token_jaccard_distance"] for g,v in report["groups"].items()},indent=2))
if __name__=="__main__":main()

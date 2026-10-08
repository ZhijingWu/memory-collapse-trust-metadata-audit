"""Reaggregate sanitized episode features using matched-task sign tests."""
import argparse,collections,csv,json,math,statistics as st
from pathlib import Path
FAMILY=["search_actions","option_clicks","buy_now_actions","product_revisits","repeated_identical_actions","loop_incidence","unchanged_option_incidence","left_after_required_options"]
def number(x):
    if str(x).lower() in ("true","false"):return float(str(x).lower()=="true")
    return float(x)
def summarize(rows):
    by={(r["task_id"],r["arm"]):r for r in rows};ids=list(dict.fromkeys(r["task_id"] for r in rows))
    assert len(by)==len(rows)==2*len(ids);stats={}
    for f in FAMILY:
        values=[(number(by[t,"inherit"][f]),number(by[t,"reset"][f])) for t in ids];ds=[z-i for i,z in values]
        pos=sum(d>0 for d in ds);neg=sum(d<0 for d in ds);n=pos+neg;k=min(pos,neg)
        p=min(1,2*sum(math.comb(n,j) for j in range(k+1))/2**n) if n else 1
        stats[f]={"inherit_mean":st.mean(i for i,z in values),"reset_mean":st.mean(z for i,z in values),
          "inherit_median":st.median(i for i,z in values),"reset_median":st.median(z for i,z in values),
          "paired_mean_difference":st.mean(ds),"paired_median_difference":st.median(ds),"reset_greater_pairs":pos,
          "inherit_greater_pairs":neg,"equal_pairs":len(ds)-n,"exact_two_sided_sign_p":p}
    high=0
    for j,f in enumerate(sorted(FAMILY,key=lambda f:stats[f]["exact_two_sided_sign_p"])):
        high=max(high,min(1,stats[f]["exact_two_sided_sign_p"]*(len(FAMILY)-j)));stats[f]["holm_adjusted_p"]=high
    return {"failure_counts":{a:dict(collections.Counter(r["primary_failure_mode"] for r in rows if r["arm"]==a)) for a in ("inherit","reset")},
      "paired_statistics":stats,"same_primary_mode_all_pairs":sum(by[t,"inherit"]["primary_failure_mode"]==by[t,"reset"]["primary_failure_mode"] for t in ids),
      "note":"Exploratory descriptions, not causal allocations; complete eight-feature family."}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    report=summarize(list(csv.DictReader(a.input.open())));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()

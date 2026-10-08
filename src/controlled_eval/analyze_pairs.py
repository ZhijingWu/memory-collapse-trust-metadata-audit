"""Analyze one row per matched task from the compact public outcome table."""
import argparse,csv,json,math,statistics as st
from pathlib import Path
def yes(v):return str(v).lower() in ("true","1")
def analyze(rows):
    assert len({r["task_id"] for r in rows})==len(rows)
    n=len(rows);counts={"reset_wins":0,"inherit_wins":0,"both_success":0,"both_fail":0};arms={}
    for r in rows:
        i,z=yes(r["inherit_success"]),yes(r["reset_success"])
        counts["both_success" if i and z else "inherit_wins" if i else "reset_wins" if z else "both_fail"]+=1
    for a in ("inherit","reset"):
        arms[a]={"successes":sum(yes(r[a+"_success"]) for r in rows),"denominator":n,"success_rate":sum(yes(r[a+"_success"]) for r in rows)/n,
          "mean_reward":st.mean(float(r[a+"_reward"]) for r in rows),"mean_rounds":st.mean(int(r[a+"_episode_length"]) for r in rows),
          "mean_model_calls":st.mean(int(r[a+"_model_calls"]) for r in rows),"total_model_calls":sum(int(r[a+"_model_calls"]) for r in rows),
          "cap_hits":sum(yes(r[a+"_round_limit_reached"]) for r in rows),"completed_purchases":sum(yes(r[a+"_terminated_purchase"]) for r in rows)}
    d=counts["reset_wins"]+counts["inherit_wins"];k=min(counts["reset_wins"],counts["inherit_wins"])
    p=min(1,2*sum(math.comb(d,j) for j in range(k+1))/2**d) if d else 1
    return {"paired_tasks":n,"aggregate":arms,"paired_outcomes":counts,"discordant_pairs":d,
      "paired_success_rate_difference_reset_minus_inherit":(counts["reset_wins"]-counts["inherit_wins"])/n,
      "exact_two_sided_mcnemar_binomial_p":p,"discordant_task_ids":[r["task_id"] for r in rows if yes(r["inherit_success"])!=yes(r["reset_success"])]}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    r=analyze(list(csv.DictReader(a.input.open())));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2))
if __name__=="__main__":main()

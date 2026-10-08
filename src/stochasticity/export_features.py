"""Export compact lexical features from independently saved compression artifacts."""
import argparse,collections,hashlib,json,re,statistics as st
from pathlib import Path
SPEC=[("inherit_original","n50_inherit","inherit"),("inherit_rep2","inherit_rep2","inherit"),("inherit_rep3","inherit_rep3","inherit"),
      ("reset_original","n50_reset","reset"),("reset_rep2","reset_rep2","reset"),("reset_rep3","reset_rep3","reset")]
def distribution(xs):
    return {"n":len(xs),"mean":st.mean(xs) if xs else None,"median":st.median(xs) if xs else None,"min":min(xs) if xs else None,
            "max":max(xs) if xs else None,"population_sd":st.pstdev(xs) if xs else None}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--runs-root",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    runs={}
    for label,folder,policy in SPEC:
        d=a.runs_root/folder;ck=json.loads((d/"mem.ckpt.json").read_text());texts=[t for t,c in ck["rules"]]
        assert ck["expel_edit_count_policy"]==policy
        events=ck["edit_events"];snap={}
        for i in range(1,ck["step_done"]+1):
            seq=[re.sub(r"^\d+\. ","",l) for l in (d/f"intermediate_expel/step_{i:03d}.txt").read_text().splitlines() if l.strip()]
            snap[str(i)]=hashlib.sha256(json.dumps(seq,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
        runs[label]={"policy":policy,"token_counts":dict(sorted(collections.Counter(re.findall(r"\w+","\n".join(texts).casefold())).items())),
          "ordered_rule_sha256":[hashlib.sha256(t.encode()).hexdigest() for t in texts],"step_sequence_sha256":snap,
          "summary":{"label":label,"policy":policy,"edit_count":len(events),"final_rule_count":len(texts),"memory_chars":len((d/"mem.txt").read_text()),
                     "first_edit_step":min((e["step"] for e in events),default=None),
                     "old_count":distribution([e["old_count"] for e in events]),"edit_change":distribution([e["edit_change"] for e in events])}}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({"runs":runs},indent=2)+"\n")
if __name__=="__main__":main()

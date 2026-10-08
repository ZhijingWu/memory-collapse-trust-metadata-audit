"""Verify identical rule content and different ordering; no model calls."""
import argparse,collections,hashlib,json,re
from pathlib import Path
def compare(a,b):
    ra=[re.sub(r"^\d+\.\s*","",x) for x in a.splitlines() if x.strip()]
    rb=[re.sub(r"^\d+\.\s*","",x) for x in b.splitlines() if x.strip()]
    return {"rules_inherit":len(ra),"rules_reset":len(rb),"identical_text_multisets":collections.Counter(ra)==collections.Counter(rb),
      "different_order":ra!=rb,"characters_inherit":len(a),"characters_reset":len(b),
      "sha256_inherit":hashlib.sha256(a.encode()).hexdigest(),"sha256_reset":hashlib.sha256(b.encode()).hexdigest()}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--inherit",type=Path,required=True);p.add_argument("--reset",type=Path,required=True);a=p.parse_args()
    r=compare(a.inherit.read_text(),a.reset.read_text());assert r["identical_text_multisets"] and r["different_order"]
    print(json.dumps(r,indent=2))
if __name__=="__main__":main()

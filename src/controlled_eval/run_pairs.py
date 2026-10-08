"""Plan or explicitly execute counterbalanced task pairs through upstream's CLI."""
import argparse,json,os,subprocess,sys
from pathlib import Path
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream",type=Path,required=True);p.add_argument("--python",default=sys.executable)
    p.add_argument("--stream",type=Path,required=True);p.add_argument("--inherit-memory",type=Path,required=True)
    p.add_argument("--reset-memory",type=Path,required=True);p.add_argument("--env-url",required=True)
    p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--model",default="gpt-5.4-mini")
    p.add_argument("--execute",action="store_true",help="Explicitly permit paid model calls; default only prints the schedule.")
    a=p.parse_args();stream=json.loads(a.stream.read_text());entries=stream["tasks"] if isinstance(stream,dict) else stream
    assert len(entries)==50 and len({e["game_idx"] for e in entries})==50
    from check_memories import compare
    control=compare(a.inherit_memory.read_text(),a.reset_memory.read_text())
    assert control["identical_text_multisets"] and control["different_order"],"Require equal content and different ordering."
    if a.execute:
        a.output_dir.mkdir(parents=True,exist_ok=True)
        manifest_path=a.output_dir/"manifest.json"
        manifest={"tasks":entries,"preflight":{"memory_hashes":{},"initial_prompt_hashes":{}}}
        if manifest_path.exists():
            manifest=json.loads(manifest_path.read_text())
            assert manifest["tasks"]==entries,"Input stream changed during resume."
        manifest_path.write_text(json.dumps(manifest,indent=2))
    cli=a.upstream.resolve()/"agentgym/agentenv/scripts/memory/evaluate.py"
    env=os.environ.copy();env.update(PYTHONPATH=str(a.upstream.resolve()/"agentgym/agentenv"),SCIWORLD_SYS_PROMPT="",SCIWORLD_REASONING_EFFORT="none",PYTHONDONTWRITEBYTECODE="1")
    for pos,entry in enumerate(entries,1):
        for arm in (("inherit","reset") if pos%2 else ("reset","inherit")):
            print(f'{pos:02d} {entry["game_idx"]} {arm}',flush=True)
            if not a.execute:continue
            out=a.output_dir/"episodes"/f"{pos:02d}"/arm;result=out/"results.jsonl"
            if result.exists():
                records=[json.loads(l) for l in result.read_text().splitlines()]
                if len(records)==1 and "error" not in records[0] and not records[0].get("skipped"):continue
                raise RuntimeError("Incomplete prior episode retained; inspect it before a new attempt.")
            if (out/"started.json").exists():raise RuntimeError("Unfinished episode retained; no automatic restart.")
            out.mkdir(parents=True,exist_ok=True);task=out/"stream.json"
            task.write_text(json.dumps({"name":"controlled_single_task","seed":stream.get("seed") if isinstance(stream,dict) else None,"tasks":[entry]}))
            (out/"started.json").write_text(json.dumps({"position":pos,"task_id":entry["game_idx"],"arm":arm}))
            with (a.output_dir/"execution_order.jsonl").open("a") as f:f.write(json.dumps({"position":pos,"idx":entry["game_idx"],"arm":arm})+"\n")
            memory=a.inherit_memory if arm=="inherit" else a.reset_memory
            cmd=[a.python,str(Path(__file__).with_name("audited_episode.py")),"--upstream",str(a.upstream.resolve()),
                 "--memory",str(memory.resolve()),"--stream",str(task.resolve()),"--env-url",a.env_url,
                 "--output-dir",str(out.resolve()),"--model",a.model]
            with (out/"evaluate.log").open("w") as log:subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
            records=[json.loads(l) for l in result.read_text().splitlines()]
            assert len(records)==1 and records[0]["idx"]==entry["game_idx"] and not records[0].get("skipped") and "error" not in records[0]
            context=json.loads((out/"memory_context.json").read_text())
            manifest["preflight"]["memory_hashes"][arm]=context["memory_sha256"]
            manifest["preflight"]["initial_prompt_hashes"][arm]=context["initial_prompt_sha256"]
            manifest_path.write_text(json.dumps(manifest,indent=2))
        if a.execute:
            pair={"position":pos,"idx":entry["game_idx"],"task_id":"webshop_"+str(entry["game_idx"]),"execution_order":["inherit","reset"] if pos%2 else ["reset","inherit"]}
            for arm in ("inherit","reset"):pair[arm]=json.loads((a.output_dir/"episodes"/f"{pos:02d}"/arm/"completion.json").read_text())
            with (a.output_dir/"paired_results.jsonl").open("a") as f:
                existing=[] if f.tell()==0 else [json.loads(l)["idx"] for l in (a.output_dir/"paired_results.jsonl").read_text().splitlines()]
                if entry["game_idx"] not in existing:f.write(json.dumps(pair)+"\n")
    if a.execute:
        rows=[json.loads(l) for l in (a.output_dir/"paired_results.jsonl").read_text().splitlines()]
        counts={"reset_wins":0,"inherit_wins":0,"both_success":0,"both_fail":0}
        for r in rows:
            i,z=r["inherit"]["success"],r["reset"]["success"]
            counts["both_success" if i and z else "inherit_wins" if i else "reset_wins" if z else "both_fail"]+=1
        (a.output_dir/"results_summary.json").write_text(json.dumps({"paired_outcomes":counts},indent=2))

if __name__=="__main__":main()

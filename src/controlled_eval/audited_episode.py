"""Audited frozen-memory episode; invoked only by the explicit paid-run option."""
import argparse,hashlib,json,os,runpy,sys,time
from pathlib import Path
def append(p,v):
    with p.open("a") as f:f.write(json.dumps(v,ensure_ascii=False)+"\n")
def readlines(p):return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--upstream",type=Path,required=True)
    p.add_argument("--memory",type=Path,required=True);p.add_argument("--stream",type=Path,required=True)
    p.add_argument("--env-url",required=True);p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--model",required=True)
    a=p.parse_args();out=a.output_dir;out.mkdir(parents=True,exist_ok=True)
    assert os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_BASE_URL"),"Set API credentials in your environment."
    sys.path.insert(0,str(a.upstream/"agentgym/agentenv"))
    from agentenv.envs.webshop import WebshopAdapter,WebshopEnvClient
    from agentenv.controller.types import ActionFormat
    from agentenv.memory.env_context import get_env_context
    from agentenv.memory.framings import render_section
    from agentenv.memory.base import BaseMemory
    from agentenv.memory.methods.expel.core import ExpeL
    assert ExpeL.on_episode_end is BaseMemory.on_episode_end
    memory_hash=hashlib.sha256(a.memory.read_bytes()).hexdigest()
    header=WebshopAdapter.conversation_start_dict[ActionFormat.REACT][0]["value"]+render_section(get_env_context("webshop")["framing_overrides"]["expel"],a.memory.read_text())
    header_hash=hashlib.sha256(header.encode()).hexdigest()
    (out/"memory_context.json").write_text(json.dumps({"memory_sha256":memory_hash,"initial_prompt_sha256":header_hash}))
    old_step=WebshopEnvClient.step
    def step(self,action):
        response=old_step(self,action)
        append(out/"action_audit.jsonl",{"round":len(readlines(out/"action_audit.jsonl"))+1,"action_response":action,
             "state":response.state,"reward":response.reward,"done":response.done})
        return response
    WebshopEnvClient.step=step
    import openai,httpx
    from openai.resources.chat.completions import Completions
    old_init=openai.OpenAI.__init__;old_create=Completions.create
    def init(self,*args,**kwargs):kwargs["max_retries"]=0;old_init(self,*args,**kwargs)
    openai.OpenAI.__init__=init
    def create(self,*args,**kwargs):
        assert kwargs["model"]==a.model and kwargs["temperature"]==0 and kwargs["reasoning_effort"]=="none"
        assert kwargs["max_completion_tokens"]==1024 and "top_p" not in kwargs
        assert kwargs["messages"][0]["content"]==header and not any(m["role"]=="system" for m in kwargs["messages"])
        call=len(readlines(out/"response_audit.jsonl"))+1
        append(out/"prompt_audit.jsonl",{"call":call,"memory_sha256":memory_hash,"initial_prompt_sha256":header_hash})
        for attempt in range(4):
            try:response=old_create(self,*args,**kwargs);break
            except Exception as exc:
                again=isinstance(exc,(openai.APIConnectionError,openai.APITimeoutError,httpx.TransportError)) and attempt<3
                append(out/"request_attempts.jsonl",{"call":call,"attempt":attempt+1,"exception_type":type(exc).__name__,"retry":again})
                if not again:raise SystemExit(90)
                time.sleep(2**(attempt+1))
        usage=response.usage
        append(out/"response_audit.jsonl",{"call":call,"content":response.choices[0].message.content,"finish_reason":response.choices[0].finish_reason,
          "input_tokens":usage.prompt_tokens,"cached_input_tokens":getattr(getattr(usage,"prompt_tokens_details",None),"cached_tokens",0) or 0,
          "output_tokens":usage.completion_tokens})
        assert hashlib.sha256(a.memory.read_bytes()).hexdigest()==memory_hash
        return response
    Completions.create=create
    cli=a.upstream/"agentgym/agentenv/scripts/memory/evaluate.py"
    sys.argv=[str(cli),"--env","webshop","--method","expel","--memory-file",str(a.memory),"--stream",str(a.stream),
      "--env-url",a.env_url,"--save-path",str(out),"--agent-model",a.model,"--agent-temperature","0","--agent-max-tokens","1024",
      "--agent-extra-body","{}","--max-rounds","10","--processes","1"]
    runpy.run_path(str(cli),run_name="__main__")
    results=readlines(out/"results.jsonl");assert len(results)==1 and "error" not in results[0] and not results[0].get("skipped")
    r=results[0];actions=readlines(out/"action_audit.jsonl");calls=readlines(out/"response_audit.jsonl")
    assert len(actions)==len(calls)<=10 and hashlib.sha256(a.memory.read_bytes()).hexdigest()==memory_hash
    r.update(model_calls=len(calls),episode_length=len(actions),terminated_purchase=any(x["done"] for x in actions),
             round_limit_reached=len(actions)==10 and not actions[-1]["done"],
             truncated_calls=sum(x["finish_reason"]=="length" for x in calls),memory_sha256=memory_hash)
    (out/"completion.json").write_text(json.dumps(r,indent=2)+"\n")
if __name__=="__main__":main()

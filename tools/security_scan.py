"""Scan an artifact for secret-like values and private runtime metadata."""
import argparse,json,re,subprocess
from pathlib import Path
PATTERNS={
 "secret_like":re.compile(r"(?<![A-Za-z0-9_])(?:sk-[A-Za-z0-9_-]{16,}|fk[A-Za-z0-9]{20,})"),
 "private_filesystem":re.compile(r"/(?:data|home)\d+/[A-Za-z0-9_.-]+|[A-Za-z]:[\\/]Users[\\/]|~/\.config/"),
 "private_ip":re.compile(r"\b(?:127|10)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b|\b192\.168\.\d{1,3}\.\d{1,3}\b|\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b"),
 "private_host":re.compile(r"\b[a-z]+-lab\b"),
 "provider_private_url":re.compile(r"https?://[^\s\"']*api\d+d[^\s\"']*"),
 "auth_value":re.compile(r"(?i)(?:authorization|bearer|cookie)\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{20,}"),
 "runtime_identifier":re.compile(r"(?i)(?:server_pid|installer_pid|session_id|env_id)\s*[\"']?\s*[:=]\s*[\"']?\d+"),
}
def scan(root,tracked=False):
    paths=[root/p for p in subprocess.check_output(["git","-C",str(root),"ls-files"],text=True).splitlines()] if tracked else [p for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts]
    findings=[]
    for p in paths:
        rel=str(p.relative_to(root));name=p.name
        if name==".env" or p.suffix in (".env",".log",".pyc") or any(x in p.relative_to(root).parts for x in ("__pycache__",".venv","venv","cache","raw_private")) or name.startswith(("credentials","secrets")):
            findings.append({"file":rel,"category":"excluded_runtime_file"})
        try:text=p.read_text(encoding="utf-8")
        except UnicodeDecodeError:findings.append({"file":rel,"category":"unexpected_binary"});continue
        for category,rx in PATTERNS.items():
            if rx.search(text):findings.append({"file":rel,"category":category})
        for m in re.finditer(r"OPENAI_API_KEY\s*=\s*([^\s]+)",text):
            value=m.group(1).strip("\"'")
            if value not in ("...","YOUR_KEY","<YOUR_KEY>","<key>"):findings.append({"file":rel,"category":"non_placeholder_key_assignment"})
    return {"passed":not findings,"files_scanned":len(paths),"findings":findings,"scan_scope":"tracked" if tracked else "artifact excluding Git metadata"}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--tracked",action="store_true");a=p.parse_args();r=scan(a.root.resolve(),a.tracked);print(json.dumps(r,indent=2))
    raise SystemExit(0 if r["passed"] else 1)
if __name__=="__main__":main()

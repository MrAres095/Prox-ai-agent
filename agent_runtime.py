"""Bounded autonomous coding runtime for Prox AI Agent.

Only executes commands inside configured workspace roots. This is not a Proxmox
admin executor; infrastructure actions must be added separately with least-privilege API access.
"""
import json
import os
import shlex
import subprocess
from pathlib import Path

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", "/var/lib/proxmox-ai-agent/repos")).resolve()
MAX_OUTPUT = 12000
TIMEOUT = int(os.getenv("AGENT_COMMAND_TIMEOUT", "300"))

# Deliberately narrow command allowlist. No shell=True and no arbitrary host administration.
ALLOWED = {
    "pwd", "ls", "find", "cat", "head", "tail", "grep", "rg",
    "git", "python", "python3", "pytest", "pip", "pip3",
    "npm", "npx", "node", "java", "javac", "gradle", "gradlew",
    "./gradlew", "make", "cmake", "cargo", "rustc", "go", "dotnet",
}

def _workspace_path(raw):
    p = (WORKSPACE / raw).resolve()
    if p != WORKSPACE and WORKSPACE not in p.parents:
        raise ValueError("Putanja izlazi iz radnog prostora.")
    return p

def run_workspace_command(command, cwd="."):
    if not isinstance(command, str) or len(command) > 2000:
        raise ValueError("Neispravna ili preduga naredba.")
    args = shlex.split(command)
    if not args or args[0] not in ALLOWED:
        raise ValueError("Naredba nije na allowlisti. Nije izvršena.")
    # Block shell chaining, redirection, substitutions and explicit privilege escalation.
    forbidden = {";", "&&", "||", "|", ">", ">>", "<", "$(", "`", "sudo", "su", "rm", "mkfs", "shutdown", "reboot"}
    if any(token in forbidden or any(x in token for x in ("$(", "`")) for token in args):
        raise ValueError("Naredba sadrži zabranjeni operator ili opasnu naredbu.")
    if any(token.startswith("/") or token == ".." or token.startswith("../") or "/../" in token for token in args):
        raise ValueError("Apsolutne putanje i izlazak iz radnog prostora nisu dopušteni.")
    if args[0] == "find" and any(token in {"-exec", "-execdir", "-delete", "-ok"} for token in args):
        raise ValueError("Opasne find opcije nisu dopuštene.")
    workdir = _workspace_path(cwd)
    if not workdir.exists() or not workdir.is_dir():
        raise ValueError("Radna mapa ne postoji.")
    env = {"PATH": os.getenv("PATH", "/usr/local/bin:/usr/bin:/bin"),
           "HOME": str(WORKSPACE), "CI": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    result = subprocess.run(args, cwd=str(workdir), env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=TIMEOUT, check=False)
    output = (result.stdout or "")[-MAX_OUTPUT:]
    return {"returncode": result.returncode, "output": output}

def read_workspace_file(path):
    target = _workspace_path(path)
    if not target.is_file():
        raise ValueError("Datoteka ne postoji unutar radnog prostora.")
    if target.stat().st_size > 200_000:
        raise ValueError("Datoteka je veća od ograničenja čitanja (200 KB).")
    return {"path": str(target.relative_to(WORKSPACE)), "content": target.read_text(encoding="utf-8", errors="replace")}

def write_workspace_file(path, content):
    target = _workspace_path(path)
    if not isinstance(content, str) or len(content.encode("utf-8")) > 100_000:
        raise ValueError("Sadržaj mora biti tekst do 100 KB.")
    if target == WORKSPACE:
        raise ValueError("Putanja mora označavati datoteku.")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValueError("Pisanje kroz simboličku poveznicu nije dopušteno.")
    target.write_text(content, encoding="utf-8")
    return {"path": str(target.relative_to(WORKSPACE)), "bytes_written": len(content.encode("utf-8"))}

def tool_definitions():
    schemas = [
        ("run_workspace_command", "Pokreni jednu dopuštenu naredbu u radnom prostoru.", {
            "command": {"type": "string"}, "cwd": {"type": "string"}
        }, ["command"]),
        ("read_workspace_file", "Pročitaj tekstualnu datoteku unutar radnog prostora.", {
            "path": {"type": "string"}
        }, ["path"]),
        ("write_workspace_file", "Kreiraj ili zamijeni tekstualnu datoteku unutar radnog prostora.", {
            "path": {"type": "string"}, "content": {"type": "string"}
        }, ["path", "content"]),
    ]
    return [{"type": "function", "function": {"name": name, "description": desc,
        "parameters": {"type": "object", "properties": props, "required": required,
                       "additionalProperties": False}}}
        for name, desc, props, required in schemas]

def execute_tool(name, arguments):
    args = json.loads(arguments or "{}")
    if name == "run_workspace_command":
        return run_workspace_command(**args)
    if name == "read_workspace_file":
        return read_workspace_file(**args)
    if name == "write_workspace_file":
        return write_workspace_file(**args)
    return {"error": "Nepoznat alat."}

def autonomous_chat(base, model, key, history, task):
    """Tool-calling loop. Stops at bounded rounds and returns a transparent status."""
    import requests
    url = base.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    system = (
        "Ti si Prox AI coding agent i odgovaraš na hrvatskom kada korisnik piše hrvatski. "
        "Radi samostalno na zadanom zadatku, koristi alate za pregled, izmjenu i testiranje koda "
        "samo unutar radnog prostora. Ne tvrdi da si nešto napravio bez rezultata alata. "
        "Dopuštene naredbe su ograničene; ne pokušavaj zaobići ograničenja. "
        "Nemaš Proxmox API ni pristup drugim hostovima u ovoj verziji. "
        "Ako nedostaje tajna, credential ili nužna odluka, pitaj korisnika. "
        "Ne radi destruktivne operacije. Sažmi stvarne testove i preostale prepreke."
    )
    messages = [{"role": "system", "content": system}]
    for item in history[-12:]:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": task})
    tools = tool_definitions()
    # Bound total calls so a malfunctioning model cannot loop forever.
    for _ in range(20):
        response = requests.post(url, headers=headers, json={
            "model": model, "messages": messages, "tools": tools,
            "tool_choice": "auto", "temperature": 0.2
        }, timeout=180)
        response.raise_for_status()
        choice = response.json()["choices"][0]["message"]
        messages.append(choice)
        calls = choice.get("tool_calls") or []
        if not calls:
            return choice.get("content") or "Agent nije vratio tekstualni završetak."
        for call in calls:
            fn = call.get("function", {})
            try:
                result = execute_tool(fn.get("name", ""), fn.get("arguments") or "{}")
            except Exception as exc:
                result = {"error": f"{type(exc).__name__}: {exc}"}
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(result, ensure_ascii=False)})
    return "Zaustavljeno nakon 20 krugova alata radi zaštite od beskonačne petlje. Pregledaj napredak i nastavi zadatak."

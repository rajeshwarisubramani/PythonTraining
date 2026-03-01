# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  HETEROGENEOUS MULTI-AGENT DEVOPS SYSTEM                            ║
║  Auto-GPT style Microservice Builder + File Scaffolder + Runner     ║
╚══════════════════════════════════════════════════════════════════════╝

Graph Flow
──────────
  Node 1 → generate_services        (LLM : Flask source code)
  Node 2 → generate_requirements    (LLM : requirements.txt per service)  ← NEW
  Node 3 → generate_dockerfiles     (LLM : Dockerfiles)
  Node 4 → generate_k8s             (LLM : Kubernetes manifests)
  Node 5 → validate_k8s             (LLM : YAML validation)
  Node 6 → scaffold_files           (disk: write ALL files incl. requirements)
  Node 7 → generate_docker_compose  (LLM : docker-compose.yml)
  Node 8 → run_docker_containers    (subprocess: build + up -d + ps)
         → END
"""

# !pip install -U langchain langchain-openai langchain-core pydantic langgraph

import os
import subprocess
import time
from pathlib import Path
from typing import Annotated, List, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel

# ──────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────

os.environ["OPENAI_API_KEY"] = 'REPLACE_YOUR_KEY'

OUTPUT_DIR        = "./output"          # root folder for all generated files
DOCKER_COMPOSE_UP = True                # set False to skip container startup
HEALTHCHECK_DELAY = 10                  # seconds to wait after `docker compose up`

# ──────────────────────────────────────────────────────────────────────
# LLM CLIENTS
# ──────────────────────────────────────────────────────────────────────

coder_llm        = ChatOpenAI(model="gpt-4o", temperature=0)
validator_llm    = ChatOpenAI(model="gpt-4o", temperature=0)
orchestrator_llm = ChatOpenAI(model="gpt-4o", temperature=0)

# ──────────────────────────────────────────────────────────────────────
# OUTPUT SCHEMAS
# ──────────────────────────────────────────────────────────────────────

class PythonServiceOutput(BaseModel):
    explanation: str
    code: str

class RequirementsOutput(BaseModel):                        # <- NEW
    requirements: str   # raw pip requirements.txt content

class DockerOutput(BaseModel):
    dockerfile: str

class K8sOutput(BaseModel):
    manifest: str

class DockerComposeOutput(BaseModel):
    compose_yaml: str

# Structured LLM chains
python_chain  = coder_llm.with_structured_output(PythonServiceOutput)
req_chain     = coder_llm.with_structured_output(RequirementsOutput)  # <- NEW
docker_chain  = coder_llm.with_structured_output(DockerOutput)
k8s_chain     = coder_llm.with_structured_output(K8sOutput)
compose_chain = coder_llm.with_structured_output(DockerComposeOutput)

# ──────────────────────────────────────────────────────────────────────
# GRAPH STATE
# ──────────────────────────────────────────────────────────────────────

class DevOpsState(TypedDict):
    # ── conversation history ──────────────────────────────────────────
    messages:              Annotated[List, add_messages]

    # ── generated code artefacts ─────────────────────────────────────
    hello_code:            str   # Flask source for hello-service
    caller_code:           str   # Flask source for caller-service
    hello_requirements:    str   # requirements.txt for hello-service   <- NEW
    caller_requirements:   str   # requirements.txt for caller-service  <- NEW
    hello_docker:          str   # Dockerfile for hello-service
    caller_docker:         str   # Dockerfile for caller-service
    k8s_manifest:          str   # Kubernetes YAML manifest
    validation_report:     str   # K8s validation result

    # ── file-scaffolding tracking ─────────────────────────────────────
    base_path:             str        # root output directory on disk
    created_files:         List[str]  # audit log -> "[FILE] path" / "[DIR] path"
    errors:                List[str]  # non-fatal I/O errors

    # ── docker runtime tracking ───────────────────────────────────────
    docker_compose_yml:    str        # generated docker-compose.yml text
    docker_status:         str        # "pending" | "started" | "failed" | "skipped"
    docker_logs:           List[str]  # stdout / stderr from docker CLI


# ──────────────────────────────────────────────────────────────────────
# LLM OUTPUT CLEANER
# ──────────────────────────────────────────────────────────────────────

import re

def strip_fences(text: str) -> str:
    """
    Remove markdown code fences that LLMs sometimes wrap their output in.

    Handles all variants:
      ```dockerfile   ```python   ```yaml   ```plaintext   ``` (bare)

    Parameters
    ----------
    text : Raw string returned by the LLM structured output field.

    Returns
    -------
    Clean content string with no fence lines.

    Examples
    --------
    >>> strip_fences("```dockerfile\\nFROM python:3.10\\n```")
    'FROM python:3.10'
    >>> strip_fences("Flask==3.0.3\\ngunicorn==22.0.0")  # no fences — unchanged
    'Flask==3.0.3\\ngunicorn==22.0.0'
    """
    # Try to match an opening fence line + body + closing fence
    pattern = r"^\s*```[a-zA-Z0-9_\-]*\n?(.*?)\n?```\s*$"
    match = re.fullmatch(pattern, text.strip(), re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: drop any line that is just a fence marker
    cleaned = [l for l in text.splitlines() if not re.match(r"^\s*```", l)]
    return "\n".join(cleaned).strip()


# ──────────────────────────────────────────────────────────────────────
# FILE / FOLDER HELPERS
# ──────────────────────────────────────────────────────────────────────

def create_folder(path: str, state: DevOpsState) -> DevOpsState:
    """
    Create a directory (and all parents) on disk.

    Parameters
    ----------
    path  : Target directory path.
    state : DevOpsState — appends to 'created_files' or 'errors'.
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        state["created_files"].append(f"[DIR]  {path}")
        print(f"    📁  {path}")
    except OSError as exc:
        state["errors"].append(f"Folder error ({path}): {exc}")
    return state


def create_file(path: str, content: str, state: DevOpsState) -> DevOpsState:
    """
    Write UTF-8 content to a file, creating parent dirs as needed.

    Parameters
    ----------
    path    : Target file path.
    content : Text content to write.
    state   : DevOpsState — appends to 'created_files' or 'errors'.
    """
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")
        state["created_files"].append(f"[FILE] {path}")
        print(f"    📄  {path}")
    except OSError as exc:
        state["errors"].append(f"File error ({path}): {exc}")
    return state


def _run_cmd(cmd: List[str], cwd: str, state: DevOpsState):
    """
    Run a shell command and stream all output into state['docker_logs'].

    Parameters
    ----------
    cmd   : Command + args, e.g. ["docker", "compose", "up", "-d"].
    cwd   : Working directory for the subprocess.
    state : DevOpsState — stdout/stderr lines appended to 'docker_logs'.

    Returns
    -------
    (success: bool, updated_state)
    """
    display_cmd = " ".join(cmd)
    state["docker_logs"].append(f"$ {display_cmd}")
    print(f"\n    >  {display_cmd}")

    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)

        for line in proc.stdout.splitlines():
            state["docker_logs"].append(f"  [stdout] {line}")
            print(f"    {line}")
        for line in proc.stderr.splitlines():
            state["docker_logs"].append(f"  [stderr] {line}")
            print(f"    {line}")

        success = proc.returncode == 0
        if not success:
            state["docker_logs"].append(f"  [exit {proc.returncode}] FAILED")
        return success, state

    except FileNotFoundError:
        msg = "docker / docker compose not found — is Docker installed and on PATH?"
        state["docker_logs"].append(f"  [ERROR] {msg}")
        state["errors"].append(msg)
        return False, state

    except subprocess.TimeoutExpired:
        msg = "Command timed out after 120 s"
        state["docker_logs"].append(f"  [ERROR] {msg}")
        state["errors"].append(msg)
        return False, state


# ──────────────────────────────────────────────────────────────────────
# AGENT 1 – PYTHON MICROSERVICE GENERATOR
# ──────────────────────────────────────────────────────────────────────

python_prompt = ChatPromptTemplate.from_template("""
Generate a production-ready minimal Flask microservice.

Service type: {service_type}

Requirements:
- Python 3.10+
- Use Flask
- Expose GET endpoint
- Listen on 0.0.0.0:5000
- Fully executable standalone file

If service_type = hello:
  Endpoint /hello  →  JSON {{"message": "Hello World"}}

If service_type = caller:
  Call http://hello-service:5000/hello via requests and return upstream response.

Return complete working code only.
""")


def generate_services(state: DevOpsState) -> dict:
    """Node 1 — Generate Flask source code for hello-service and caller-service."""
    print("\n🚀  [Node 1] Generating Python microservices...")
    hello  = python_chain.invoke(python_prompt.format_prompt(service_type="hello"))
    caller = python_chain.invoke(python_prompt.format_prompt(service_type="caller"))
    return {"hello_code": hello.code, "caller_code": caller.code}


# ──────────────────────────────────────────────────────────────────────
# AGENT 2 – REQUIREMENTS.TXT GENERATOR  ← NEW
# ──────────────────────────────────────────────────────────────────────

requirements_prompt = ChatPromptTemplate.from_template("""
You are a Python dependency expert.

Analyse the following Flask microservice source code and generate a minimal,
pinned requirements.txt file for it.

Rules:
- Include ONLY packages actually imported or used in the code.
- Pin every package to a specific stable version (e.g. Flask==3.0.3).
- Always include gunicorn (production WSGI server used in the Dockerfile).
- One package per line, no comments, no blank lines.
- Do NOT include stdlib modules (os, json, time, etc.).

Service name : {service_name}
Source code  :
{code}
""")


def generate_requirements(state: DevOpsState) -> dict:
    """
    Node 2 — Generate a pinned requirements.txt for each microservice.

    Calls the LLM separately for hello-service and caller-service using
    their respective source code, then stores results in DevOpsState.

    DevOpsState fields updated
    --------------------------
    hello_requirements  : raw requirements.txt content for hello-service
    caller_requirements : raw requirements.txt content for caller-service
    """
    print("\n📋  [Node 2] Generating requirements.txt for each service...")

    hello_req = req_chain.invoke(
        requirements_prompt.format_prompt(
            service_name="hello-service",
            code=state["hello_code"],
        )
    )
    print(f"    hello-service  requirements:\n      {hello_req.requirements.replace(chr(10), chr(10) + '      ')}")

    caller_req = req_chain.invoke(
        requirements_prompt.format_prompt(
            service_name="caller-service",
            code=state["caller_code"],
        )
    )
    print(f"    caller-service requirements:\n      {caller_req.requirements.replace(chr(10), chr(10) + '      ')}")

    return {
        "hello_requirements":  strip_fences(hello_req.requirements),
        "caller_requirements": strip_fences(caller_req.requirements),
    }


# ──────────────────────────────────────────────────────────────────────
# AGENT 3 – DOCKERFILE GENERATOR
# ──────────────────────────────────────────────────────────────────────

docker_prompt = ChatPromptTemplate.from_template("""
Generate an optimized Dockerfile for this Flask microservice.

Requirements:
- Base image : python:3.10-slim
- WORKDIR    : /app
- COPY requirements.txt and RUN pip install
- COPY app.py
- Expose port 5000
- Use gunicorn as the production WSGI server

Python source code:
{code}

Pinned requirements.txt content:
{requirements}
""")


def generate_dockerfiles(state: DevOpsState) -> dict:
    """Node 3 — Generate Dockerfiles for both services (informed by requirements.txt)."""
    print("\n🐳  [Node 3] Generating Dockerfiles...")

    hello_docker = docker_chain.invoke(
        docker_prompt.format_prompt(
            code=state["hello_code"],
            requirements=state["hello_requirements"],
        )
    )
    caller_docker = docker_chain.invoke(
        docker_prompt.format_prompt(
            code=state["caller_code"],
            requirements=state["caller_requirements"],
        )
    )
    return {
        "hello_docker":  strip_fences(hello_docker.dockerfile),
        "caller_docker": strip_fences(caller_docker.dockerfile),
    }


# ──────────────────────────────────────────────────────────────────────
# AGENT 4 – KUBERNETES MANIFEST GENERATOR
# ──────────────────────────────────────────────────────────────────────

k8s_prompt = ChatPromptTemplate.from_template("""
Generate Kubernetes YAML manifests.

Requirements:
- Deployment + ClusterIP Service for hello-service
- Deployment + ClusterIP Service for caller-service
- Proper label selectors
- Port 5000 on both
- caller-service reaches hello-service via DNS name hello-service

Return valid multi-document YAML separated by ---.
""")


def generate_k8s(state: DevOpsState) -> dict:
    """Node 4 — Generate Kubernetes deployment + service manifests."""
    print("\n☸️   [Node 4] Generating Kubernetes manifests...")
    manifest = k8s_chain.invoke(k8s_prompt.format_prompt())
    return {"k8s_manifest": strip_fences(manifest.manifest)}


# ──────────────────────────────────────────────────────────────────────
# AGENT 5 – KUBERNETES VALIDATOR
# ──────────────────────────────────────────────────────────────────────

validator_prompt = ChatPromptTemplate.from_template("""
You are a Kubernetes YAML validator.

Check for:
- Syntax issues
- Port mismatches
- Selector mismatches
- Service name errors
- Inter-service communication correctness

YAML:
{manifest}

Return:
- VALID or INVALID
- List of required fixes if INVALID
""")


def validate_k8s(state: DevOpsState) -> dict:
    """Node 5 — Validate the generated Kubernetes manifest."""
    print("\n🔍  [Node 5] Validating Kubernetes manifests...")
    result = validator_llm.invoke(
        validator_prompt.format_prompt(manifest=state["k8s_manifest"])
    )
    return {"validation_report": result.content}


# ──────────────────────────────────────────────────────────────────────
# AGENT 6 – FILE SCAFFOLDER
# ──────────────────────────────────────────────────────────────────────

def scaffold_files(state: DevOpsState) -> dict:
    """
    Node 6 — Write ALL generated artefacts to disk, including requirements.txt.

    Folder layout
    ─────────────
    {base_path}/
    ├── hello-service/
    │   ├── app.py
    │   ├── requirements.txt    <- NEW
    │   └── Dockerfile
    ├── caller-service/
    │   ├── app.py
    │   ├── requirements.txt    <- NEW
    │   └── Dockerfile
    ├── k8s/
    │   └── manifests.yaml
    └── validation_report.txt

    Every path is logged to state['created_files'].
    Any I/O errors are appended to state['errors'] (non-fatal).
    """
    print("\n🗂️   [Node 6] Scaffolding files on disk...")
    base = state.get("base_path", OUTPUT_DIR)

    hello_dir  = os.path.join(base, "hello-service")
    caller_dir = os.path.join(base, "caller-service")
    k8s_dir    = os.path.join(base, "k8s")

    # ── directories ───────────────────────────────────────────────────
    state = create_folder(hello_dir,  state)
    state = create_folder(caller_dir, state)
    state = create_folder(k8s_dir,    state)

    # ── hello-service ─────────────────────────────────────────────────
    state = create_file(os.path.join(hello_dir, "app.py"),           state["hello_code"],         state)
    state = create_file(os.path.join(hello_dir, "requirements.txt"), state["hello_requirements"],  state)  # <- NEW
    state = create_file(os.path.join(hello_dir, "Dockerfile"),       state["hello_docker"],        state)

    # ── caller-service ────────────────────────────────────────────────
    state = create_file(os.path.join(caller_dir, "app.py"),           state["caller_code"],         state)
    state = create_file(os.path.join(caller_dir, "requirements.txt"), state["caller_requirements"], state)  # <- NEW
    state = create_file(os.path.join(caller_dir, "Dockerfile"),       state["caller_docker"],       state)

    # ── k8s + report ──────────────────────────────────────────────────
    state = create_file(os.path.join(k8s_dir, "manifests.yaml"),          state["k8s_manifest"],      state)
    state = create_file(os.path.join(base,    "validation_report.txt"),   state["validation_report"], state)

    total_files = sum(1 for p in state["created_files"] if p.startswith("[FILE]"))
    total_dirs  = sum(1 for p in state["created_files"] if p.startswith("[DIR]"))
    print(f"\n    ✅  Scaffold complete — {total_dirs} folders, {total_files} files written.")

    return {"created_files": state["created_files"], "errors": state["errors"]}


# ──────────────────────────────────────────────────────────────────────
# AGENT 7 – DOCKER COMPOSE GENERATOR
# ──────────────────────────────────────────────────────────────────────

compose_prompt = ChatPromptTemplate.from_template("""
Generate a production-ready docker-compose.yml for two Flask microservices.

hello-service Dockerfile:
{hello_docker}

caller-service Dockerfile:
{caller_docker}

Requirements:
- version: "3.9"
- service names      : hello-service, caller-service
- build contexts     : ./hello-service  and  ./caller-service
- port mappings      : hello-service  5001:5000
                       caller-service 5002:5000
- caller-service depends_on hello-service
- shared bridge network called microservices-net
- restart: unless-stopped on both services
- healthcheck on hello-service: GET /hello every 30 s, timeout 10 s, retries 3
- environment variable SERVICE_NAME set to the service name on each container

Return only the raw YAML in the compose_yaml field — no markdown fences.
""")


def generate_docker_compose(state: DevOpsState) -> dict:
    """
    Node 7 — Generate docker-compose.yml via LLM and write it to disk.

    DevOpsState fields updated
    --------------------------
    docker_compose_yml : raw YAML string
    created_files      : compose file path appended
    errors             : any write errors appended
    """
    print("\n📦  [Node 7] Generating docker-compose.yml...")

    result = compose_chain.invoke(
        compose_prompt.format_prompt(
            hello_docker=state["hello_docker"],
            caller_docker=state["caller_docker"],
        )
    )

    compose_content = strip_fences(result.compose_yaml)
    compose_path    = os.path.join(state.get("base_path", OUTPUT_DIR), "docker-compose.yml")
    state = create_file(compose_path, compose_content, state)
    print(f"    docker-compose.yml written -> {compose_path}")

    return {
        "docker_compose_yml": compose_content,
        "created_files":      state["created_files"],
        "errors":             state["errors"],
    }


# ──────────────────────────────────────────────────────────────────────
# AGENT 8 – DOCKER CONTAINER RUNNER
# ──────────────────────────────────────────────────────────────────────

def run_docker_containers(state: DevOpsState) -> dict:
    """
    Node 8 — Build images and start containers with docker compose.

    Steps
    -----
    1. docker compose build  — build images (uses requirements.txt + Dockerfiles)
    2. docker compose up -d  — start in detached mode
    3. sleep HEALTHCHECK_DELAY seconds
    4. docker compose ps     — display running status

    DevOpsState fields updated
    --------------------------
    docker_status : "started" | "failed" | "skipped"
    docker_logs   : all CLI output lines
    errors        : docker errors (non-fatal)
    """
    print("\n🚢  [Node 8] Building and starting Docker containers...")

    if not DOCKER_COMPOSE_UP:
        print("    DOCKER_COMPOSE_UP=False — skipping container startup.")
        return {
            "docker_status": "skipped",
            "docker_logs":   state["docker_logs"],
            "errors":        state["errors"],
        }

    base = state.get("base_path", OUTPUT_DIR)

    # Step 1: build
    print("\n  Step 1/3 — docker compose build...")
    ok, state = _run_cmd(["docker", "compose", "build"], cwd=base, state=state)
    if not ok:
        state["errors"].append("docker compose build failed — see docker_logs.")
        return {"docker_status": "failed", "docker_logs": state["docker_logs"], "errors": state["errors"]}

    # Step 2: start
    print("\n  Step 2/3 — docker compose up -d...")
    ok, state = _run_cmd(["docker", "compose", "up", "-d"], cwd=base, state=state)
    if not ok:
        state["errors"].append("docker compose up failed — see docker_logs.")
        return {"docker_status": "failed", "docker_logs": state["docker_logs"], "errors": state["errors"]}

    # Step 3: wait + inspect
    print(f"\n  Step 3/3 — Waiting {HEALTHCHECK_DELAY}s then checking status...")
    time.sleep(HEALTHCHECK_DELAY)
    _run_cmd(["docker", "compose", "ps"], cwd=base, state=state)

    state["docker_logs"].append("Containers running. Endpoints:")
    state["docker_logs"].append("  hello-service  -> http://localhost:5001/hello")
    state["docker_logs"].append("  caller-service -> http://localhost:5002")

    print("\n    ✅  Containers started successfully!")
    print("    hello-service  -> http://localhost:5001/hello")
    print("    caller-service -> http://localhost:5002")

    return {
        "docker_status": "started",
        "docker_logs":   state["docker_logs"],
        "errors":        state["errors"],
    }


# ──────────────────────────────────────────────────────────────────────
# BUILD LANGGRAPH FLOW
# ──────────────────────────────────────────────────────────────────────
#
#   generate_services
#         |
#   generate_requirements    <- NEW: LLM generates requirements.txt per service
#         |
#   generate_dockerfiles     <- informed by requirements.txt
#         |
#   generate_k8s
#         |
#   validate_k8s
#         |
#   scaffold_files           <- writes app.py + requirements.txt + Dockerfile
#         |
#   generate_docker_compose
#         |
#   run_docker_containers
#         |
#        END
#
# ──────────────────────────────────────────────────────────────────────

builder = StateGraph(DevOpsState)

builder.add_node("generate_services",       generate_services)
builder.add_node("generate_requirements",   generate_requirements)    # <- NEW
builder.add_node("generate_dockerfiles",    generate_dockerfiles)
builder.add_node("generate_k8s",            generate_k8s)
builder.add_node("validate_k8s",            validate_k8s)
builder.add_node("scaffold_files",          scaffold_files)
builder.add_node("generate_docker_compose", generate_docker_compose)
builder.add_node("run_docker_containers",   run_docker_containers)

builder.set_entry_point("generate_services")

builder.add_edge("generate_services",       "generate_requirements")   # <- NEW
builder.add_edge("generate_requirements",   "generate_dockerfiles")    # <- NEW
builder.add_edge("generate_dockerfiles",    "generate_k8s")
builder.add_edge("generate_k8s",            "validate_k8s")
builder.add_edge("validate_k8s",            "scaffold_files")
builder.add_edge("scaffold_files",          "generate_docker_compose")
builder.add_edge("generate_docker_compose", "run_docker_containers")
builder.add_edge("run_docker_containers",   END)

app = builder.compile()

# ──────────────────────────────────────────────────────────────────────
# RUN SYSTEM
# ──────────────────────────────────────────────────────────────────────

result = app.invoke({
    "messages":            [HumanMessage(content="Build DevOps system")],
    # code artefacts
    "hello_code":          "",
    "caller_code":         "",
    "hello_requirements":  "",   # <- NEW
    "caller_requirements": "",   # <- NEW
    "hello_docker":        "",
    "caller_docker":       "",
    "k8s_manifest":        "",
    "validation_report":   "",
    # scaffolding
    "base_path":           OUTPUT_DIR,
    "created_files":       [],
    "errors":              [],
    # docker runtime
    "docker_compose_yml":  "",
    "docker_status":       "pending",
    "docker_logs":         [],
})

# ──────────────────────────────────────────────────────────────────────
# PRINT OUTPUTS
# ──────────────────────────────────────────────────────────────────────

SEP = "=" * 60

print(f"\n{SEP}\n  HELLO SERVICE — app.py\n{SEP}")
print(result["hello_code"])

print(f"\n{SEP}\n  HELLO SERVICE — requirements.txt\n{SEP}")
print(result["hello_requirements"])

print(f"\n{SEP}\n  HELLO SERVICE — Dockerfile\n{SEP}")
print(result["hello_docker"])

print(f"\n{SEP}\n  CALLER SERVICE — app.py\n{SEP}")
print(result["caller_code"])

print(f"\n{SEP}\n  CALLER SERVICE — requirements.txt\n{SEP}")
print(result["caller_requirements"])

print(f"\n{SEP}\n  CALLER SERVICE — Dockerfile\n{SEP}")
print(result["caller_docker"])

print(f"\n{SEP}\n  KUBERNETES MANIFEST\n{SEP}")
print(result["k8s_manifest"])

print(f"\n{SEP}\n  VALIDATION REPORT\n{SEP}")
print(result["validation_report"])

print(f"\n{SEP}\n  DOCKER-COMPOSE.YML\n{SEP}")
print(result["docker_compose_yml"])

print(f"\n{SEP}\n  DOCKER STATUS : {result['docker_status'].upper()}\n{SEP}")
for line in result["docker_logs"]:
    print(f"  {line}")

print(f"\n{SEP}\n  FILE MANIFEST\n{SEP}")
for entry in result["created_files"]:
    print(f"  {entry}")

if result["errors"]:
    print(f"\n  Errors ({len(result['errors'])}):")
    for err in result["errors"]:
        print(f"  * {err}")
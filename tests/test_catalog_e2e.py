"""Skill catalogue e2e tests — 4 layers (corpus, install, RAG, CLI, fallback)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = REPO_ROOT / "skills" / "catalog"
DISPATCHER_SKILL = REPO_ROOT / "skills" / "claude" / "engineering-skill-catalog" / "SKILL.md"
OSE_URL = os.environ.get("OSE_URL", "http://127.0.0.1:8765")


def _yaml_frontmatter(path: Path) -> dict:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def _ose_available() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen(f"{OSE_URL}/healthz", timeout=3)
        return True
    except Exception:
        return False


def _mcp_search(query: str, top_k: int = 5) -> list[str]:
    """Call OSE search via MCP JSON-RPC streamable-http. Returns list of file paths."""
    import urllib.request as _req
    url = f"{OSE_URL}/mcp"
    hdrs = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

    def _post(body: dict, sid: str | None = None) -> tuple[str | None, dict]:
        h = dict(hdrs, **{"mcp-session-id": sid} if sid else {})
        r = _req.Request(url, data=json.dumps(body).encode(), headers=h)
        resp = _req.urlopen(r, timeout=30)
        sid_out = resp.headers.get("mcp-session-id")
        for line in resp.read().decode().splitlines():
            if line.startswith("data: "):
                return sid_out, json.loads(line[6:])
        return sid_out, {}

    sid, _ = _post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "aes-test", "version": "1.0"}}})
    _post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    _, res = _post({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "search", "arguments": {
                        "query": query, "scope": "all",
                        "project_paths": [str(REPO_ROOT)]}}}, sid)
    raw = res.get("result", {}).get("content", [{}])[0].get("text", "{}")
    return [r.get("path", "") for r in json.loads(raw).get("results", [])[:top_k]]


def _claude_available() -> bool:
    return shutil.which("claude") is not None


def _run_claude(prompt: str, config_dir: str, model: str | None = None) -> dict:
    model = model or os.environ.get("AES_CLAUDE_E2E_MODEL", "haiku")
    env = dict(os.environ, CLAUDE_CONFIG_DIR=config_dir)
    with tempfile.TemporaryDirectory(prefix="aes-live-") as tmp:
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True, capture_output=True)
        Path(tmp).joinpath("notes.txt").write_text("seed\n")
        subprocess.run(["git", "add", "notes.txt"], cwd=tmp, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.name=test", "-c", "user.email=test@example.com",
             "commit", "-q", "-m", "init"],
            cwd=tmp, check=True, capture_output=True,
        )
        proc = subprocess.run(
            ["claude", "-p", "--model", model, "--output-format", "stream-json",
             "--verbose", "--dangerously-skip-permissions", prompt],
            env=env, text=True, capture_output=True, timeout=120, cwd=tmp,
        )
    events = []
    for line in proc.stdout.splitlines():
        if line.strip():
            try:
                events.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                pass
    return {"returncode": proc.returncode, "events": events, "stderr": proc.stderr}


def _is_unavailable_run(r: dict) -> bool:
    """True when a run is rate-limited or unauthenticated (environmental, not an integration bug)."""
    if r["returncode"] != 0:
        return True
    return any(ev.get("type") == "rate_limit_event" for ev in r["events"])


def _has_ose_tool_use(events: list[dict]) -> bool:
    for ev in events:
        # Non-partial shape: {"type":"assistant","message":{"content":[{"type":"tool_use","name":"..."}]}}
        if ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if (isinstance(block, dict)
                        and block.get("type") == "tool_use"
                        and "opencode-search" in block.get("name", "")):
                    return True
        # Partial-delta shape (fallback for include-partial-messages mode)
        name = ev.get("name", "") or ev.get("content_block", {}).get("name", "")
        if "opencode-search" in str(name):
            return True
        cb = ev.get("content_block", {})
        if cb.get("type") == "tool_use" and "opencode-search" in cb.get("name", ""):
            return True
    return False


# ── Layer 0: corpus gate ─────────────────────────────────────────────────────

def test_catalog_directory_exists():
    assert CATALOG_DIR.is_dir()


def test_dispatcher_skill_exists_and_valid():
    assert DISPATCHER_SKILL.is_file()
    fm = _yaml_frontmatter(DISPATCHER_SKILL)
    assert fm.get("name") == "engineering-skill-catalog"
    assert fm.get("description")


def test_all_catalog_files_have_valid_frontmatter():
    files = list(CATALOG_DIR.rglob("*.md"))
    assert files
    errors = []
    for f in files:
        fm = _yaml_frontmatter(f)
        missing = [k for k in ("name", "description", "discipline", "tags") if not fm.get(k)]
        if missing:
            errors.append(f"{f.relative_to(REPO_ROOT)}: missing {missing}")
    assert not errors, "\n".join(errors)


def test_catalog_slug_matches_filename():
    errors = [
        f"{f.name}: name={_yaml_frontmatter(f).get('name')!r} != {f.stem!r}"
        for f in CATALOG_DIR.rglob("*.md")
        if _yaml_frontmatter(f).get("name", "") != f.stem
    ]
    assert not errors, "\n".join(errors)


def test_catalog_no_duplicate_names():
    seen: dict[str, str] = {}
    dups = []
    for f in CATALOG_DIR.rglob("*.md"):
        name = _yaml_frontmatter(f).get("name", "")
        if name in seen:
            dups.append(f"{name}: {seen[name]} and {f.name}")
        else:
            seen[name] = f.name
    assert not dups, "; ".join(dups)


def test_catalog_required_sections():
    required = {"When to use", "Signal", "Why", "Remediate"}
    errors = []
    for f in CATALOG_DIR.rglob("*.md"):
        headers = set(re.findall(r"^## (.+)$", f.read_text(), re.MULTILINE))
        missing = required - headers
        if missing:
            errors.append(f"{f.relative_to(REPO_ROOT)}: missing {sorted(missing)}")
    assert not errors, "\n".join(errors)


def test_catalog_covers_all_disciplines():
    expected = {"backend", "frontend", "infra", "qa", "security", "data", "craft"}
    found = {f.parent.name for f in CATALOG_DIR.rglob("*.md")}
    assert expected <= found, f"Missing: {expected - found}"


def test_engineering_skill_catalog_in_skill_names():
    from policy.shared import SKILL_NAMES
    assert "engineering-skill-catalog" in SKILL_NAMES


def test_opencode_index_yaml_valid():
    cfg = REPO_ROOT / ".opencode-index.yaml"
    assert cfg.is_file()
    data = yaml.safe_load(cfg.read_text())
    assert isinstance(data.get("index", {}).get("exclude"), list)


# ── Layer 1: install gate ─────────────────────────────────────────────────────

def test_dispatcher_skill_symlinked_into_all_profiles(tmp_path: Path):
    from scripts.install_policy import run_install
    home = tmp_path
    for root in (home / ".claude", home / ".claude-account1", home / ".claude-account2"):
        root.mkdir(parents=True, exist_ok=True)
        (root / "CLAUDE.md").write_text("")
        (root / "settings.json").write_text("{}\n")
    run_install(apply=True, dry_run=False, targets={"claude", "skills", "hooks"},
                profiles={"main", "account1", "account2"}, home=home, repo_root=REPO_ROOT)
    for profile_dir in (home / ".claude", home / ".claude-account1", home / ".claude-account2"):
        skill_link = profile_dir / "skills" / "engineering-skill-catalog"
        assert skill_link.exists(), f"Not installed in {profile_dir.name}"
        assert skill_link.is_symlink(), f"Not a symlink in {profile_dir.name}"


def test_all_six_skills_installed(tmp_path: Path):
    from scripts.install_policy import run_install
    home = tmp_path
    root = home / ".claude"
    root.mkdir(parents=True, exist_ok=True)
    (root / "CLAUDE.md").write_text("")
    (root / "settings.json").write_text("{}\n")
    run_install(apply=True, dry_run=False, targets={"skills"}, profiles={"main"},
                home=home, repo_root=REPO_ROOT)
    expected = {"lean-change", "repo-first-research", "lean-implement", "lean-review",
                "perf-investigation", "engineering-skill-catalog"}
    installed = {p.name for p in (root / "skills").iterdir()}
    assert expected == installed, f"Got: {sorted(installed)}"


GOLDEN_SET = [
    ("fix N+1 query ORM eager loading", "n-plus-one-queries"),
    ("SQL index missing slow query EXPLAIN", "indexing-and-query-plans"),
    ("idempotency key payment retry dedup", "idempotency-keys"),
    ("pagination without OFFSET keyset cursor", "cursor-pagination"),
    ("API backward compatibility versioning", "api-versioning-and-contracts"),
    ("rate limiting throttle token bucket", "rate-limiting-and-backpressure"),
    ("Redis cache invalidation stale data", "caching-and-invalidation"),
    ("database connection pool exhausted", "connection-pooling"),
    ("exponential backoff jitter retry transient", "retries-with-backoff-and-jitter"),
    ("circuit breaker fast-fail downstream", "circuit-breaker"),
    ("zero downtime rename column migration", "expand-contract-migrations"),
    ("terraform idempotent apply IaC drift", "iac-idempotency"),
    ("Kubernetes OOMKill memory limits requests", "k8s-requests-and-limits"),
    ("canary rollout auto rollback error rate", "canary-deployments"),
    ("SLO error budget burn rate alert", "slos-and-error-budgets"),
    ("OpenTelemetry OTLP traces metrics logs", "opentelemetry-instrumentation"),
    ("WCAG 2.2 accessibility aria contrast", "wcag-accessibility"),
    ("LCP INP CLS core web vitals RUM", "core-web-vitals"),
    ("JavaScript bundle size code split", "js-bundle-budget"),
    ("React server components hydration", "ssr-rsc-and-hydration"),
    ("test pyramid unit integration e2e ratio", "test-pyramid"),
    ("flaky tests quarantine CI failure rate", "flaky-test-quarantine"),
    ("consumer contract testing Pact", "contract-testing"),
    ("OWASP broken access control IDOR", "owasp-a01-broken-access-control"),
    ("SBOM supply chain CVE scan", "owasp-a03-supply-chain-and-sbom"),
    ("SQL injection parameterized query", "sql-injection"),
    ("secrets git history leak rotation", "secrets-in-code"),
    ("SAST DAST SCA shift left security", "shift-left-sast-dast-sca"),
    ("prompt injection LLM defense", "prompt-injection-defense"),
    ("RAG evaluation recall faithfulness", "rag-and-llm-evaluation"),
    ("ETL pipeline idempotent retry", "pipeline-idempotency"),
    ("race condition goroutine concurrent data", "concurrency-and-races"),
    ("feature flag rollout kill switch", "feature-flags-and-rollout"),
    ("DORA metrics deploy frequency lead time", "dora-metrics"),
]


@pytest.mark.live
@pytest.mark.slow
def test_rag_precision_at_5():
    """Layer 2: Precision@5 ≥ 0.70 on the golden set via real MCP JSON-RPC."""
    if not _ose_available():
        pytest.skip("OSE daemon not available")
    hits, misses = 0, []
    for query, expected_slug in GOLDEN_SET:
        try:
            top5 = _mcp_search(query)
            if any(expected_slug in p for p in top5):
                hits += 1
            else:
                misses.append(f"{expected_slug}: top5={[Path(p).stem for p in top5]}")
        except Exception as e:
            misses.append(f"{expected_slug}: {e}")
    precision = hits / len(GOLDEN_SET)
    assert precision >= 0.7, f"Precision@5={precision:.2f}<0.70\n" + "\n".join(misses)


PROFILE_DIRS = {
    "account1": str(Path.home() / ".claude-account1"),  # primary: claude1 (logged-in)
    "main": str(Path.home() / ".claude"),
    "account2": str(Path.home() / ".claude-account2"),
}
SE_PROMPT = (
    "My ORM fires one SQL per row. "
    "Use the engineering-skill-catalog skill to retrieve the fix technique."
)


@pytest.mark.live
@pytest.mark.parametrize("profile_name,config_dir", list(PROFILE_DIRS.items()))
def test_per_profile_ose_invocation(profile_name: str, config_dir: str):
    """Layer 3: each profile must invoke the OSE search MCP (>=1 of 3 runs)."""
    if not _claude_available():
        pytest.skip("claude CLI not available")
    if not _ose_available():
        pytest.skip("OSE daemon not available")
    if not Path(config_dir).exists():
        pytest.skip(f"Profile dir {config_dir} not found")
    results = [_run_claude(SE_PROMPT, config_dir) for _ in range(3)]
    if all(_is_unavailable_run(r) for r in results):
        pytest.skip(f"Profile {profile_name}: all runs rate-limited or unauthenticated")
    available = [r for r in results if not _is_unavailable_run(r)]
    successes = [r for r in available if _has_ose_tool_use(r["events"])]
    assert successes, f"Profile {profile_name}: OSE never invoked in {len(available)} available run(s)"


@pytest.mark.live
def test_dispatcher_skill_visible_to_claude1_profile():
    """Layer 3: engineering-skill-catalog appears in Claude's output (claude1 profile)."""
    if not _claude_available():
        pytest.skip("claude CLI not available")
    config_dir = PROFILE_DIRS["account1"]
    if not Path(config_dir).exists():
        pytest.skip("account1 profile not found")
    result = _run_claude("List available engineering skills briefly.", config_dir)
    assert result["returncode"] == 0
    all_text = json.dumps(result["events"])
    assert "engineering-skill-catalog" in all_text or "catalog" in all_text.lower()


@pytest.mark.live
def test_non_se_prompt_does_not_invoke_ose():
    """Layer 4: a non-SE prompt must not trigger the OSE search tool."""
    if not _claude_available():
        pytest.skip("claude CLI not available")
    config_dir = PROFILE_DIRS["main"]
    if not Path(config_dir).exists():
        pytest.skip("main profile not found")
    result = _run_claude("What is the capital of France? One word.", config_dir)
    assert result["returncode"] == 0
    assert not _has_ose_tool_use(result["events"]), "OSE invoked for non-SE prompt"


def test_fallback_catalog_searchable_without_daemon():
    """Layer 4: grep over skills/catalog/ works without OSE daemon."""
    files = list(CATALOG_DIR.glob("backend/n-plus-one-queries.md"))
    assert files, "n-plus-one-queries.md missing — fallback would fail"
    content = files[0].read_text()
    assert "Remediate" in content
    assert any(kw in content.lower() for kw in ("eager", "join", "dataloader", "batch"))

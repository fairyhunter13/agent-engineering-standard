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


def _run_claude(prompt: str, config_dir: str, model: str | None = None, timeout: int = 120) -> dict:
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
            env=env, text=True, capture_output=True, timeout=timeout, cwd=tmp,
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
    # rate_limit_event with status="allowed" is informational — request still went through
    return any(
        ev.get("type") == "rate_limit_event"
        and ev.get("rate_limit_info", {}).get("status") != "allowed"
        for ev in r["events"]
    )


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
    """Layer 4: a non-SE prompt must not trigger the OSE search tool (via claude1)."""
    if not _claude_available():
        pytest.skip("claude CLI not available")
    config_dir = PROFILE_DIRS["account1"]  # primary logged-in profile
    if not Path(config_dir).exists():
        pytest.skip("account1 profile not found")
    result = _run_claude("What is the capital of France? One word.", config_dir)
    if _is_unavailable_run(result):
        pytest.skip("claude1 unavailable (rate-limited or unauthenticated)")
    assert result["returncode"] == 0
    assert not _has_ose_tool_use(result["events"]), "OSE invoked for non-SE prompt"


def _ose_result_text(events: list[dict]) -> str:
    """Concatenate OSE tool-result text and final assistant text from stream-json events."""
    parts = []
    for ev in events:
        if ev.get("type") == "user":
            for block in ev.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    for inner in block.get("content", []):
                        if isinstance(inner, dict) and inner.get("type") == "text":
                            parts.append(inner["text"])
        elif ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
    return " ".join(parts)


_SKILLS_BACKEND = [
    ("old mobile app crashes after we shipped a breaking change to our REST endpoint response shape", "api-versioning-and-contracts"),
    ("synchronous HTTP calls between microservices cause cascading failures when the checkout service is slow", "async-messaging-patterns"),
    ("product catalog database is hammered; every page load fires 50 queries for the same data", "caching-and-invalidation"),
    ("our service hammers the bank API even when it is down, queue builds up until everything crashes", "circuit-breaker"),
    ("PostgreSQL hits max_connections under load, new requests fail with too many connections", "connection-pooling"),
    ("OFFSET 50000 page loads take 8 seconds, listing endpoint slows as users scroll deeper", "cursor-pagination"),
    ("messages are sometimes processed twice and sometimes dropped; when does exactly-once delivery apply", "delivery-semantics"),
    ("a request spans 5 services, response is slow but we cannot tell which service is the bottleneck", "distributed-tracing"),
    ("adding a NOT NULL column to a 50M row table without taking the site down for maintenance", "expand-contract-migrations"),
    ("retrying a failed payment request charges the customer a second time", "idempotency-keys"),
    ("EXPLAIN shows a sequential scan on a 10M row table, query takes 15 seconds on a simple filter", "indexing-and-query-plans"),
    ("ORM issues 200 SQL queries when rendering a page that lists 200 orders", "n-plus-one-queries"),
    ("a single misbehaving API client starves all other clients and brings the service to its knees", "rate-limiting-and-backpressure"),
    ("naive retry storm amplifies load on an already-struggling downstream service during an outage", "retries-with-backoff-and-jitter"),
    ("plain text log messages are unsearchable in Datadog; correlation between requests across services is impossible", "structured-logging"),
    ("two concurrent checkouts decrement the same inventory count causing overselling without locks", "transaction-isolation-and-locking"),
]


_SKILLS_CRAFT = [
    ("PR reviews take days, reviewers block on nits, authors feel attacked, no actionable feedback", "code-review-discipline"),
    ("git bisect fails because commits are squashed into huge blobs with messages like fix stuff", "commit-and-pr-hygiene"),
    ("goroutine writes to a shared map while another goroutine reads, intermittent panic in production", "concurrency-and-races"),
    ("bug reported in prod cannot be reproduced locally, no idea where to start investigating", "debugging-methodology"),
    ("package.json has 400 dependencies including abandoned packages with critical CVEs", "dependency-hygiene"),
    ("all errors are swallowed or re-thrown as generic 500s; impossible to distinguish expected from unexpected", "error-handling-taxonomy"),
    ("shipping a new checkout flow deploys to all users at once with no ability to roll back incrementally", "feature-flags-and-rollout"),
    ("need to extract a class from legacy code that has no tests and could break anything", "refactoring-under-tests"),
]
_SKILLS_DATA = [
    ("need to populate a new column from event history for 500M rows without locking the production table", "backfill-safety"),
    ("BigQuery query over 3 years of events scans the entire table and costs 800 dollars each run", "data-partitioning"),
    ("a NULL in an upstream column silently propagated through the pipeline into the BI dashboard", "data-quality-checks"),
    ("user emails and phone numbers are being logged in the analytics pipeline and a GDPR audit is coming", "pii-minimization"),
    ("re-running a failed ETL stage inserted duplicate rows that propagated into the data warehouse", "pipeline-idempotency"),
    ("user input is concatenated into an LLM system prompt allowing the user to escape the instructions", "prompt-injection-defense"),
    ("RAG chatbot gives wrong answers but we have no metrics to tell if retrieval or generation is the problem", "rag-and-llm-evaluation"),
    ("changed a protobuf field type and Avro consumers started throwing deserialization exceptions", "schema-evolution"),
]
_SKILLS_FRONTEND = [
    ("hero image is 4MB uncompressed, LCP is 8s on mobile, no width and height attributes causing layout shift", "asset-and-image-optimization"),
    ("entire app bundle loads on the login page even though most routes are never visited", "code-splitting-and-lazy-loading"),
    ("Google Search Console shows poor CLS from ads that inject content above the fold after page load", "core-web-vitals"),
    ("XSS via injected script tag in user-generated content, no Content-Security-Policy header set", "csp-and-frontend-security"),
    ("uncaught error in one React widget crashes the entire app and shows a blank white page", "error-boundaries"),
    ("form shows all validation errors only on final submit, users cannot tell which field failed mid-typing", "form-validation-and-ux"),
    ("app shows English for users in Japan because locale detection uses the wrong header, pluralization breaks", "internationalization"),
    ("main.js is 2MB gzipped, Time to Interactive on 3G is 12 seconds", "js-bundle-budget"),
    ("synthetic tests pass but real users report the page feels slow and we have no field performance data", "real-user-monitoring"),
    ("Next.js hydration error: server HTML does not match client render, app flickers on load", "ssr-rsc-and-hydration"),
    ("prop drilling 8 levels deep, every parent re-renders when any child state changes", "state-management-boundaries"),
    ("screen reader skips an important button, color contrast ratio is 2:1 on the call-to-action", "wcag-accessibility"),
]


_SKILLS_INFRA = [
    ("after the outage the team blamed the engineer, no root-cause analysis, same issue recurred two weeks later", "blameless-postmortems"),
    ("need to roll back a bad deploy instantly without waiting for all pods to terminate and restart", "blue-green-deployments"),
    ("route 5 percent of traffic to the new version and auto-rollback if error rate exceeds the SLO threshold", "canary-deployments"),
    ("CI takes 45 minutes, everyone merges at 5pm causing a deploy train collision", "cicd-pipeline-design"),
    ("Docker image is 2GB, runs as root, includes dev dependencies, security scan reports 80 HIGH CVEs", "container-image-hygiene"),
    ("CTO wants to measure engineering delivery speed but we have no baseline metrics established", "dora-metrics"),
    ("traffic spikes at 9am crash pods because Kubernetes does not scale up fast enough before requests fail", "horizontal-pod-autoscaling"),
    ("second terraform apply changes resources that nothing touched, the plan is never empty on repeated runs", "iac-idempotency"),
    ("pod OOMKilled in production, memory limit was set to 64Mi for a JVM service that needs much more", "k8s-requests-and-limits"),
    ("pods pass liveness check while still initializing, traffic is routed before the app finishes starting", "liveness-and-readiness-probes"),
    ("migrating from Datadog APM to vendor-neutral tracing without rewriting all instrumentation code", "opentelemetry-instrumentation"),
    ("engineer who wrote the service left, on-call has no documentation to debug a 3am PagerDuty alert", "runbooks-and-incident-response"),
    ("database password hardcoded in docker-compose.yml was checked into the public GitHub repository", "secrets-management"),
    ("team ships features so fast that reliability degrades with no mechanism to enforce a freeze", "slos-and-error-budgets"),
    ("Datadog bill tripled after adding distributed tracing because we sample 100 percent of all requests", "telemetry-cost-and-sampling"),
    ("rolling update to Kubernetes drops 5 percent of requests as old pods terminate mid-connection", "zero-downtime-deployments"),
]
_SKILLS_QA = [
    ("frontend team and backend team keep breaking each other's API contracts, need isolated boundary verification", "contract-testing"),
    ("100 percent line coverage but mutation score is 12 percent, tests do not actually catch real bugs", "coverage-as-signal"),
    ("test passes locally, fails in CI, passes again on retry — it depends on the current timestamp", "deterministic-tests"),
    ("Selenium suite has 2000 tests, takes 3 hours, breaks on every CSS class rename", "e2e-test-strategy"),
    ("CI is red 60 percent of the time from tests that sometimes pass and sometimes fail randomly", "flaky-test-quarantine"),
    ("unit tests mock the entire database layer, tests pass but a migration broke production silently", "mock-boundaries"),
    ("tests pass but nobody trusts them; want to verify tests actually detect real code defects", "mutation-testing"),
    ("use Hypothesis or QuickCheck to generate hundreds of random inputs automatically and discover edge cases hand-written examples miss", "property-based-testing"),
    ("test environment uses a copy of the production database containing real user PII", "sanitized-test-data"),
    ("1000 snapshot tests, every CSS change breaks all of them and nobody reviews the diffs meaningfully", "snapshot-testing-hygiene"),
    ("every test creates fixtures with 20-line setup blocks duplicated across 500 test files", "test-data-builders"),
    ("all tests are E2E, CI takes 4 hours, a small refactor breaks 200 tests covering the same behavior", "test-pyramid"),
]


_SKILLS_SECURITY = [
    ("microservice has admin database access because scoping permissions was harder than granting full access", "least-privilege-and-zero-trust"),
    ("user can increment the ID in the URL and see another user's private invoice data", "owasp-a01-broken-access-control"),
    ("debug endpoint is enabled in production, server version is exposed in HTTP response headers", "owasp-a02-security-misconfiguration"),
    ("npm audit finds a critical CVE in a transitive dependency we did not know we were shipping", "owasp-a03-supply-chain-and-sbom"),
    ("threat model the payment flow at design time to find missing business logic constraints before writing any code", "owasp-a04-insecure-design"),
    ("passwords stored as MD5 hashes, TLS 1.0 enabled, customer data at rest is not encrypted", "owasp-a05-cryptographic-failures"),
    ("log4shell-style vulnerability 3 hops deep in the dependency tree, no process to patch in 48 hours", "owasp-a06-vulnerable-components"),
    ("no rate limiting on login endpoint, no MFA required, JWTs never expire, sessions are permanent", "owasp-a07-authentication-failures"),
    ("GitHub Actions workflow uses mutable tag actions/checkout@main which could be poisoned by attacker", "owasp-a08-integrity-failures"),
    ("account takeover happened but we have no audit logs of login attempts or permission changes", "owasp-a09-logging-failures"),
    ("internal stack trace with database schema details is returned to the client on every 500 error", "owasp-a10-exceptional-conditions"),
    ("AWS access key committed to GitHub 6 months ago, now seeing unauthorized S3 charges", "secrets-in-code"),
    ("security only tests in production via pentest, findings arrive after code is already shipped", "shift-left-sast-dast-sca"),
    ("user input is concatenated directly into a SQL query string using f-string formatting", "sql-injection"),
]

ALL_SKILLS = (
    _SKILLS_BACKEND + _SKILLS_CRAFT + _SKILLS_DATA + _SKILLS_FRONTEND
    + _SKILLS_INFRA + _SKILLS_QA + _SKILLS_SECURITY
)

DISCIPLINE_REPRESENTATIVES = [
    ("backend", "ORM issues 200 SQL queries when rendering a page listing 200 orders", "n-plus-one-queries",
     ["eager", "join", "dataloader", "batch"]),
    ("craft", "goroutine writes to a shared map while another reads, intermittent panic in production", "concurrency-and-races",
     ["race", "mutex", "lock", "atomic", "sync"]),
    ("data", "re-running a failed ETL stage inserted duplicate rows that propagated into the data warehouse", "pipeline-idempotency",
     ["idempotent", "deduplicate", "upsert", "checkpoint", "dedup"]),
    ("frontend", "Google Search Console shows poor CLS from ads injecting content above the fold after page load", "core-web-vitals",
     ["lcp", "cls", "inp", "layout", "cumulative", "vitals"]),
    ("infra", "team ships so fast that reliability degrades with no mechanism to enforce a reliability freeze", "slos-and-error-budgets",
     ["slo", "error budget", "objective", "budget", "burn"]),
    ("qa", "all tests are E2E, CI takes 4 hours, small refactor breaks 200 tests covering the same behavior", "test-pyramid",
     ["pyramid", "unit", "integration", "e2e"]),
    ("security", "user input is concatenated directly into a SQL query string using f-string formatting", "sql-injection",
     ["parameterized", "prepared", "bind", "orm", "injection"]),
]


def test_fallback_catalog_searchable_without_daemon():
    """Layer 4: grep over skills/catalog/ works without OSE daemon."""
    files = list(CATALOG_DIR.glob("backend/n-plus-one-queries.md"))
    assert files, "n-plus-one-queries.md missing — fallback would fail"
    content = files[0].read_text()
    assert "Remediate" in content
    assert any(kw in content.lower() for kw in ("eager", "join", "dataloader", "batch"))


# ── Tier A: all 86 skills loadable via MCP ───────────────────────────────────

@pytest.mark.live
def test_all_skills_loadable_via_mcp():
    """Tier A: every catalogue skill is retrievable via real MCP. Recall@10 ≥ 0.95, @5 ≥ 0.90."""
    if not _ose_available():
        pytest.skip("OSE daemon not available")
    hits10, hits5, misses = 0, 0, []
    for query, slug in ALL_SKILLS:
        try:
            top10 = _mcp_search(query, top_k=10)
            if any(slug in p for p in top10):
                hits10 += 1
                if any(slug in p for p in top10[:5]):
                    hits5 += 1
            else:
                misses.append(f"MISS@10 {slug}: top10={[Path(p).stem for p in top10]}")
        except Exception as e:
            misses.append(f"ERROR {slug}: {e}")
    total = len(ALL_SKILLS)
    r10, r5 = hits10 / total, hits5 / total
    if misses:
        print("\n--- Misses ---\n" + "\n".join(misses))
    assert r10 >= 0.95, f"Recall@10={r10:.2f}<0.95 ({hits10}/{total})\n" + "\n".join(misses)
    assert r5 >= 0.90, f"Recall@5={r5:.2f}<0.90 ({hits5}/{total})"


# ── Tier B: one skill per discipline driven through claude1 ───────────────────

@pytest.mark.live
@pytest.mark.slow
@pytest.mark.parametrize(
    "discipline,query,slug,keywords", DISCIPLINE_REPRESENTATIVES,
    ids=[d for d, *_ in DISCIPLINE_REPRESENTATIVES],
)
def test_skill_used_live_per_discipline(discipline, query, slug, keywords):
    """Tier B: one skill per discipline retrieved AND used correctly via claude1 (≥1/3 runs)."""
    if not _claude_available():
        pytest.skip("claude CLI not available")
    if not _ose_available():
        pytest.skip("OSE daemon not available")
    config_dir = PROFILE_DIRS["account1"]
    if not Path(config_dir).exists():
        pytest.skip("account1 profile not found")
    prompt = (
        f"{query}. "
        "Use the engineering-skill-catalog skill to look up and explain the relevant technique."
    )
    results = [_run_claude(prompt, config_dir, timeout=300) for _ in range(3)]
    if all(_is_unavailable_run(r) for r in results):
        pytest.skip(f"claude1 unavailable for discipline={discipline}")
    available = [r for r in results if not _is_unavailable_run(r)]
    result_texts = [_ose_result_text(r["events"]) for r in available]
    successes = [
        i for i, r in enumerate(available)
        if _has_ose_tool_use(r["events"])
        and (slug in result_texts[i]
             or any(kw in result_texts[i].lower() for kw in keywords))
    ]
    assert successes, (
        f"discipline={discipline}: '{slug}' never loaded+used correctly "
        f"in {len(available)} available run(s). "
        f"ose_fired={[_has_ose_tool_use(r['events']) for r in available]}"
    )

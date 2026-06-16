# >>> agent-engineering-standard:claude-launchers >>>
# Claude launchers (managed by agent-engineering-standard)
# Preserves the current shared-history multi-profile model.
function claude() {
    command claude --model "opusplan" --dangerously-skip-permissions "$@"
}

function claude1() {
    CLAUDE_CONFIG_DIR="$HOME/.claude-account1" claude "$@"
}

function claude2() {
    CLAUDE_CONFIG_DIR="$HOME/.claude-account2" claude "$@"
}
# <<< agent-engineering-standard:claude-launchers <<<

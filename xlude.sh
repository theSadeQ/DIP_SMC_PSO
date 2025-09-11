#!/usr/bin/env bash
# xlude.sh — PR/CI workflow helper (dry-run by default)
# Purpose: Automate tasks for PR #14/#15, CI gating (#16/#17), backup refs,
#          cleanup of merged branches, and rollback via merge commit.
# Safety:  - Dry-run unless --apply
#          - Force push only with --force-with-lease
#          - Creates backup branches before risky ops
# Requires: git, gh (GitHub CLI), jq; pytest for tests

set -euo pipefail
IFS=$'\n\t'

VERSION="0.1.0"

# ---------------------------- Global Defaults ----------------------------- #
APPLY=0
REPO="."
MERGE_METHOD="merge"     # merge|squash|rebase (for gh pr merge)
STRATEGY="rebase"        # rebase|merge (to sync PR14 with main)
FORCE_WITH_LEASE=0
AUTO_MERGE=1

DEFAULT_CLEANUP_BRANCHES=(
  c04/factory-indent-fix
  c04/tests-integration
  c04_shim_logger_fix2
)

PR14_NUM=14
PR15_NUM=15
CI_GATE_PRS=(16 17)

# ----------------------------- Utilities --------------------------------- #
log(){ printf "==> %s\n" "$*" >&2; }
warn(){ printf "!!  %s\n" "$*" >&2; }
die(){ printf "ERROR: %s\n" "$*" >&2; exit 1; }
have(){ command -v "$1" >/dev/null 2>&1; }
req(){ for c in "$@"; do have "$c" || die "Missing required tool: $c"; done; }

# run: read-only commands execute regardless of dry-run
run(){ eval "$@"; }

# doit: only executes when APPLY=1; otherwise prints the command to run
doit(){
  if [[ $APPLY -eq 1 ]]; then
    eval "$@"
  else
    printf "[dry-run] %s\n" "$*"
  fi
}

ensure_repo(){
  [[ -d "$REPO/.git" ]] || die "No .git found at REPO=$REPO"
  cd "$REPO"
}

git_current_branch(){
  git rev-parse --abbrev-ref HEAD
}

create_backup_branch(){
  local base="${1:-$(git_current_branch)}"
  local ts
  ts="$(date +%Y%m%d%H%M%S)"
  local backup="backup/${base//\//-}-$ts"
  log "Creating backup branch: $backup"
  doit "git branch \"$backup\" \"$base\""
}

print_tools(){
  log "Tools:"
  for t in git gh jq pytest; do
    if have "$t"; then
      printf "  - %-7s %s\n" "$t" "$("$t" --version 2>&1 | head -n1)"
    else
      printf "  - %-7s MISSING\n" "$t"
    fi
  done
}

usage(){
  cat <<'EOF'
xlude — PR/CI workflow helper (dry-run by default)

USAGE:
  xlude.sh [--repo PATH] [--apply] [global flags] <command> [args]

GLOBAL FLAGS:
  --repo PATH                Path to git repo (default: .)
  --apply                    Execute writes (default: dry-run)
  --merge-method {merge|squash|rebase}   (default: merge)
  --strategy {rebase|merge}  Strategy for PR14 sync with main (default: rebase)
  --force-with-lease         Allow force-with-lease on push (only when needed)
  --no-auto-merge            Disable gh auto-merge

COMMANDS:
  check-tools                        Print required tool versions
  pr14 [--strategy ...]              Handle PR #14 (c04/finish-line) conflicts, sync with main, test, push, watch CI, merge.
  pr15                                Review PR #15 (bp-types-doctests): doctests/type hints, ensure no runtime changes (heuristics), merge.
  backup-refs                         Show backup refs and reflog for rollback sanity checks.
  ci-gate [--prs 16,17]               Confirm recent merged PRs have green checks; print merge_commit_sha and statuses.
  cleanup-branches [names...]         Delete merged remote branches (defaults provided).
  rollback (--pr N | --sha SHA)       Revert a merged PR by merge commit (-m 1) and open a revert PR.

EXAMPLES:
  ./xlude.sh pr14
  ./xlude.sh --apply --strategy rebase pr14
  ./xlude.sh pr15
  ./xlude.sh ci-gate --prs 16,17
  ./xlude.sh cleanup-branches
  ./xlude.sh --apply rollback --pr 16

Safety:
  - Dry-run prints commands; add --apply to actually execute.
  - Force pushes require --force-with-lease.
EOF
}

parse_global_flags(){
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --repo) REPO="${2:?}"; shift 2;;
      --apply) APPLY=1; shift;;
      --merge-method) MERGE_METHOD="${2:?}"; shift 2;;
      --strategy) STRATEGY="${2:?}"; shift 2;;
      --force-with-lease) FORCE_WITH_LEASE=1; shift;;
      --no-auto-merge) AUTO_MERGE=0; shift;;
      -h|--help) usage; exit 0;;
      *) break;;
    esac
  done
  printf '%q ' "$@"
}

cmd_check_tools(){
  print_tools
}

cmd_backup_refs(){
  ensure_repo
  log "Backup refs (if any):"
  run "git show-ref | grep -i backup || git for-each-ref refs/backup || true"
  echo
  log "Recent reflog (top 50):"
  run "git reflog --date=iso | head -n 50"
}

watch_checks_and_merge(){
  local pr="$1"
  log "Watching PR #$pr checks..."
  if have gh; then
    run "gh pr checks $pr --watch --interval 15 || true"
    if [[ $AUTO_MERGE -eq 1 ]]; then
      log "Attempting auto-merge when checks are green..."
      doit "gh pr merge $pr --${MERGE_METHOD} --auto"
    else
      log "Auto-merge disabled; manual gh pr merge suggested."
    fi
  else
    warn "gh not installed; cannot watch checks or merge automatically."
  fi
}

cmd_pr14(){
  ensure_repo
  req git
  have gh || warn "gh not installed; will operate via git only."
  local branch="c04/finish-line"

  log "Fetching all remotes..."
  doit "git fetch --all --prune"

  if have gh; then
    log "Checking out PR #$PR14_NUM (${branch}) via gh..."
    doit "gh pr checkout $PR14_NUM"
  else
    log "Checking out branch ${branch} via git..."
    doit "git checkout ${branch}"
  fi

  create_backup_branch "$(git_current_branch)"

  log "Sync with origin/main using strategy: $STRATEGY"
  case "$STRATEGY" in
    rebase) doit "git rebase origin/main" ;;
    merge)  doit "git merge --no-ff origin/main" ;;
    *) die "Unknown strategy: $STRATEGY" ;;
  esac

  log "Resolve any conflicts, then continue rebase/merge as needed."
  warn "If conflicts exist, re-run this step after resolving (script will continue)."

  if have pytest; then
    log "Running tests (pytest -q)..."
    doit "pytest -q"
  else
    warn "pytest not found; skipping tests. Install to enable."
  fi

  log "Pushing branch upstream..."
  if [[ "$STRATEGY" == "rebase" ]]; then
    if [[ $FORCE_WITH_LEASE -eq 1 ]]; then
      doit "git push -u origin HEAD --force-with-lease"
    else
      warn "Rebase may require a force-with-lease push. Re-run with --force-with-lease to allow."
      doit "git push -u origin HEAD || true"
    fi
  else
    doit "git push -u origin HEAD"
  fi

  watch_checks_and_merge "$PR14_NUM"
}

heuristic_runtime_change_check(){
  local base="origin/main"
  log "Heuristic scan for runtime changes vs $base..."
  run "git fetch origin main --quiet || true"
  run "git diff --name-only $base...HEAD | sed 's/^/  - /'"
  echo
  log "Diffstat (full vs. -w):"
  run "git diff --stat $base...HEAD"
  run "git diff -w --stat $base...HEAD"
  echo
  log "Scanning added lines for suspicious tokens (return, if, for, while, yield, await, assignments/calls)..."
  run "git diff $base...HEAD | grep -E '^\+[^+]' | grep -E '\\b(return|if|for|while|yield|await)\\b|\([^)]+\)|[^!<>]=[^=]' | sed 's/^/  ? /' || true"
  echo
  warn "This is a heuristic; manually inspect if any '?' lines appear."
}

cmd_pr15(){
  ensure_repo
  req git
  have gh || warn "gh not installed; will operate via git only."

  log "Checkout PR #$PR15_NUM (bp-types-doctests)..."
  if have gh; then
    doit "gh pr checkout $PR15_NUM"
  else
    die "gh required to checkout PR by number; alternatively 'git fetch origin pull/$PR15_NUM/head:pr-$PR15_NUM && git checkout pr-$PR15_NUM'"
  fi

  log "Run doctests..."
  if have pytest; then
    doit "pytest --doctest-modules -q"
  else
    die "pytest required to run doctests."
  fi

  if have mypy; then
    log "Optional: running mypy (if configured)..."
    doit "mypy || true"
  fi

  heuristic_runtime_change_check

  watch_checks_and_merge "$PR15_NUM"
}

cmd_ci_gate(){
  ensure_repo
  req gh jq
  local prs=("${CI_GATE_PRS[@]}")
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --prs) IFS=',' read -r -a prs <<< "${2:?}"; shift 2;;
      *) break;;
    esac
  done

  for pr in "${prs[@]}"; do
    log "Checking PR #$pr status and merge commit..."
    run "gh pr view $pr --json number,state,mergedAt,mergeCommit,mergeStateStatus,statusCheckRollup | jq '{
      number, state, mergedAt, merge_commit_sha:(.mergeCommit.oid), mergeStateStatus,
      checks: (.statusCheckRollup // [] | map({name:.name, status:.status, conclusion:(.conclusion // "")}))
    }'"
  done
}

cmd_cleanup_branches(){
  ensure_repo
  local branches=("$@")
  if [[ ${#branches[@]} -eq 0 ]]; then
    branches=("${DEFAULT_CLEANUP_BRANCHES[@]}")
  fi
  log "Deleting remote branches: ${branches[*]}"
  doit "git fetch --all --prune"
  doit "git push origin --delete ${branches[*]} || true"
}

cmd_rollback(){
  ensure_repo
  req git
  have gh || warn "gh not installed; will need explicit --sha."

  local pr=""
  local sha=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --pr) pr="${2:?}"; shift 2;;
      --sha) sha="${2:?}"; shift 2;;
      *) break;;
    esac
  done

  if [[ -n "$pr" && -z "$sha" ]]; then
    req gh jq
    log "Fetching merge commit SHA for PR #$pr..."
    sha="$(gh pr view "$pr" --json mergeCommit -q .mergeCommit.oid)"
    [[ -n "$sha" ]] || die "Could not determine merge commit SHA for PR #$pr"
  fi

  [[ -n "$sha" ]] || die "Provide --pr N or --sha SHA"

  log "Creating revert for merge commit $sha (-m 1)..."
  create_backup_branch "$(git_current_branch)"
  doit "git revert $sha -m 1"

  local revert_branch="revert-$sha"
  log "Pushing revert branch and opening PR..."
  doit "git checkout -b $revert_branch"
  doit "git push -u origin $revert_branch"
  if have gh; then
    doit "gh pr create --title \"Revert $sha\" --body \"Automated revert via xlude.\" --base main --head $revert_branch"
  else
    warn "gh not installed; open PR manually."
  fi
}

main(){
  # Parse global flags first
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --repo) REPO="${2:?}"; shift 2;;
      --apply) APPLY=1; shift;;
      --merge-method) MERGE_METHOD="${2:?}"; shift 2;;
      --strategy) STRATEGY="${2:?}"; shift 2;;
      --force-with-lease) FORCE_WITH_LEASE=1; shift;;
      --no-auto-merge) AUTO_MERGE=0; shift;;
      -h|--help) usage; exit 0;;
      help) usage; exit 0;;
      *) break;;
    esac
  done

  local cmd="${1:-}"
  [[ -n "$cmd" ]] || { usage; exit 0; }
  shift || true

  case "$cmd" in
    check-tools)          cmd_check_tools "$@";;
    pr14)                 cmd_pr14 "$@";;
    pr15)                 cmd_pr15 "$@";;
    backup-refs)          cmd_backup_refs "$@";;
    ci-gate)              cmd_ci_gate "$@";;
    cleanup-branches)     cmd_cleanup_branches "$@";;
    rollback)             cmd_rollback "$@";;
    -h|--help|help)       usage;;
    *) die "Unknown command: $cmd";;
  esac

  log "Done (version $VERSION). Mode: $([ "$APPLY" -eq 1 ] && echo APPLY || echo DRY-RUN)"
}

main "$@"
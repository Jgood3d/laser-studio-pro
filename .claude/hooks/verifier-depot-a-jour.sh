#!/usr/bin/env bash
# Avant que Claude modifie un fichier : la branche doit être à jour.
#
# Bloque la modification (code de sortie 2, message renvoyé à Claude) si la
# branche courante a du retard sur sa branche distante, ou s'il manque des
# commits de Dev (dépôt Jgood3d/laser-studio-pro). Claude suit alors l'étape 1
# du skill « contribuer » (mise à jour) avant de recommencer.
#
# Ne bloque jamais sans raison sûre : pas de réseau, pas de branche distante,
# fusion ou rebase en cours => on laisse passer. Une vérification réussie vaut
# 15 minutes, pour ne pas interroger GitHub à chaque modification.

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

git_dir=$(git rev-parse --git-dir)
marker="$git_dir/claude-verif-a-jour"
now=$(date +%s)
if [ -f "$marker" ]; then
    last=$(cat "$marker" 2>/dev/null)
    case "$last" in ''|*[!0-9]*) last=0 ;; esac
    [ $((now - last)) -lt 900 ] && exit 0
fi

# Fusion, rebase ou cherry-pick en cours : on résout les conflits, pas de blocage.
for f in MERGE_HEAD REBASE_HEAD CHERRY_PICK_HEAD rebase-merge rebase-apply; do
    [ -e "$git_dir/$f" ] && exit 0
done

branch=$(git branch --show-current)
[ -n "$branch" ] || exit 0

# Dépôt principal : le remote qui pointe vers Jgood3d/laser-studio-pro, origin sinon.
main_remote=$(git remote -v | awk 'tolower($2) ~ /jgood3d\/laser-studio-pro/ {print $1; exit}')
[ -n "$main_remote" ] || main_remote=origin
git remote get-url "$main_remote" >/dev/null 2>&1 || exit 0

tracking=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)
tracking_remote=${tracking%%/*}

# timeout de coreutils (présent dans Git Bash sous Windows) ; sans lui, fetch sans limite.
if command -v timeout >/dev/null 2>&1 && timeout --version >/dev/null 2>&1; then
    limit="timeout 30"
else
    limit=""
fi
fetch() {
    GIT_TERMINAL_PROMPT=0 $limit git fetch --quiet "$1" >/dev/null 2>&1
}
fetch "$main_remote" || exit 0          # pas de réseau : on ne bloque pas
if [ -n "$tracking_remote" ] && [ "$tracking_remote" != "$main_remote" ]; then
    fetch "$tracking_remote" || exit 0
fi

problems=""
if [ -n "$tracking" ]; then
    behind=$(git rev-list --count "HEAD..$tracking" 2>/dev/null || echo 0)
    if [ "$behind" -gt 0 ]; then
        problems="$problems
- la branche « $branch » a $behind commit(s) de retard sur « $tracking »"
    fi
fi

dev_ref="$main_remote/Dev"
if [ "$branch" != "main" ] && git rev-parse --verify --quiet "$dev_ref" >/dev/null; then
    missing=$(git rev-list --count --no-merges "HEAD..$dev_ref" 2>/dev/null || echo 0)
    if [ "$missing" -gt 0 ]; then
        problems="$problems
- il manque $missing commit(s) de « $dev_ref » dans « $branch »"
    fi
fi

if [ -n "$problems" ]; then
    cat >&2 <<EOF
Modification refusée : le dépôt n'est pas à jour.$problems

Avant de modifier un fichier, mets le dépôt à jour en suivant l'étape 1 du
skill « contribuer » (.claude/skills/contribuer/SKILL.md), puis recommence.
EOF
    exit 2
fi

echo "$now" > "$marker"
exit 0

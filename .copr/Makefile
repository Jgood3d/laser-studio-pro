# Construction du paquet source (SRPM) par Copr, méthode « make srpm » :
#   make -f .copr/Makefile srpm outdir=<dossier> [spec=<chemin du spec>]
#
# Copr appelle cette cible dans un chroot, depuis une copie du dépôt git.
# L'archive est faite à partir du commit courant (n'importe quelle branche,
# sans attendre un tag) ; le spec en tire une version de développement
# 2.5.0-1.AAAAMMJJ.<nombre de commits>git<commit>. Aussi utilisable en local, voir
# packaging/fedora/README.md.

TOP := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
spec ?= $(TOP)/packaging/fedora/laser-studio-pro.spec
outdir ?= $(TOP)/dist/srpm
# - Une seule commande shell : make évaluerait des $(shell git ...) avant la
#   première ligne de la recette, donc avant que dnf installe git dans le chroot.
# - safe.directory : git refuse un dépôt dont il n'est pas le propriétaire
#   (cas du chroot de Copr).
# - commit, snapdate et commitcount sont inscrits dans la copie du spec mise
#   dans le SRPM : des --define seraient perdus quand Copr (ou mock) le reconstruit.
# - commitcount : nombre de commits, qui ordonne les versions d'un même jour.
#   Un clone partiel (--depth) le fausserait : l'historique est alors complété.
srpm:
	set -e; \
	command -v git >/dev/null && command -v rpmbuild >/dev/null || dnf -y install git rpm-build; \
	git="git -c safe.directory=* -C $(TOP)"; \
	name=$$(rpmspec -q --srpm --qf '%{name}' $(spec)); \
	version=$$(rpmspec -q --srpm --qf '%{version}' $(spec)); \
	commit=$$($$git rev-parse HEAD); \
	snapdate=$$($$git log -1 --format=%cd --date=format:%Y%m%d); \
	if [ "$$($$git rev-parse --is-shallow-repository)" = true ]; then $$git fetch -q --unshallow; fi; \
	commitcount=$$($$git rev-list --count HEAD); \
	work=$$(mktemp -d); \
	$$git archive --format=tar.gz --prefix="$$name-$$version/" -o "$$work/$$name-$$version.tar.gz" HEAD; \
	{ echo "%global commit $$commit"; echo "%global snapdate $$snapdate"; echo "%global commitcount $$commitcount"; cat $(spec); } > "$$work/$$name.spec"; \
	rpmbuild -bs "$$work/$$name.spec" --define "_sourcedir $$work" --define "_srcrpmdir $(outdir)"; \
	rm -r "$$work"

.PHONY: srpm

# Construction du paquet source (SRPM) par Copr, méthode « make srpm » :
#   make -f .copr/Makefile srpm outdir=<dossier> [spec=<chemin du spec>]
#
# Copr appelle cette cible dans un chroot, depuis une copie du dépôt git.
# L'archive est faite à partir du commit courant (n'importe quelle branche,
# sans attendre un tag) ; le spec en tire une version de développement
# 2.5.0-1.AAAAMMJJgit<commit>. Aussi utilisable en local, voir
# packaging/fedora/README.md.

TOP := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
spec ?= $(TOP)/packaging/fedora/laser-studio-pro.spec
outdir ?= $(TOP)/dist/srpm
# git refuse un dépôt dont il n'est pas le propriétaire (cas du chroot de Copr).
GIT := git -c safe.directory='*' -C $(TOP)

srpm:
	command -v git >/dev/null && command -v rpmbuild >/dev/null || dnf -y install git rpm-build
	$(eval NAME := $(shell rpmspec -q --srpm --qf '%{name}' $(spec)))
	$(eval VERSION := $(shell rpmspec -q --srpm --qf '%{version}' $(spec)))
	$(eval COMMIT := $(shell $(GIT) rev-parse HEAD))
	$(eval SNAPDATE := $(shell $(GIT) log -1 --format=%cd --date=format:%Y%m%d))
	$(eval WORK := $(shell mktemp -d))
	$(GIT) archive --format=tar.gz --prefix=$(NAME)-$(VERSION)/ \
		-o $(WORK)/$(NAME)-$(VERSION).tar.gz HEAD
	# commit et snapdate inscrits dans la copie du spec mise dans le SRPM : des
	# --define seraient perdus quand Copr (ou mock) reconstruit le SRPM.
	{ echo "%global commit $(COMMIT)"; echo "%global snapdate $(SNAPDATE)"; cat $(spec); } \
		> $(WORK)/$(NAME).spec
	rpmbuild -bs $(WORK)/$(NAME).spec \
		--define "_sourcedir $(WORK)" \
		--define "_srcrpmdir $(outdir)"
	rm -rf $(WORK)

.PHONY: srpm

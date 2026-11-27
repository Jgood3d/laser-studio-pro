# Paquet RPM de Laser Studio Pro pour Fedora (Copr). Voir packaging/fedora/README.md.
#
# Version publiée : l'archive du tag v%%{version} sur GitHub.
# Version de développement : `make -f .copr/Makefile srpm` construit l'archive
# depuis le dépôt git et définit `commit`, `snapdate` et `commitcount`
# (Release 1.AAAAMMJJ.<nombre de commits>git<commit>).

%global forgeurl https://github.com/Jgood3d/laser-studio-pro
%global app_id io.github.jgood3d.LaserStudioPro

%bcond tests 1

%if %{defined commit}
%global shortcommit %(c=%{commit}; echo ${c:0:7})
# Le nombre de commits départage les versions d'un même jour : le hash seul les
# classerait au hasard, et dnf ne proposerait pas toujours la plus récente.
%global snapinfo .%{snapdate}.%{commitcount}git%{shortcommit}
%endif

Name:           laser-studio-pro
Version:        3.0.0
Release:        1%{?snapinfo}%{?dist}
Summary:        Prepare and engrave images and drawings on GRBL lasers

# Code : GPL-3.0-or-later. Icônes Breeze et Jarvis (resources/icons/) : LGPL-3.0-or-later.
# Polices embarquées (OFL-1.1) : retirées, remplacées par celles du système (voir %%prep).
License:        GPL-3.0-or-later AND LGPL-3.0-or-later
URL:            %{forgeurl}
Source:         %{forgeurl}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib
%if %{with tests}
# Polices vérifiées par les tests (tests/test_bundled_fonts.py, Stencil Studio).
BuildRequires:  dejavu-sans-fonts
BuildRequires:  google-rubik-fonts
BuildRequires:  impallari-dancing-script-fonts
BuildRequires:  appstream
%endif

# Polices des modèles de la bibliothèque et de Stencil Studio : celles du système,
# pas des copies (voir %%prep et %%install). Qt les trouve sous le même nom.
Requires:       dejavu-sans-fonts
Requires:       google-rubik-fonts
Requires:       impallari-dancing-script-fonts
Requires:       hicolor-icon-theme
# Détection du sujet par IA dans Stencil Studio : facultative. Suggests et non
# Recommends : onnxruntime exige sympy, qui recommande LaTeX et matplotlib
# (plus de 200 paquets, environ 1 Go installé).
Suggests:       python3-onnxruntime

%description
Laser Studio Pro prepares images and vector drawings for laser engraving and
cutting, then drives GRBL engravers and cutters over USB: image engraving with
dithering, vector editor with layers (SVG and DXF import, text, shapes,
nesting), box, puzzle and keychain generators, Stencil Studio, guided
calibration and machine control.


%prep
%autosetup -p1
# Fedora fournit OpenCV sous le nom « opencv » (python3-opencv), sans variante headless.
sed -i 's/"opencv-python-headless"/"opencv"/' pyproject.toml
# Modèle de détourage de Stencil Studio : téléchargé au premier usage dans le
# profil de l'utilisateur, car le dossier installé n'est pas modifiable.
rm src/stencil_studio/resources/models/u2netp.onnx
# Polices embarquées (Rubik, Dancing Script) : celles des paquets Fedora, en
# Requires. Sans le dossier, l'application s'appuie sur les polices du système.
rm -r src/laser_studio/resources/fonts
# Modules lancés seuls dans le dépôt : installés, ce ne sont plus des scripts.
for f in $(grep -rl --include='*.py' '^#!' src); do
    sed -i '1{/^#!/d}' "$f"
done


%generate_buildrequires
%pyproject_buildrequires


%build
%pyproject_wheel


%install
%pyproject_install

# Stencil Studio : police DejaVu du système à la place de la copie embarquée.
ln -sf %{_datadir}/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf \
    %{buildroot}%{python3_sitelib}/stencil_studio/resources/fonts/DejaVuSans-Bold.ttf

%pyproject_save_files -L laser_studio laser_common stencil_studio

desktop-file-install --dir=%{buildroot}%{_datadir}/applications \
    packaging/linux/%{app_id}.desktop
install -Dpm 0644 src/laser_studio/resources/laser_studio_pro_512.png \
    %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/%{app_id}.png
install -Dpm 0644 packaging/linux/%{app_id}.metainfo.xml \
    %{buildroot}%{_metainfodir}/%{app_id}.metainfo.xml


%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{app_id}.desktop
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/%{app_id}.metainfo.xml
# selftest : autotest de Stencil Studio, lancé à la main.
%pyproject_check_import -e stencil_studio.selftest
%if %{with tests}
export QT_QPA_PLATFORM=offscreen
export QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox"
%{py3_test_envvars} %{python3} -m unittest discover -s tests
%endif


%files -f %{pyproject_files}
%license LICENSE
%license src/laser_studio/resources/icons/breeze/COPYING.LGPL-3
%doc README.md CHANGELOG.md
%{_bindir}/laser-studio-pro
%{_datadir}/applications/%{app_id}.desktop
%{_datadir}/icons/hicolor/512x512/apps/%{app_id}.png
%{_metainfodir}/%{app_id}.metainfo.xml


%changelog
* Thu Nov 26 2026 Antoine Le Morvan <antoine@le-morvan.com> - 3.0.0-1
- Version 3.0.0

* Sun Nov 22 2026 Antoine Le Morvan <antoine@le-morvan.com> - 2.5.0-1
- Initial package

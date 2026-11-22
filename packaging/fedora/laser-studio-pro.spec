# Paquet RPM de Laser Studio Pro pour Fedora (Copr). Voir packaging/fedora/README.md.
#
# Version publiée : l'archive du tag v%%{version} sur GitHub.
# Version de développement : `make -f .copr/Makefile srpm` construit l'archive
# depuis le dépôt git et définit `commit` et `snapdate` (Release 1.AAAAMMJJgit<commit>).

%global forgeurl https://github.com/Jgood3d/laser-studio-pro
%global app_id io.github.jgood3d.LaserStudioPro

%bcond tests 1

%if %{defined commit}
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global snapinfo .%{snapdate}git%{shortcommit}
%endif

Name:           laser-studio-pro
Version:        2.5.0
Release:        1%{?snapinfo}%{?dist}
Summary:        Prepare and engrave images and drawings on GRBL lasers

# Code : GPL-3.0-or-later. Polices embarquées (resources/fonts/) : OFL-1.1.
# Icônes Breeze et Jarvis (resources/icons/) : LGPL-3.0-or-later.
License:        GPL-3.0-or-later AND OFL-1.1 AND LGPL-3.0-or-later
URL:            %{forgeurl}
Source:         %{forgeurl}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib
%if %{with tests}
# Fenêtres créées hors écran pendant les tests ; police DejaVu de Stencil Studio.
BuildRequires:  dejavu-sans-fonts
BuildRequires:  appstream
%endif

# Police de Stencil Studio : celle du système, pas une copie (voir %%install).
Requires:       dejavu-sans-fonts
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
rm src/stencil_studio/models/u2netp.onnx
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
    %{buildroot}%{python3_sitelib}/stencil_studio/fonts/DejaVuSans-Bold.ttf

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
%license src/laser_studio/resources/fonts/OFL-*.txt
%license src/laser_studio/resources/icons/breeze/COPYING.LGPL-3
%doc README.md CHANGELOG.md
%{_bindir}/laser-studio-pro
%{_datadir}/applications/%{app_id}.desktop
%{_datadir}/icons/hicolor/512x512/apps/%{app_id}.png
%{_metainfodir}/%{app_id}.metainfo.xml


%changelog
* Sun Nov 22 2026 Antoine Le Morvan <antoine@le-morvan.com> - 2.5.0-1
- Initial package

# Code signing policy

*[Version française plus bas](#politique-de-signature-du-code)*

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

## What is signed

The Windows release files of Laser Studio Pro: the program `LaserStudioPro.exe` and the installer `LaserStudioPro_Setup-<version>-Windows.exe`. They are built by the [Release workflow](.github/workflows/release.yml) on GitHub Actions, from the source code of this repository only, for a version tag (`v<version>`). Nothing built on a personal computer is signed.

Each signed file carries the product name "Laser Studio Pro" and the version of the release (`APP_VERSION` in `src/laser_studio/core/version.py`, the same as the tag).

## Team roles

| Role | Members |
| --- | --- |
| Committers and reviewers | [Jgood3d](https://github.com/Jgood3d), [alemorvan](https://github.com/alemorvan) |
| Approvers | [Jgood3d](https://github.com/Jgood3d) |

Every change reaches the `Dev` branch through a pull request. Every signing request is approved by hand by an approver, for releases only.

## Privacy

Laser Studio Pro does not collect or send any personal data, and has no telemetry.

The program only connects to the internet in one case: Stencil Studio's optional subject detection downloads its AI model (`u2netp.onnx`, from GitHub) when it is not already installed, and checks the file's fingerprint before using it. The links to the donation page and to the support e-mail open only when the user clicks them.

---

# Politique de signature du code

Signature du code gratuite fournie par [SignPath.io](https://about.signpath.io/), certificat de la [SignPath Foundation](https://signpath.org/).

## Ce qui est signé

Les fichiers Windows publiés de Laser Studio Pro : le programme `LaserStudioPro.exe` et l'installeur `LaserStudioPro_Setup-<version>-Windows.exe`. Ils sont compilés par le [workflow Release](.github/workflows/release.yml) sur GitHub Actions, uniquement à partir du code source de ce dépôt, pour un tag de version (`v<version>`). Rien de ce qui est compilé sur un ordinateur personnel n'est signé.

Chaque fichier signé porte le nom de produit « Laser Studio Pro » et la version publiée (`APP_VERSION` dans `src/laser_studio/core/version.py`, identique au tag).

## Rôles dans l'équipe

| Rôle | Membres |
| --- | --- |
| Auteurs et relecteurs | [Jgood3d](https://github.com/Jgood3d), [alemorvan](https://github.com/alemorvan) |
| Approbateurs | [Jgood3d](https://github.com/Jgood3d) |

Toute modification arrive dans la branche `Dev` par une pull request. Chaque demande de signature est approuvée à la main par un approbateur, pour les versions publiées uniquement.

## Vie privée

Laser Studio Pro ne collecte ni n'envoie aucune donnée personnelle, et n'a aucune télémétrie.

Le programme ne se connecte à internet que dans un cas : la détection du sujet de Stencil Studio, facultative, télécharge son modèle d'IA (`u2netp.onnx`, depuis GitHub) s'il n'est pas déjà installé, et vérifie l'empreinte du fichier avant de l'utiliser. Les liens vers la page de dons et vers l'e-mail de support ne s'ouvrent que sur un clic de l'utilisateur.

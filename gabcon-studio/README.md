# GabCon Studio — Interface pour GabCon-BuildAI

Une interface Web **locale** pour le dépôt [GabCon-BuildAI](https://github.com/misterblaecher/GabCon-BuildAI).

**Workflow sans API d'IA :** décris ton idée → copie le prompt dans ChatGPT (site/app normal) → colle le blueprint Python généré → exécute et visualise avec le moteur Python du projet → exporte `.schem`, `.py`, `.png`, `.json`.

## Installation

1. Le dossier **`gabcon-studio/` est inclus dans le dépôt `GabCon-BuildAI`**, au même niveau que `src/`, `tools/`, `pyproject.toml` et `mod/`.
2. Installer les dépendances du dépôt, si ce n'est pas déjà fait :

   ```bash
   uv sync --extra dev
   ```

3. Depuis la racine du dépôt, lancer :

   ```bash
   uv run python gabcon-studio/server.py
   ```

4. Ouvrir **http://127.0.0.1:8788** dans le navigateur.

> Sur Windows, ces commandes fonctionnent dans PowerShell si `uv` est installé. Le port 8788 diffère de celui du dashboard BuildAI (8787).

## Fonctionnalités

- Copie d'un prompt spécialisé pour ChatGPT, sans appel à l'API OpenAI.
- Éditeur Python avec import `.py`, insertion de tabulations et sauvegarde automatique du brouillon dans le navigateur.
- Génération à partir du **véritable DSL BuildAI** (`run_blueprint`) ; pas une simulation.
- Validation structurale et génération de `render.png` (6 vues) et `final.schem` WorldEdit.
- Visualiseur 3D interactif simplifié (souris pour tourner, molette pour zoomer, `Maj` + glisser pour déplacer) sans dépendances Web externes.
- Statistiques, palette de matériaux, téléchargements et historique local.
- Support du registre de blocs personnalisé via la variable `MCBUILD_SERVER_REGISTRY` du dépôt.

Les projets sont conservés dans `gabcon-studio/runs/`. Le dossier est ignoré par son propre `.gitignore`.

## Limitations et sécurité

- **Local uniquement** (`127.0.0.1`) : cette interface n'est pas conçue pour un serveur public.
- Le sandbox DSL du dépôt est conçu contre les **erreurs de l'IA, pas contre un adversaire malveillant** : ne colle pas de Python provenant d'une personne non fiable et n'expose pas ce service à Internet.
- La construction est exécutée dans un processus Python enfant avec délai maximum et le serveur accepte une seule génération à la fois.
- **Limite standard : 1 000 000 blocs** (auparavant 160 000). La limite interne de `VoxelGrid` reste à 4 000 000 blocs et 512 blocs de dimension par axe.
- Pour augmenter la limite de Studio (sans modifier le moteur), définir dans le fichier `.env` du dépôt : `GABCON_STUDIO_MAX_BLOCKS=2000000`, puis **redémarrer le serveur Studio**. Les valeurs sont plafonnées à 4 000 000.
- Jusqu'à **160 000 blocs**, Studio tente le rendu détaillé de six vues et la prévisualisation 3D. Au-delà, il génère automatiquement **une vue du dessus allégée** ; `final.schem` conserve l'intégralité des blocs. La vue 3D navigateur n'est pas chargée au-delà de ce seuil, et peut également être désactivée si la surface dépasse 30 000 blocs.
- L'exporteur `.schem` actuel convertit le volume entier en mémoire : Studio protège les ressources avec une limite de **20 millions de cases englobantes**, y compris les espaces vides. Pour des builds très étalés, rapproche les zones séparées.
- Les grosses générations peuvent durer longtemps ; le délai maximal du processus est porté à **900 secondes**. Augmenter la limite ne garantit pas que l'ordinateur pourra rendre ou exporter toutes les tailles.
- Le visualiseur 3D utilise des couleurs simplifiées, sans les modèles et textures Minecraft réels. Le PNG utilise le renderer de BuildAI.
- Un script DSL doit utiliser les fonctions supportées par le projet, **pas** `minecraft`, `mcpi` ou `worldedit` comme import Python.
- Il n'y a aucune synchronisation automatique de la conversation ChatGPT, pas de connexion au compte, et aucune API d'IA utilisée par Studio.

## Erreur HTTP 422

Un `POST /api/build 422` signifie qu'une erreur du **blueprint, de la palette, d'une limite ou du moteur** s'est produite : ce n'est pas systématiquement la limite de blocs. Le message exact est affiché **sous l'éditeur** et aussi dans la console PowerShell du serveur sous la forme `[studio] Build failed (...): ...`. Conserve ce texte pour diagnostiquer le problème.

## Fichiers

- `server.py` : API HTTP locale et sorties téléchargeables.
- `worker.py` : utilise `mcbuild.dsl.sandbox`, le moteur de rendu et l'exporteur `.schem` du projet.
- `static/` : interface HTML/CSS/JS responsive et viewer canvas autonome.

## Windows : démarrage rapide

Double-clique sur `gabcon-studio/lancer-studio.bat` après avoir exécuté `uv sync --extra dev`.

## Test rapide

Clique sur **Exemple**, puis **Visualiser la construction**. Le script de démonstration construit une tour médiévale. S'il y a une erreur de bloc ou de dépendances, Studio affiche le message renvoyé par BuildAI pour que tu puisses corriger le blueprint.

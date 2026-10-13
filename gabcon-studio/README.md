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

## Utilisation sur téléphone (Android / iPhone)

GabCon Studio est une **application Web installable (PWA)**. Son moteur de génération reste sur ton PC Windows ; ton téléphone sert d'interface pour coller le Python de ChatGPT, inspecter la construction et récupérer le `.schem`.

La solution recommandée est **Tailscale Serve**, qui fournit un accès HTTPS **privé** sans exposer le port Python sur Internet. Tu peux utiliser ton téléphone même en dehors du Wi-Fi de chez toi, tant que le PC et le téléphone sont connectés au même réseau privé Tailscale (tailnet) et que le PC reste allumé.

1. Installer [Tailscale](https://tailscale.com/download) **sur le PC et le téléphone**, puis te connecter au **même compte/tailnet** sur les deux.
2. Dans PowerShell sur le PC, depuis la racine du projet, lancer Studio :

   ```powershell
   uv run python gabcon-studio/server.py
   ```

3. Dans **un deuxième PowerShell sur le PC**, activer le proxy HTTPS privé :

   ```powershell
   tailscale serve --bg http://127.0.0.1:8788
   tailscale serve status
   ```

   Lors de la première utilisation, Tailscale peut demander d'activer HTTPS pour ton tailnet. Le résultat de `tailscale serve status` affiche l'adresse HTTPS du PC (de forme `https://nom-pc.<tailnet>.ts.net`).

4. Sur ton téléphone, activer Tailscale, puis ouvrir **l'adresse HTTPS affichée** dans le navigateur du téléphone.
5. Ajouter GabCon Studio à l'écran d'accueil : **Android** → menu Chrome → *Installer l'application* ou bouton *Installer l'app* dans Studio ; **iPhone** → Safari → *Partager* → *Sur l'écran d'accueil*.

Tu peux alors lancer Studio depuis son icône. Le bouton *Installer l'app* de Studio fournit également une indication pour ton navigateur. Sur mobile, tu peux **pivoter avec un doigt et zoomer avec deux doigts** dans la vue 3D.

**Important :**
- Ne pas remplacer `tailscale serve` par `tailscale funnel` : Funnel publie un service sur l'Internet public.
- Ne pas ouvrir/rediriger le port `8788` sur la box Internet et ne pas modifier `HOST = "127.0.0.1"`. Le processus traite du Python fourni par l'utilisateur et **n'est pas sécurisé contre du code hostile**.
- Restreindre l'accès à ton tailnet ; toute personne disposant de l'accès au service peut utiliser Studio. Ne partage pas cet accès avec une personne non fiable.
- La page d'accueil peut être mise en cache par la PWA, mais **les générations, fichiers et API exigent une connexion au PC**. Les blueprints en cours sont sauvegardés uniquement dans le stockage local de *chaque navigateur*, ils ne sont pas synchronisés entre le PC et le téléphone. L'historique des constructions est, lui, stocké sur le PC.
- **GitHub Pages ne peut pas exécuter le moteur BuildAI en Python**. Une version entièrement hébergée sur un site public nécessiterait un serveur Python distinct, un système de comptes/authentification et une isolation renforcée du code, ce que ce mode privé n'essaie pas de faire.

Documentation : [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) et [installation des applications Web sur mobile](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable).

## Fonctionnalités

- Copie d'un prompt spécialisé pour ChatGPT, sans appel à l'API OpenAI.
- Application Web mobile installable sur Android/iPhone, avec icônes, manifeste et accès privé HTTPS via Tailscale Serve.
- Gestes tactiles du visualiseur 3D : glisser pour pivoter, pincer pour zoomer.
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

## Accélérer les générations sur PC

L'export Sponge `.schem` utilise des tableaux NumPy compacts ; les validations sont effectuées une seule fois dans Studio. Le `stats.json` d'une génération contient désormais `timings_ms` avec les durées de **blueprint**, **validation**, **render**, **schematic** et **browser_preview**. Ces durées permettent de voir si le PC est ralenti par les boucles Python, le rendu 3D ou l'export.

**Pour privilégier la vitesse à la qualité du rendu**, ajouter ceci dans le `.env` à la racine du dépôt :

```dotenv
GABCON_STUDIO_PREVIEW_MODE=fast
```

Puis arrêter le serveur (Ctrl+C), et relancer :

```powershell
uv run python gabcon-studio/server.py
```

**Depuis l'éditeur Studio, sélectionne le mode de rendu par génération :**

- **⚡ Rapide (choix initial de l'interface)** : une seule vue isométrique **sans ombres** sur les petits builds, plutôt que six vues avec calcul d'ombres. Adapté aux essais et aux constructions importantes.
- **✦ Qualité** : six vues détaillées avec ombres pour les projets de 160 000 blocs ou moins.
- **Au-delà de 160 000 blocs** : les deux modes utilisent automatiquement une vue du dessus légère pour éviter de saturer la RAM. Le fichier `.schem` conserve tous les blocs.

La valeur `GABCON_STUDIO_PREVIEW_MODE=fast` définit aussi un mode rapide lors de l'utilisation du worker directement en ligne de commande (sans l'interface Web). Dans l'interface, le menu de rendu fait autorité. Le mode précédent `auto` garde son comportement de compatibilité : qualité pour les petits projets et vue du dessus pour les grands.

L'export `.schem` choisit automatiquement une grille dense NumPy de 8, 16 ou 32 bits suivant la taille de la palette (au lieu de réserver systématiquement 16 bits). La validation structurale, faite avant l'export Studio, n'est pas répétée. La compatibilité Sponge Schematic v3 et Minecraft 1.21.1 est couverte par les tests.

Pour comparer la vitesse sur un même PC, génère exactement le même blueprint et la même seed dans chaque mode, puis lis les durées `render` et `schematic` du panneau de statistiques. Aucun gain chiffré n'est garanti sans mesure sur ta machine.

Pour un test reproductible sur le même ordinateur :

```powershell
uv run python tools/benchmark_schem.py --width 64 --height 32 --length 64
```

Conseils système : utiliser un SSD pour `gabcon-studio/runs/`, fermer les applications consommant beaucoup de RAM, et garder `uv`/Python à jour sans modifier manuellement les dépendances verrouillées. Vérifier les temps dans `stats.json` avant de chercher à augmenter le nombre de cœurs : le DSL et la génération 3D n'utilisent pas automatiquement tous les cœurs du CPU.

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

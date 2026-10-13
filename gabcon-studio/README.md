# GabCon Studio — Interface pour GabCon-BuildAI

Une interface Web **locale** pour le dépôt [GabCon-BuildAI](https://github.com/misterblaecher/GabCon-BuildAI).

**Deux parcours indépendants, sans API d'IA intégrée :**
- **A — ChatGPT direct :** décris la construction → choisis facultativement le format via une **carte-bouton avec pour/contre** → copie le prompt → ChatGPT crée directement le fichier Minecraft téléchargeable.
- **B — GabCon BuildAI local :** charge un blueprint **`.py` ou `.json`** dans l'éditeur moteur → exécute le moteur sur ton PC → prévisualise et exporte `.schem`, `.py`, `.png`, `.json`.

La sélection de format ChatGPT **ne change jamais** l'entrée, les paramètres ou l'exécution du moteur BuildAI.

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

## Parcours A — Génération directe par ChatGPT

**GabCon Studio sert à préparer un prompt**, avec un format de fichier **facultatif**.
La création du fichier est demandée **dans ChatGPT**, puis le joueur le télécharge et l'essaie
dans Minecraft. Le moteur local, le visualiseur et l'éditeur Studio restent disponibles
comme **outils optionnels** ; aucun n'est nécessaire pour demander un fichier à ChatGPT.

1. Dans **Préparer le prompt pour ChatGPT**, écris ton idée, puis choisis style/échelle/détails.
2. Dans la grille de **cartes-boutons**, laisse **Aucun format imposé** sélectionné pour un prompt **général**.
   ChatGPT décide alors du meilleur format utilisable pour ce projet.
3. Pour un format particulier, clique sur sa carte. Chaque carte affiche **pour / contre**,
   difficulté IA et statut *prêt en jeu / conversion requise* sans menu déroulant.
   La carte sélectionnée est mise en évidence et adapte uniquement le prompt ChatGPT.
4. Clique **Copier le prompt pour ChatGPT**, ouvre une conversation ChatGPT et colle-le.
5. ChatGPT utilise ses outils disponibles pour **créer le fichier téléchargeable directement**
   et t'indique comment l'installer ou le charger dans Minecraft.

### Catalogue : formats réellement utilisables pour un build Java 1.21.1

Les **cartes cliquables** sont regroupées par **destination réelle**, et les prompts ChatGPT sont distincts pour chaque format.
La colonne *difficulté IA* est une estimation de la difficulté de produire un fichier **valide**
avec des outils de code/fichiers, pas une mesure de fiabilité garantie.

| Type de fichier | Atouts | Limites | Difficulté IA / test en jeu |
| --- | --- | --- | --- |
| **Aucun format** (par défaut) | ChatGPT choisit une sortie adaptée au projet sans imposer d'extension | Moins prévisible | Variable |
| **`.schem` Sponge v3 / WorldEdit** | Idéal pour coller rapidement des structures modernes et de grande taille | WorldEdit/compatible nécessaire, NBT gzip + VarInt à vérifier | **Intermédiaire** / prêt avec WorldEdit |
| **`.litematic` Litematica/Forgematica** | Hologramme, plans guidés, liste des matériaux en survie | Mod + bibliothèque compatibles, palette et tableau LongArray complexe | **Difficile** / prêt avec mod compatible |
| **`.nbt` structure vanilla Java** | Pas besoin de WorldEdit, format de structure natif | Structure block limité en taille ; commandes / datapack pour placement important | **Intermédiaire** / prêt avec structure block ou commande |
| **`.zip` datapack** | Installation dans `datapacks`, commandes vanilla, pas de plugin requis | Permissions pour `/function`, génération de beaucoup de blocs potentiellement lourde | **Facile à intermédiaire** / prêt après installation |
| **`.mcfunction`** | Génération par IA simple : texte de commandes `fill`/`setblock` | Fichier seul non exécutable : nécessite un datapack | **Facile** / intermédiaire |
| **`.py` DSL BuildAI** | Compact, boucles, formes complexes et finitions | Nécessite le moteur GabCon-BuildAI pour fabriquer un vrai schematic | **Facile à intermédiaire** / intermédiaire |
| **`.json` opérations** | Facile à valider et modifier ; contrôles stricts de la liste d'opérations | Non chargé par Minecraft sans convertisseur ; 1 200 primitives maximum | **Facile** / intermédiaire |
| **`.md` plan** | Utile pour conceptualiser architecture, dimensions et matériaux | **N'est pas un build** ; ne place aucun bloc | **Facile** / documentation |

**Choix conseillé :** `.schem` pour charger/coller un build dans WorldEdit ;
`.litematic` pour l'afficher comme schéma de construction avec Forgematica sur NeoForge ;
`.nbt` ou un datapack `.zip` si tu veux éviter WorldEdit.
Si tu ne sélectionnes rien, ChatGPT décide librement : le prompt **ne favorise aucun format**.

Les prompts spécialisés demandent à ChatGPT de **créer directement les vrais fichiers**
et de vérifier leur structure avec ses outils de code/fichiers : type NBT, dimensions,
index des palettes, compression, ZIP et emplacements de fichiers. Un fichier binaire
**ne doit jamais être simulé par du texte renommé** : si la conversation ne dispose
pas des outils nécessaires, ChatGPT doit signaler la limite et proposer une alternative réelle.

Pour Minecraft Java **1.21.1**, le datapack utilise `pack_format=48` et
le chemin `data/gabcon/function/construction.mcfunction` (répertoire `function` au singulier).
Pour `.litematic` sur NeoForge, utiliser **Forgematica** avec **MaFgLib** adaptés à 1.21.1 ;
la Litematica classique vise principalement Fabric. Un `.nbt` de structure vanilla est
**différent** d'un `.schem` WorldEdit ; la méthode de placement diffère.

**Non proposés en génération directe Java 1.21.1 :** `.schematic` ancien format
(IDs historiques / problèmes de conversion), `.mcstructure` (Minecraft Bedrock),
`.mca` (région de monde, risquée à écraser) et `.obj`/`.vox` (modèles 3D non installables
comme des blocs Minecraft sans conversion).

### Le cas du schematic direct

Pour `.schem`, le prompt précise **Sponge v3**, **DataVersion 3955**, palette,
coordonnées, encodage **VarInt**, ordre des blocs et compression NBT gzip.
Il demande de **créer et vérifier le vrai fichier téléchargeable dans ChatGPT**,
sans appeler GitHub Actions, sans requête au moteur local et sans import Studio.

Un modèle textuel sans outils de fichiers ne peut pas produire de façon fiable un
fichier binaire `.schem` en répondant uniquement en texte. Le prompt demande dans
ce cas d'annoncer la limite et de proposer un moyen de génération concret,
**sans fabriquer de lien de téléchargement fictif**.

Les cartes-boutons ne lancent aucune IA toutes seules et ne transmettent pas tes demandes
à un service API et n'envoie pas le schematic dans le monde Minecraft :
**tu télécharges et places le fichier toi-même**.

## Parcours B — GabCon BuildAI et son moteur local

Cette section de l'interface est **complètement indépendante** de la génération ChatGPT.

1. Choisis l'entrée moteur avec les deux boutons **Python DSL (.py)** ou **Opérations (.json)**.
   Le moteur accepte du Python DSL conforme au projet ou le JSON d'opérations
   `gabcon-block-ops-v1`. Il **n'exécute pas** les fichiers binaires `.schem`,
   `.nbt`, `.litematic`, les datapacks ZIP, les fichiers `.mcfunction` ou les plans `.md`.
2. Colle ou importe le blueprint dans l'éditeur local. Ce choix ne change **jamais**
   le format sélectionné pour le prompt ChatGPT dans le parcours A.
3. Lance **Générer avec BuildAI** : le moteur Python du PC valide le fichier, place les
   blocs dans la grille et crée les rendus et un vrai `final.schem`.
4. Utilise la vue 3D et les exports de la colonne **Rendu du moteur BuildAI**.
   Les durées, la seed et le choix Rapide/Qualité concernent uniquement ce moteur.

Un bouton **Importer un brief ChatGPT** est placé dans le parcours A pour restaurer
le cahier des charges `gabcon-build-brief-v1` ; le bouton **Importer .py / .json**
du parcours B est réservé aux blueprints locaux. Ces deux imports ne se confondent pas.

Le moteur local tourne sur `127.0.0.1` et ne doit recevoir que du code de confiance.
Le parcours A n'a pas besoin que le moteur local fonctionne : il se contente de
copier un prompt, et ChatGPT crée le fichier directement dans sa conversation.

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

# COMMAND_PALETTE — Plan d'implementation final (Ctrl+P)

## Objectif

Implementer une **Command Palette TUI** (style VS Code), ouverte avec **Ctrl+P**, affichee au centre de l'ecran comme une modal, avec :
- recherche **fuzzy**
- navigation clavier complete
- execution d'actions existantes (filtres, tris, pages/overlays, actions globales)
- integration sans casser les flows TUI existants

---

## Decisions produit figees (validees)

- Trigger d'ouverture : **Ctrl+P**
- Scope V1 : **toutes les commandes utiles actuelles** (filtres + tris + pages + actions)
- Recherche : **fuzzy search**
- UI : **modal centree plein ecran (style VS Code)**

---

## Contraintes techniques importantes (codebase actuelle)

- Le routing des overlays est centralise dans `src/app.js` (chaine de priorite unique).
- `P` ouvre deja Settings (`src/key-handler.js`) -> **gerer le conflit avec Ctrl+P proprement**.
- `Y` est actuellement utilise pour `Install Endpoints` (pas un tri tier).
- Les tris hotkeys actifs sont : `R O M L A S C H V B U`.
- Le moteur supporte deja `sortColumn: 'tier'` (`src/utils.js`) -> commande palette possible meme sans hotkey dediee.
- Le rendu tourne a ~12 FPS -> eviter recalcul fuzzy lourd a chaque frame.
- Tests unitaires centraux dans `test/test.js` + tests hotkeys existants.
- Obligations projet apres feature :
  - `pnpm test`
  - `pnpm start`
  - corriger puis rerun jusqu'a vert

---

## Mode d'utilisation de cette checklist (pour l'IA pendant le dev)

- Cocher `[x]` **uniquement** quand le critere de validation de l'etape est atteint.
- Garder **une seule etape "en cours"** a la fois.
- Ne pas cocher sur intention; cocher sur preuve (code + test + verif).
- En cas de blocage : noter le blocage sous l'etape concernee avant de continuer.
- Ne pas skipper les etapes docs/tests/changelog.

---

## Plan executable (checklist detaillee)

## Phase 0 - Preflight & cadrage technique

- [ ] Relire `src/app.js`, `src/key-handler.js`, `src/overlays.js`, `src/render-table.js`, `src/utils.js`.
- [ ] Verifier l'ordre exact de priorite des overlays dans la boucle de rendu.
- [ ] Lister tous les hotkeys existants (et confirmer les conflits).
- [ ] Valider le comportement actuel de `P`, `Y`, `Esc`, `Ctrl+C`.
- [ ] Ecrire un mini "mapping de commandes" de reference avant code.

**Critere de validation**
- Cartographie clavier + overlays documentee et sans ambiguite.

---

## Phase 1 - Modele d'etat (state) pour la palette

### Fichier principal
- `src/app.js`

### Taches
- [ ] Ajouter les champs d'etat palette :
  - `commandPaletteOpen: false`
  - `commandPaletteQuery: ''`
  - `commandPaletteCursor: 0`
  - `commandPaletteScrollOffset: 0`
  - `commandPaletteResults: []`
- [ ] Ajouter un helper de reset palette (query/cursor/scroll/results).
- [ ] Verifier que l'etat palette n'interfere pas avec les autres overlays.

**Critere de validation**
- L'application demarre sans erreur avec le nouvel etat, palette fermee par defaut.

---

## Phase 2 - Registry de commandes (source de verite)

### Nouveau fichier
- `src/command-palette.js` (registry + mapping execution)

### Taches
- [ ] Creer un type de commande uniforme :
  - `id`
  - `label`
  - `category`
  - `shortcutLabel`
  - `keywords[]`
  - `run(ctx)` (action)
- [ ] Ajouter les categories V1 :
  - Filters
  - Sort
  - Pages
  - Actions
  - Appearance
  - Session
- [ ] Injecter les actions existantes (sans duplication fragile).
- [ ] Prevoir les commandes “palette-only” (ex: sort tier) avec label clair.
- [ ] Ajouter commentaires `📖` pertinents et JSDoc `@file/@description/@exports`.

**Critere de validation**
- Registry complet, lisible, sans logique UI dans ce module.

---

## Phase 3 - Fuzzy search (logique pure testable)

### Fichier recommande (conformite architecture tests)
- `src/utils.js`

### Taches
- [ ] Ajouter une fonction de matching fuzzy (ordre des caracteres).
- [ ] Ajouter un score robuste (base + bonus contiguite + bonus debut de mot).
- [ ] Ajouter extraction des positions matchees (pour highlight UI).
- [ ] Ajouter fonction de ranking des commandes :
  - score desc
  - tie-break stable (categorie puis label)
- [ ] Gerer query vide (retour trie "par defaut UX").
- [ ] Gerer query whitespace/casse/accentuation (normalisation minimale).
- [ ] Exporter ces helpers proprement.

**Critere de validation**
- Les fonctions fuzzy sont pures, deterministes, et exploitables sans dependance TUI.

---

## Phase 4 - Rendu overlay Command Palette

### Fichier
- `src/overlays.js`

### Taches
- [ ] Ajouter `renderCommandPalette()`.
- [ ] UI modal centree :
  - header (“Command Palette”)
  - input `> query▏`
  - liste groupee par categories
  - raccourci affiche a droite
  - footer d'aide (`↑↓`, `Enter`, `Esc`)
- [ ] Integrer highlight des caracteres matches.
- [ ] Ajouter scroll interne (avec `sliceOverlayLines` / helpers existants).
- [ ] Ajouter etat vide (“No command found”).
- [ ] S'assurer que la palette respecte largeur terminal + nettoyage `\x1b[K`.
- [ ] Ajouter une couleur dediee dans `theme` (`overlayBg.commandPalette`).

### Fichier complementaire
- `src/theme.js`
- [ ] Ajouter la teinte `commandPalette` en dark/light.

**Critere de validation**
- La palette se rend correctement, lisible en dark/light, sans glitch de layout.

---

## Phase 5 - Routing de rendu principal

### Fichier
- `src/app.js`

### Taches
- [ ] Injecter le renderer palette dans la chaine de rendu overlay.
- [ ] Positionner la priorite palette de facon explicite (et coherente avec overlays existants).
- [ ] Eviter recalcul inutile `visibleSorted` quand palette ouverte si non necessaire.
- [ ] Verifier qu'aucun ecran existant n'est casse (settings/help/changelog/etc).

**Critere de validation**
- Quand palette ouverte, seul son rendu est actif; fermeture restaure la vue precedente.

---

## Phase 6 - Gestion clavier (input handling)

### Fichier
- `src/key-handler.js`

### Taches
- [ ] Intercepter `Ctrl+P` tot dans la fonction (avant `P` settings).
- [ ] Comportement `Ctrl+P` :
  - ouvre palette si fermee
  - ferme palette si deja ouverte (toggle)
- [ ] Ajouter bloc “si `state.commandPaletteOpen`” (swallow des touches) :
  - `Esc` ferme
  - `↑/↓` navigation
  - `PgUp/PgDn/Home/End` navigation rapide
  - `Backspace` edite query
  - caracteres imprimables ajoutent a query
  - `Enter` execute commande selectionnee
  - `Ctrl+C` sort l'app
- [ ] Empecher `P` simple d'ouvrir settings quand `ctrl=true`.
- [ ] Recalculer resultats fuzzy uniquement quand query/cursor change (pas chaque frame).

**Critere de validation**
- Aucun conflit clavier observable entre `Ctrl+P` et les hotkeys existants.

---

## Phase 7 - Dispatch d'actions (execution des commandes)

### Fichiers
- `src/command-palette.js`
- `src/key-handler.js` (ctx passe au dispatcher)

### Taches
- [ ] Construire un `context` minimal d'execution (state + helpers deja disponibles).
- [ ] Mapper les commandes vers les actions existantes :
  - cycle tier/provider/configured
  - tris
  - ouverture overlays
  - cycle theme/tool/ping
  - reset view
  - favorite toggle
- [ ] Fermer palette apres execution.
- [ ] Rafraichir les listes visibles/sort/cursor si la commande modifie la vue.
- [ ] Gerer les commandes indisponibles (si besoin) sans crash.

**Critere de validation**
- Chaque commande execute l'action attendue et l'UI reste coherente.

---

## Phase 8 - Inventaire commandes V1 (a implementer)

### Filters
- [ ] Show all tiers
- [ ] Tier S+
- [ ] Tier S
- [ ] Tier A+
- [ ] Tier A
- [ ] Tier A-
- [ ] Tier B+
- [ ] Tier B
- [ ] Tier C
- [ ] Cycle provider filter
- [ ] Toggle configured-only

### Sort
- [ ] Sort by rank
- [ ] Sort by provider
- [ ] Sort by model
- [ ] Sort by latest ping
- [ ] Sort by avg ping
- [ ] Sort by SWE
- [ ] Sort by context
- [ ] Sort by health
- [ ] Sort by verdict
- [ ] Sort by stability
- [ ] Sort by uptime
- [ ] Sort by tier (palette-only, optionnel mais recommande)

### Pages / Overlays
- [ ] Open settings
- [ ] Open help
- [ ] Open changelog
- [ ] Open smart recommend
- [ ] Open install endpoints
- [ ] Open feedback

### Actions globales
- [ ] Cycle tool mode
- [ ] Cycle theme
- [ ] Cycle ping mode
- [ ] Toggle favorite (row selectionnee)
- [ ] Reset view settings

**Critere de validation**
- La palette expose reellement “tout ce qu'on peut faire” cote utilisateur.

---

## Phase 9 - Tests unitaires & hotkeys

### Fichier tests
- `test/test.js` (principal)
- `test/tui-hotkeys.test.js` (si extension utile)

### Taches
- [ ] Ajouter tests fuzzy :
  - match basique
  - no match
  - bonus contiguite
  - bonus debut de mot
  - tri stable des resultats
- [ ] Ajouter tests mapping commandes :
  - commande -> action attendue
  - commandes inconnues -> comportement sur
- [ ] Ajouter tests clavier :
  - `Ctrl+P` ouvre/ferme
  - `P` simple ouvre toujours settings
  - `Esc` ferme palette sans effet de bord
  - `Enter` execute la bonne commande

**Critere de validation**
- Les tests couvrent fuzzy + routing clavier + dispatch principal.

---

## Phase 10 - Tests manuels TUI (agent-tui)

### Scenarios minimaux
- [ ] Ouvrir palette via `Ctrl+P` (visible au centre).
- [ ] Taper query (`fil`, `sort`, `settings`) -> resultats filtres.
- [ ] Naviguer `↑↓` + `Enter` -> action executee.
- [ ] `Esc` ferme palette.
- [ ] Verifier qu'apres execution l'ecran cible est correct.
- [ ] Verifier non-regression : Settings/Help/Recommend/Changelog still OK.

**Critere de validation**
- Le comportement visuel et interactif est stable en conditions reelles TUI.

---

## Phase 11 - Documentation & changelog

### README
- [ ] Ajouter `Ctrl+P` dans la table des hotkeys.
- [ ] Ajouter une feature “Command Palette” dans la section Features.
- [ ] Decrire brievement le fuzzy search.

### Aide in-app
- [ ] Ajouter la ligne `Ctrl+P` dans `renderHelp()`.

### CHANGELOG
- [ ] Ajouter entree sous la bonne version (`Added`/`Changed`).

**Critere de validation**
- Les docs utilisateur refletent la feature livree.

---

## Phase 12 - Qualite finale obligatoire

- [ ] Lancer `pnpm test`.
- [ ] Corriger toutes les regressions.
- [ ] Relancer `pnpm test` jusqu'a vert.
- [ ] Lancer `pnpm start` et verifier runtime sans erreur.
- [ ] Corriger/rerun `pnpm start` si besoin.
- [ ] Verifier une derniere fois la Command Palette en usage reel.
- [ ] Executer le son de fin : `afplay ~/sonclaude.wav &>/dev/null &` (quand implementation terminee).

**Critere de validation**
- Build/test/runtime OK + UX palette validee.

---

## Details d'implementation critiques (anti-regression)

- Toujours verifier `key.ctrl` pour differencier `Ctrl+P` de `P`.
- Le bloc palette doit etre traite avant les hotkeys globales.
- Ne pas faire de “fake keypress” en chaine : appeler des helpers d'action partages.
- Garder une source de verite unique pour l'etat de tri/filtre (`state` + helpers existants).
- Eviter recalcul fuzzy dans le render loop; faire le recalcul sur evenement input.
- Respecter les conventions projet :
  - commentaires `📖` quand utile
  - JSDoc complet pour nouveaux modules
  - style/ton coherent avec le code existant

---

## Definition of Done (DoD)

- [ ] `Ctrl+P` ouvre une modal palette centree.
- [ ] Recherche fuzzy fonctionnelle + highlight.
- [ ] Navigation clavier complete.
- [ ] Execution des commandes principales sans casse.
- [ ] Pas de conflit avec hotkeys existants (`P`, `Y`, etc.).
- [ ] Aide/README/changelog a jour.
- [ ] `pnpm test` green.
- [ ] `pnpm start` sans runtime error.
- [ ] Verification visuelle agent-tui validee.

---

## Annex - Mapping commandes/hotkeys (reference rapide)

- Filters: `T`, `D`, `E`
- Sort: `R`, `O`, `M`, `L`, `A`, `S`, `C`, `H`, `V`, `B`, `U` (+ `tier` palette-only possible)
- Pages: `P`, `K`, `N`, `Q`, `Y`, `I`
- Actions: `Z`, `G`, `W`, `F`, `Shift+R`

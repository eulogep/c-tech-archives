# Système de design « Sceau »

Ce document décrit la charte de l’interface v2 de C-Tech Archives : son principe, ses jetons, ses composants et les règles qui la gardent compatible avec la politique de sécurité.

## Principe

Une archive est un document que l’on scelle. Le motif du **sceau** structure toute l’interface :

- chaque archive porte un sceau génératif unique, dérivé de sa référence ;
- la marque elle-même est un sceau (graine `BRAND_SEAL_SEED` dans `archives/presentation.py`) ;
- l’intégrité SHA-256 est présentée comme l’état du sceau : conforme, rompu ou jamais revérifié ;
- la barre latérale reste « coffre » (encre profonde) dans les deux thèmes ; les surfaces de travail sont du papier chaud en clair et de l’encre en sombre.

## Sceau génératif

`archives/presentation.py` (`seal_geometry`, `render_seal`) et `static/js/app.js` (`sealSvg`) implémentent le même algorithme :

1. SHA-256 de la référence (espaces de bord retirés) ;
2. octet 0 → teinte de fond, octet 1 → teinte d’accent, octet 7 → rotation ;
3. trois anneaux de 6, 12 et 18 segments en symétrie miroir ; chaque segment reçoit l’une de quatre opacités, à partir de 2 bits pris dans la suite de l’empreinte ;
4. couronne de 48 graduations et noyau central.

Le sceau ne dépend **jamais** de l’empreinte du fichier : il identifie un dossier sans rien révéler de son contenu. Il est décoratif (`aria-hidden`) sauf si un libellé est fourni.

## Jetons

Toutes les valeurs sont des propriétés personnalisées sur `:root`, redéfinies pour `[data-theme="dark"]` et pour `prefers-color-scheme: dark` lorsque l’utilisateur n’a pas choisi le thème clair.

| Famille | Jetons |
|---|---|
| Surfaces | `--bg`, `--surface`, `--surface-2`, `--surface-3`, `--surface-sunken`, `--surface-glass` |
| Texte | `--text`, `--text-2`, `--text-3` |
| Accent | `--accent`, `--accent-strong`, `--accent-soft`, `--accent-ring`, `--on-accent` |
| États | `--success`, `--warning`, `--danger`, `--info` (+ variantes `-soft`) |
| Confidentialité | `--level-public` (vert), `--level-internal` (ambre), `--level-confidential` (cramoisi) |
| Graphiques | `--chart-1…4`, `--chart-track`, `--heat-0…4` |
| Forme | `--radius-xs…xl`, `--radius-pill`, `--shadow-1…3`, `--focus` |
| Mouvement | `--ease-out`, `--ease-spring`, `--duration` |

Typographies : **Fraunces** (titres, chiffres clés, axe optique), **Geist** (interface), **Geist Mono** (références, empreintes, adresses IP). Les fichiers WOFF2 latins et leurs licences OFL sont dans `static/fonts/`.

## Composants

| Composant | Classes principales |
|---|---|
| Coquille | `.app-shell`, `.sidebar`, `.nav-link`, `.clearance`, `.topbar`, `.user-menu` |
| Boutons | `.button`, `.button-secondary`, `.button-ghost`, `.button-danger`, `.button-compact`, `.row-action`, `.icon-button` |
| Badges | `.badge-active`, `.badge-archived`, `.badge-public`, `.badge-internal`, `.badge-confidential`, `.badge-role`, `.badge-tech` |
| Cartes | `.card`, `.card-flush`, `.kpi`, `.stat-tile`, `.archive-card`, `.roadmap-item` |
| Formulaires | `.form-field`, `.choice-cards`, `.choice-card`, `.dropzone`, `.password-field`, `.strength` |
| Données | `.data-table`, `.cell-archive`, `.timeline`, `.event-list`, `.feed`, `.rank-list` |
| Graphiques | `.bar-chart`, `.donut`, `.integrity-ring`, `.heatmap`, `.scope-meter`, `.sparkline` |
| Dialogues | `.palette`, `.sheet`, `.onboarding-dialog` |
| Retours | `.toast-stack`, `.message`, `.alert`, `.empty-state` |

Les balises de gabarit intégrées (`archives/templatetags/archive_ui.py`) sont `{% icon %}`, `{% seal %}`, `{% brand_seal %}`, et les filtres `initials`, `tone_of`, `kind_of` et `kind_label`.

## Règles de compatibilité CSP

La politique est `default-src 'self'; script-src 'self'; style-src 'self'` (voir `config/middleware.py`). Elle impose :

- **aucun script en ligne** : les données passent par `json_script` (non exécuté) et les attributs `data-*` ;
- **aucun attribut `style=""`** : les dimensions dynamiques sont des attributs SVG (`width`, `x`, `stroke-dasharray`) ou des propriétés CSSOM posées par `app.js` ;
- **nombres SVG non localisés** : la locale française écrirait `187,5`. Les géométries passent donc par `svg_number()` avant d’arriver au gabarit ;
- **aucune ressource tierce** : polices, icônes et images sont servies par l’application.

Le test `test_templates_contain_no_inline_script_or_style_attribute` vérifie ces règles sur tous les gabarits.

## Accessibilité

- Lien d’évitement, repères (`nav`, `main`, `aside`), titres hiérarchisés.
- Focus visible partout (`:focus-visible` avec anneau d’accent).
- Graphiques : `role="img"` avec libellé, `<title>` par barre ou cellule, tableau de données masqué visuellement pour le flux mensuel.
- Palette de commandes au motif combobox et listbox (`aria-activedescendant`, `aria-selected`).
- Notifications en `role="status"`, ou `role="alert"` pour les erreurs, qui ne se ferment alors pas automatiquement.
- Mouvements désactivés sous `prefers-reduced-motion`, bordures visibles en `forced-colors`.
- Tout fonctionne sans JavaScript : menu `details`, formulaires GET et POST, liens de bascule de vue.

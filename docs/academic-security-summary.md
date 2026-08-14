# Synthèse académique de sécurité

Cette synthèse réutilise les constats et le modèle de menace de T-014. Elle ne remplace pas la revue détaillée [`security-review.md`](security-review.md), qui demeure la source de résultats de test et de risques résiduels.

## Actifs à protéger

| Actif | Enjeu | Protection MVP |
|---|---|---|
| Identité et sessions | Empêcher l’accès non authentifié et les redirections externes | Session Django, compte actif, `next` contrôlé, logout POST/CSRF |
| Métadonnées d’archives | Éviter la divulgation de titres, références et classification | RBAC, QuerySets filtrés, 404 anti-inférence |
| Fichiers | Éviter accès direct, traversal et upload non contrôlé | Stockage privé, noms UUID, validation serveur et `FileResponse` autorisé |
| Intégrité documentaire | Détecter une différence de contenu | Référence SHA-256, vérification POST et audit du résultat |
| Journal d’audit | Conserver le contexte métier sans donnée sensible | Service append-only applicatif, détails minimaux et Admin read-only |
| Configuration | Éviter débogage, secret ou hôte de production mal configuré | Variables d’environnement, `check --deploy`, hôtes explicites et wildcard refusé hors DEBUG |

## Menaces et contrôles

| Menace | Contrôles effectivement appliqués | Preuve automatisée |
|---|---|---|
| IDOR et énumération d’identifiants | QuerySets visibles avant liste, recherche, détail, téléchargement et intégrité ; 404 hors périmètre | `RBAC-*`, `HARD-001` à `HARD-004` |
| Mass assignment | Formulaires à liste blanche ; champs serveur imposés | `HARD-005`, tests CRUD |
| XSS et saisies malveillantes | Échappement Django, pas de `safe` sur données utilisateur, ORM | `HARD-006` à `HARD-008`, `SEARCH-020` à `SEARCH-021` |
| CSRF | POST avec jeton pour mutations, logout et intégrité | `HARD-021` à `HARD-024` |
| Traversal et exposition de fichiers | UUID, stockage privé et absence d’URL publique | `HARD-009` à `HARD-011`, `FILE-*` |
| Accès audit non autorisé | Vue audit réservée à l’Administrateur/superuser | `AUDIT-020` à `AUDIT-030`, `HARD-012` à `HARD-014` |
| Altération de fichier | SHA-256 et conservation de la référence historique | `HASH-*`, `HARD-018` |
| Configuration production trop permissive | Secret requis, DEBUG interdit, hôtes explicites et `*` refusé | `HARD-025`, `HARD-026` |

## Risques résiduels

Le MVP ne fournit pas de MFA, rate limiting intégré, antivirus, chiffrement applicatif au repos, signature numérique, SIEM/WORM, ACL par service ou individu, versioning documentaire, sauvegarde/restauration, pentest externe ni certification OWASP. SHA-256 détecte une différence entre un fichier et sa référence, mais ne protège pas contre un acteur capable de modifier simultanément le stockage et la base.

## Positionnement de production

Le projet est un MVP fonctionnel et vérifié. Une production réelle nécessite au minimum une décision C-Tech sur l’identité, les hôtes, HTTPS, reverse proxy, sauvegardes, gestion de secrets, conservation, antivirus, supervision, incident et conformité. Les contrôles de développement ne doivent pas être interprétés comme une garantie de production immédiate.

# Fiche de révision finale — soutenance C-Tech Archives

Utilisez cette fiche pour expliquer les choix du MVP avec des termes précis, un exemple concret et une limite assumée.

| Concept | Définition | Pourquoi utilisé | Où dans le projet | Exemple | Limite |
|---|---|---|---|---|---|
| Django MTV | Variante Django de MVC : modèles, templates et vues | Structurer un monolithe web cohérent | Applications `accounts`, `archives`, `audit`, `dashboard` | Une vue liste rend un template avec un QuerySet | Pas une architecture microservices |
| ORM | Couche qui transforme des objets Python en requêtes relationnelles | Réduire le SQL construit à la main et centraliser les requêtes | Modèles et QuerySets Django | Filtrer les archives visibles par confidentialité | Ne remplace pas une bonne règle d’autorisation |
| PostgreSQL | Base relationnelle transactionnelle | Conserver relations, contraintes et audit | Configuration `DATABASES` | `PROTECT` empêche de casser une relation référencée | Sauvegarde et restauration hors MVP |
| Migration | Versionnement du schéma de base | Rendre les évolutions reproductibles | Dossiers `migrations/` | `python manage.py migrate` | T-016 ne crée aucune migration |
| ModelForm | Formulaire Django lié à un modèle avec liste blanche | Valider la saisie sans exposer les champs techniques | `archives.forms.ArchiveForm` | `uploaded_by` n’est pas fourni par le navigateur | La validation HTML seule ne suffit pas |
| Session | Identité conservée côté navigateur via cookie | Adaptée à l’interface Django server-rendered | Auth Django, login/logout | Une connexion donne accès au dashboard | Pas de MFA dans le MVP |
| CSRF | Jeton prouvant qu’un POST vient de la page attendue | Protéger les opérations mutables contre un autre site | Formulaires Django, logout et intégrité | POST sans token refusé | Ne protège pas une autorisation mal conçue |
| RBAC | Contrôle d’accès par rôle | Adapter la visibilité documentaire aux responsabilités | `archives.permissions` | Agent voit PUBLIC/INTERNAL, pas CONFIDENTIAL | Pas d’ACL individuelle ou par service |
| QuerySet | Requête Django paresseuse sur les objets | Filtrer le périmètre avant affichage ou action | `visible_archives_for` | Recherche limitée aux archives visibles | L’interface seule ne suffit pas |
| 404 anti-inférence | Réponse générique pour une ressource hors périmètre | Ne pas confirmer l’existence d’une archive confidentielle | Mixins et vues archives | Consultant demandant CONFIDENTIAL reçoit 404 | Ne masque pas tous les signaux d’infrastructure |
| FileField | Champ Django qui référence un fichier stocké hors de la base | Lier métadonnées et document sans stocker le binaire dans PostgreSQL | `Archive.file` | PDF synthétique associé à une archive | Pas de versioning de contenu |
| Stockage privé | Répertoire non publié par URL publique | Éviter un contournement du RBAC par lien direct | `PrivateArchiveStorage` | Téléchargement via `FileResponse` contrôlé | Pas de stockage objet ou chiffrement au repos |
| AuditLog | Événement métier structuré | Tracer les opérations sensibles réussies | `audit.models`, `audit.services` | Création et téléchargement journalisés | Append-only applicatif, pas WORM externe |
| SHA-256 | Hash de 256 bits, non réversible | Comparer le contenu actuel à une référence | `archives.integrity` | `VALID` ou `MISMATCH` | Ni chiffrement ni signature numérique |
| XSS | Injection de script dans une page | Protéger les utilisateurs et l’interface | Templates Django et formulaires | Titre HTML échappé au rendu | Éviter aussi l’usage imprudent de `safe` |
| Injection SQL | Modification de requête par une entrée malveillante | Préserver les données | ORM Django et formulaires | Recherche SQL-like traitée comme texte | L’ORM ne corrige pas une autorisation absente |
| IDOR | Accès à un objet par identifiant sans contrôle de droit | Éviter qu’une URL devinée expose une archive | QuerySets RBAC, vues détail/download | ID CONFIDENTIAL hors rôle donne 404 | Nécessite une règle visible cohérente partout |
| Variables d’environnement | Paramètres hors code : secrets, DB, hôtes | Séparer le code des secrets et profils | `.env.example`, `config.settings` | Secret Django absent de Git | Nécessite une vraie gestion de secrets en production |
| HSTS | En-tête imposant HTTPS au navigateur | Réduire les retours vers HTTP après validation | Paramètres `DJANGO_SECURE_HSTS_*` | Production simulée avec HSTS | À activer seulement après HTTPS complet |

## Réponses pièges à mémoriser

> **SHA-256 chiffre-t-il le document ?** Non. Il calcule une empreinte de comparaison ; le fichier ne peut pas être retrouvé depuis le hash.

> **Django empêche-t-il toutes les attaques automatiquement ?** Non. Django apporte des mécanismes, mais les politiques RBAC, QuerySets, formulaires, stockage et paramètres doivent être conçus et testés.

> **Cacher un bouton suffit-il à protéger une action ?** Non. L’interface est seulement ergonomique. Les vues serveur vérifient toujours l’utilisateur et le périmètre.

> **Le MVP est-il certifié OWASP ou prêt production immédiatement ?** Non. Il possède une revue de sécurité et 263 tests, mais pas de pentest externe, de certification, ni toutes les mesures d’exploitation nécessaires.

## Phrase de conclusion

> « Le MVP est fonctionnel, testé et documenté. Ses contrôles principaux sont appliqués côté serveur, et ses limites sont explicitement présentées comme des perspectives à valider avec C-Tech. »

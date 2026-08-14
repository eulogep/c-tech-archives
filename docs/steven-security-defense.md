# Défense sécurité — fiche courte pour Steven

## Réponse générale à retenir

> Non, l’application n’est pas « totalement sécurisée » : aucun système réaliste ne doit être présenté ainsi. Le MVP applique des contrôles mesurables et testés — authentification, autorisation serveur, stockage privé, validation des fichiers, CSRF, ORM, audit et contrôle d’intégrité — tout en documentant clairement les limites restantes, notamment l’antivirus, le brute-force, l’immutabilité externe des logs et l’infrastructure de production.

## Les onze points à savoir expliquer

| Sujet | Réponse courte mémorisable |
|---|---|
| 1. Authentification | Django gère les mots de passe hachés et les sessions. Un compte inactif ne peut pas se connecter, et un `next` externe est neutralisé. |
| 2. RBAC | Les rôles métier sont Administrateur, Agent et Consultant. La politique est centralisée, puis appliquée dans les QuerySets et les vues. |
| 3. 403 vs 404 | 404 est utilisé lorsque l’utilisateur ne doit pas savoir qu’une archive existe. 403 est utilisé quand il connaît l’objet mais n’a pas le droit d’exécuter une action. |
| 4. Stockage privé | Les documents ne sont pas servis par `/media/`. Ils sont stockés hors de l’exposition publique et téléchargés uniquement via une vue Django contrôlée. |
| 5. Upload allowlist | Le serveur vérifie extension, taille, type déclaré et signatures simples. Le nom physique est un UUID généré côté serveur. |
| 6. CSRF | Les actions POST sensibles nécessitent un jeton CSRF. Une requête externe mutable sans jeton est rejetée. |
| 7. ORM et injection | Les recherches utilisent l’ORM Django, pas de SQL brut. Une chaîne comme `' OR 1=1 --` reste une donnée de recherche. |
| 8. XSS | Les templates Django échappent les métadonnées et les requêtes. Les contenus `<script>` sont affichés comme texte, pas exécutés. |
| 9. Audit append-only | Les événements métier sont créés par un service central. L’interface audit est réservée à l’Administrateur et Django Admin interdit ajout, modification et suppression. |
| 10. SHA-256 | Le checksum est calculé après stockage du fichier. Une vérification compare le fichier actuel à cette référence ; un mismatch ne remplace jamais la référence historique. |
| 11. Limites | Pas de MFA, antivirus, rate limiting intégré, signature numérique, WORM, SIEM ou durcissement reverse proxy complet dans le MVP. |

## Trois questions fréquentes

### Pourquoi le checksum ne suffit-il pas contre tout ?

Parce qu’il détecte une différence entre le fichier actuel et la référence stockée. Une personne contrôlant à la fois le stockage et la base pourrait modifier les deux. Une signature numérique, un stockage immuable ou une infrastructure séparée serait nécessaire pour une garantie plus forte.

### Pourquoi le Consultant reçoit-il parfois 404 et non 403 ?

Pour éviter une fuite par inférence. Si une archive `INTERNAL` ou `CONFIDENTIAL` renvoyait 403 au Consultant, cela confirmerait déjà son existence. Le 404 garde cette information non divulguée.

### Que faut-il faire avant une vraie mise en production ?

Configurer les secrets et hôtes réels hors Git, activer HTTPS, cookies secure et HSTS avec prudence, régler les limites du reverse proxy, ajouter un audit de dépendances CI, décider d’une protection anti-brute-force, puis valider sauvegardes, monitoring et gestion des incidents.

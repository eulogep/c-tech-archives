# Plan de soutenance académique

Ce plan prépare la matière source d’une soutenance. Il ne constitue pas un PowerPoint ni un PDF et peut être adapté à la durée demandée par le jury.

| Séquence | Message à transmettre | Preuve ou support recommandé |
|---:|---|---|
| 1. Contexte / problème | Les archives doivent être centralisées, retrouvées et protégées selon leur sensibilité. | Exemple de besoin documentaire, sans donnée C-Tech réelle |
| 2. Objectifs | Réunir gestion de métadonnées, contrôle d’accès, traçabilité et intégrité dans un MVP vérifiable. | `README.md` et `final-feature-matrix.md` |
| 3. Analyse du besoin | Distinguer rôles, confidentialité, référentiels, fichiers privés et conservation. | `assumptions.md`, `technical-validation-questions.md` |
| 4. Architecture | Présenter le monolithe Django modulaire, PostgreSQL et le stockage privé séparé. | `architecture-final.md` et diagramme Mermaid |
| 5. Modèle de données | Expliquer `User`, référentiels, `Archive`, `AuditLog`, relations `PROTECT` et statuts. | Diagramme de données final |
| 6. Fonctionnalités | Montrer authentification, CRUD sans DELETE, recherche, fichiers, audit, intégrité et interface. | `final-feature-matrix.md` |
| 7. Sécurité | Expliquer RBAC, QuerySets, 404 anti-inférence, CSRF, validation, audit et SHA-256. | `security-review.md`, `final-rbac-matrix.md` |
| 8. Démonstration | Présenter Consultant, Agent puis Administrateur sur données synthétiques. | `demo-script.md`, application locale |
| 9. Tests | Montrer 255 tests automatisés et les groupes de couverture. | `final-test-matrix.md`, sortie `manage.py test` |
| 10. Limites | Reconnaître les limites techniques et de production sans sur-promesse. | README, revue de sécurité |
| 11. Perspectives | Présenter MFA, antivirus, versioning, ACL fine, SIEM/WORM, stockage objet et monitoring comme évolutions. | README et `technical-validation-questions.md` |
| 12. Conclusion | Le MVP est fonctionnel, documenté, démontrable et prêt pour une revue humaine finale, non pour une promesse de production immédiate. | Synthèse du MVP status |

## Fil conducteur conseillé

> « Le projet ne cherche pas seulement à déposer un fichier. Il vérifie qui agit, quel document est visible, comment le fichier est protégé, ce qui est tracé et comment l’intégrité est contrôlée. »

## Répartition temporelle indicative

Pour une présentation de 10 minutes, consacrez environ deux minutes à l’architecture et aux données, trois minutes aux fonctionnalités et à la démonstration, deux minutes à la sécurité, une minute aux tests, puis deux minutes aux limites, perspectives et questions. Ajustez la démonstration avec la version 2 minutes ou 5–7 minutes selon le temps effectivement accordé.

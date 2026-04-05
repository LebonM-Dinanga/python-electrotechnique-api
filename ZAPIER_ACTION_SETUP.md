# Zapier Action Setup

Zapier ne se cree pas dans ce repo. C'est une action externe a rebrancher dans le builder GPT.

## Role recommande de Zapier dans ElectroGPT

N'utilise Zapier que pour les actions de sortie ou d'automatisation, par exemple :

- exporter un resultat vers Google Docs
- enregistrer un rapport
- creer une fiche de synthese
- envoyer une note ou un resume vers un outil tiers

Ne l'utilise pas pour :

- calculer
- simuler
- faire un diagnostic
- rechercher des articles
- generer un workflow academique

Ces taches doivent rester sur les actions ElectroGPT specialisees ou sur Wolfram.

## Regle de selection a mettre dans les instructions du GPT

```text
Utilise Zapier uniquement si l'utilisateur demande explicitement une action d'export, d'enregistrement, d'envoi, de synchronisation ou de creation de document dans un outil externe. N'utilise jamais Zapier pour calculer, simuler, diagnostiquer ou rechercher.
```

## Ordre recommande dans le builder GPT

Ajoute Zapier apres les actions ElectroGPT techniques.

Ordre conseille :

1. Wolfram
2. Research
3. Simulation
4. Realtime
5. Diagnosis
6. Academic
7. Thesis
8. Live
9. Zapier

## Exemples de demandes qui doivent aller vers Zapier

```text
Exporte ce plan de TFE dans Google Docs
```

```text
Enregistre ce diagnostic dans un document Google Docs
```

```text
Envoie ce resume bibliographique dans mon dossier Google Drive via Zapier
```

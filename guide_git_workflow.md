# Guide Git - Comprendre et gérer les commits

Ce guide couvre : comment fonctionne Git avec les s fichiers de modèle dispersés, comment committer les changements, et comment mettre en place un nouveau projet pour de futurs fichiers.

---

## 1. Comprendre le fonctionnement de base


Un dépôt Git (repo) = un dossier spécifique sur le disque, lié à GitHub.

```
/home/classic_ops/classic-model/     ← repo
```

Git surveille **uniquement** ce qui se trouve dans ce dossier (et ses sous-dossiers). Si un fichier est ailleurs sur le disque même si il est  modifier tous les jours, Git ne le voit pas et ne peut rien en faire.

### Le cas des fichiers de modèle dispersés

Mes fichiers de travail (init, job_options, siteinfo) sont générés/modifiés dans d'autres dossiers :

| Fichier | Emplacement réel (source) |
|---|---|
| `CA-MonJ_init.nc` | `/home/classic_ops/quick_start_test_runs/all_sites_container_test_1/CA-MonJ/` |
| `job_options_daily.txt` | `.../CA-MonJ/job_configs/` |
| `siteinfo.yaml` | `/home/classic_ops/CLASSIC/inputFiles/FLUXNETsites_12PFT/CA-MonJ/` |

Le repo Git, lui, est ailleurs :
```
/home/classic_ops/classic-model/CA-MonJ/
```

**Donc chaque fois que je modifies un fichier source, il faut le RECOPIER dans le repo avant que Git puisse voir le changement.** C'est l'étape qui peut causer le message trompeur `nothing to commit, working tree clean` (Git dit "rien à committer" parce qu'il compare le repo à lui-même, pas aux fichiers sources).

### Le cycle complet en 3 étapes

 Depuis le bash
```
1. COPIER   (cp)      : fichier source → dossier du repo
2. STAGER   (git add)  : dire à Git "inclus ce fichier dans le prochain commit"
3. COMMIT   (git commit) : enregistrer un instantané (snapshot) avec un message
4. PUSH     (git push) : envoyer ces commits vers GitHub
```

---

## 2. Routine pour committer les fichiers de modèle (classic-model)

### Étape 1 - Copier les nouvelles versions

```bash
cp /home/classic_ops/quick_start_test_runs/all_sites_container_test_1/CA-MonJ/CA-MonJ_init.nc \
   /home/classic_ops/classic-model/CA-MonJ/

cp /home/classic_ops/quick_start_test_runs/all_sites_container_test_1/CA-MonJ/job_configs/job_options_daily.txt \
   /home/classic_ops/classic-model/CA-MonJ/job_configs/

cp /home/classic_ops/CLASSIC/inputFiles/FLUXNETsites_12PFT/CA-MonJ/siteinfo.yaml \
   /home/classic_ops/classic-model/CA-MonJ/site_info/
```

### Étape 2 - Vérifier ce que Git a détecté
Fonction status
```bash
cd /home/classic_ops/classic-model
git status
```

- Si je vois des fichiers en rouge ("modified:" ou "not staged") → il y a bien des changements, continue à l'étape 3
- Si je vois "nothing to commit, working tree clean" **après avoir copié** → les fichiers sources n'ont en fait pas changé depuis le dernier commit (rien à faire, c'est normal)

### Étape 3 - Stager, committer, pousser

```bash
git add CA-MonJ/
git commit -m "Update CA-MonJ init, job_options, siteinfo" -->Préciser-type-de-commit : -m ""
git push
```

### Ou via Positron (Source Control, visuel)

1. `Ctrl+Shift+G` pour ouvrir l'onglet Source Control
2. Vérifier que le dossier ouvert est bien `/home/classic_ops/classic-model`
3. Cliquer `+` sur les fichiers modifiés (ou "Stage All Changes")
4. Écrire un message de commit clair
5. Cliquer **Commit** ✓
6. Cliquer **Sync Changes** ou **Push**

---

## 3. Créer un nouvel environnement / projet pour de futurs fichiers

Quand on commence un nouveau site, un nouveau script, ou un nouveau projet à suivre avec Git, voici la démarche.

### Cas A - Nouveau dossier/site dans un repo existant

Si on ajoute un nouveau site (ex: `CA-XYZ`) dans le même repo `classic-model` :

```bash
mkdir -p /home/classic_ops/classic-model/CA-XYZ/job_configs
mkdir -p /home/classic_ops/classic-model/CA-XYZ/site_info

cp /chemin/vers/source/CA-XYZ_init.nc /home/classic_ops/classic-model/CA-XYZ/
cp /chemin/vers/source/job_options.txt /home/classic_ops/classic-model/CA-XYZ/job_configs/
cp /chemin/vers/source/siteinfo.yaml /home/classic_ops/classic-model/CA-XYZ/site_info/

cd /home/classic_ops/classic-model
git add CA-XYZ/
git commit -m "Add CA-XYZ site files"
git push
```

### Cas B - Nouveau repo GitHub complet

1. **Créer le repo sur GitHub** (via le site web) : bouton "New repository", choisir un nom, ne PAS cocher "Initialize with README" si je veux importer du contenu existant (sinon ça peut créer des conflits).

2. **Créer/lier le dossier local** :

```bash
mkdir -p /home/classic_ops/nom-du-nouveau-projet
cd /home/classic_ops/nom-du-nouveau-projet
git init
git remote add origin https://github.com/danyblanchet7/nom-du-nouveau-projet.git
```

3. **Créer un `.gitignore` dès le départ** (important pour éviter de suivre des fichiers inutiles comme les environnements virtuels) :

```bash
cat > .gitignore << 'EOF'
.venv/
__pycache__/
*.pyc
*.nc.tmp
EOF
```

4. **Ajouter les premiers fichiers et premier commit** :

```bash
git add .
git commit -m "Initial commit"
git branch -M main
git push -u origin main
```

Le `-u origin main` la première fois est important : ça lie ta branche locale à la branche distante, pour que les futurs `git push` (sans arguments) fonctionnent tout seuls.

### Cas C - Nouveau projet Python/R (exp my-python-project)

1. Ouvrir le dossier dans Positron : `File → Open Folder`
2. Ouvrir un terminal dans Positron 
3. Suivre les étapes du Cas B ci-dessus
4. Ensuite, pour chaque nouveau fichier créé directement dans ce dossier (`.py`, `.R`, etc.), pas besoin de `cp` — juste `git add`, `commit`, `push` car les fichiers sont déjà dans le repo.

---

## 4. Aide-mémoire des commandes essentielles

| Commande | Ce qu'elle fait |
|---|---|
| `git status` | Montre l'état actuel (fichiers modifiés, stagés, etc.) |
| `git add <fichier>` | Prépare un fichier précis pour le prochain commit |
| `git add .` | Prépare tous les fichiers modifiés du dossier courant |
| `git commit -m "message"` | Enregistre un instantané avec description |
| `git push` | Envoie les commits locaux vers GitHub |
| `git pull` | Récupère les derniers changements depuis GitHub |
| `git log --oneline -5` | Affiche les 5 derniers commits (résumé) |
| `git remote -v` | Montre à quel repo GitHub ce dossier est connecté |
| `git ls-files` | Liste tous les fichiers actuellement suivis par Git |
| `git rm -r --cached <dossier>` | Arrête de suivre un dossier (sans le supprimer du disque) |

---

## 5. Erreurs fréquentes et solutions

### "nothing to commit, working tree clean" mais on a modifié un fichier
→ oublié l'étape `cp` (copier le fichier source vers le repo). Voir section 2, Étape 1.

### "fatal: ... is outside repository"
→ On essaies de faire `git add` sur un fichier qui n'est pas physiquement dans le dossier du repo. Il faut d'abord le copier dedans.

### Deux commandes collées ensemble dans le terminal (ex: `git statusgit add .`)
→ Ça arrive quand on copie-colle plusieurs lignes trop vite. Tape ou colle une commande à la fois, en t'assurant que la précédente est bien terminée (retour à la ligne de commande normale).


### GitHub semble vide alors que `git log` montre des commits
→ Vérifie que on regardes le bon repo sur github.com (bon nom, bon compte), et la bonne branche (`main` vs `master`).

---

## 6. Résumé visuel du workflow

```
FICHIER SOURCE (ailleurs sur le disque)
        │
        │  cp (copier)
        ▼
DOSSIER DU REPO (ex: classic-model/CA-MonJ/)
        │
        │  git add (stager)
        ▼
ZONE DE STAGING (préparé pour le commit)
        │
        │  git commit -m "..."
        ▼
HISTORIQUE LOCAL (commit enregistré sur ta machine)
        │
        │  git push
        ▼
GITHUB (visible en ligne, partagé/sauvegardé)
```

-> sauter une étape est la cause la plus fréquente de "ça marche pas".

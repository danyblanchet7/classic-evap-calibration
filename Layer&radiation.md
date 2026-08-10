#  2026-08-07 to 2026-08-07 -  layer ( claude IA assisted)


> *"**Contexte** : Problème dans mon run de CLASSIC. Le modéle tourne bien en configuration job options file daily mais en semi-hourly, il shutdown aprés l'année 2021. Il ne parvient pas à simuler 2022,2023,2024 seulement 2016-2021."* 

---

**l'erreur est la suivante :**

```
Fortran runtime error: Index '22' of dimension 3 of array 'soilc' outside of expected range (20:1)
```
dans la routine turbation de soilCProcesses.f90, appelée depuis ctemDriver.F90.

> Le tableau soilc (carbone du sol) est dimensionné pour un maximum de 20 couches (ignd ou un paramètre lié au nombre de couches de sol/carbone), mais le code essaie d'accéder à l'indice 22, donc quelque part, un compteur dépasse la taille allouée. 

>Le crash est à la ligne 265 de src/base/soilCProcesses.f90, dans la subroutine turbation.

>En regardant le code, on vois la ligne clé du crash :
```fortran
soilC(i,j,1:botlyr - 2) = soilcinter(2:botlyr - 1)
```
 La variable botlyr ("bottom layer") détermine jusqu'où la turbation opère. Si botlyr devient égal à 24, alors botlyr - 2 = 22 = **Dépassement de la limite de 20 couches**!!!

---

**le nœud du problème :**

>Ligne 88-91 : une boucle cherche botlyr = l (l'indice de la couche de sol la plus profonde qui est perméable), en se basant sur zbotw ( l'épaisseur/profondeur des couches).
>Ligne 98 : botlyr = botlyr + 2 (marge pour les conditions aux limites).
>Ligne 254 (le crash) : soilC(i,j,1:botlyr - 2) = ...

```fortran

do l = 1,botlyr
  ...
  turblyrbot = l  ! deepest layer in which turbation occurs
  ...
end do

```

Cette boucle va de 1 à botlyr, et botlyr peut valoir jusqu'à ignd + 2 = 22 (rappel : botlyr = botlyr_trouvé + 2 pour les conditions aux limites, ligne 98). Donc turblyrbot peut lui aussi se retrouver à 22.

**plus loin** :

```fortran
soilC(i,j,1:turblyrbot) = soilC(i,j,1:turblyrbot) + amount/real(turblyrbot)
litter(i,j,1:turblyrbot) = litter(i,j,1:turblyrbot) + amount/real(turblyrbot)
```
Si turblyrbot = 22, cette ligne essaie d'écrire à l'indice 22 dans un tableau soilC dimensionné pour seulement 20 couches (ignd = 20)! **Exactement l'erreur que j'ai (Index '22' of dimension 3 ... outside of expected range).**

---

*C'est un bug de bornage d'indice dans le code source de CLASSIC (soilCProcesses.f90), probablement déclenché quand la colonne de sol est entièrement perméable jusqu'à la couche 20 (pas de roche-mère détectée dans les 20 couches), ce qui pousse botlyr à sa valeur maximale (22) et fait déborder turblyrbot. C'est cohérent avec le fait que ça casse précisément en passant à 2022, les conditions de sol/pergélisol à votre site ont peut-être changé de régime cette année-là (active layer plus profond, dégel plus important), amenant botlyr à sa valeur limite.*

---


## Correctif temporaire appliqué (contournement du problème) :

Dans les 2 occurrences de la boucle de calcul (bloc cryoturbation et bloc bioturbation), remplacement de :

```fortran
turblyrbot = l
```
par :

```fortran
turblyrbot = min(l, ignd)
```

>Ceci plafonne l'indice utilisé pour écrire dans soilC/litter à la taille réelle des tableaux, sans changer le comportement dans les cas normaux (l ≤ ignd).

**Fichier modifié** : src/base/soilCProcesses.f90 (sauvegarde conservée : soilCProcesses.f90.bak)

Enfin recompilation effectuée

--- 
# CLASSIC ne calcule pas les flux sortants SW↑ (rsus) et LW↑ (rlus).

---

## 1. Problème initial : rayonnements up invalides
 
CLASSIC ne calcule pas rsus / rlus
Le modèle CLASSIC fournit :

    rsds = SW↓

    rss = SW net (SW absorbé)

    rlds = LW↓

    rls = LW net (LW émis)

Mais il ne calcule pas :

    SW↑ (rsus)

    LW↑ (rlus)

J'ai tenté de les activer via le XML, mais les blocs ajoutés étaient invalides.

---

## Blocs XML invalides..

IDs en conflit (28/29)

balise cassée </defaultUnit

variables fsuacc / flusacc = flux accumulés, pas instantanés

CLASSIC a écrit des fichiers corrompus (valeurs constantes ou nulles)
---

Puis j'ai observé que **rsus_halfhourly.nc et rss_halfhourly.nc avaient exactement la même taille**
Donc j'ai supprimer les dossiers corrompus et supprimer les lignes ajoutés dans le xml

---

# **SOLUTION** = Reconstruction physique des flux sortants
CLASSIC fournit les  flux :

    SW↓ = rsds

    SW net = rss

    LW↓ = rlds

    LW net = rls

Donc :

     SW↑ (rsus)
_𝑟𝑠𝑢𝑠 = 𝑟𝑠𝑑𝑠−𝑟𝑠𝑠_

    LW↑ (rlus)
_𝑟𝑙𝑢𝑠=𝑟𝑙𝑑𝑠−𝑟𝑙𝑠_
---
## Intégration dans mon code de calibration Python
```python
classic["rsus"] = classic["rsds"]["rsds"] - classic["rss"]["rss"]
classic["rlus"] = classic["rlds"]["rlds"] - classic["rls"]["rls"]
```

Dans VARIABLES :

```python
("Rsu_J", "rsus"),
("Rlu_J", "rlus"),
```
| Variable | Nom CLASSIC | Signification | Type | Ce que tu fais |
| --- | --- | --- | --- | --- |
| **rsds** | SW↓ | solaire entrant | fourni | utilisé tel quel |
| **rss** | SW_net | solaire absorbé | fourni | utilisé tel quel |
| **rlds** | LW↓ | infrarouge entrant | fourni | utilisé tel quel |
| **rls** | LW_net | infrarouge net | fourni | utilisé tel quel |
| **rsus** | SW↑ | solaire réfléchi | **reconstruit** | rsds − rss |
| **rlus** | LW↑ | infrarouge émis | **reconstruit** | rlds − rls |
---
Résultats = métriques réalistes
    SW↑ (rsus) -> RMSE ≈ 8–29 W/m² et corrélation ≈ 0.96-0.99

    LW↑ (rlus) -> RMSE ≈ 210-230 W/m² et corrélation ≈ 0.93–0.95


---

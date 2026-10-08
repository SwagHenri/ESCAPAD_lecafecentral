# Google Analytics 4 · Café Central Lille (lecafecentral.fr)

Runbook complet pour créer la propriété GA4 du Café Central et brancher tout le suivi : propriété, flux, GTM, consentement, accès. Tout ce qui pouvait être préparé l'est ; il reste **trois actions** qui demandent un compte Google administrateur d'ESCAPAD (détail plus bas).

> **État au 05/10/2026.** La propriété GA4 a été créée à la main : ID de mesure **`G-VVXGLCV6CR`** (flux web lecafecentral.fr). Il reste à compléter sa configuration (§ 3), à brancher GTM (§ 5) et à déployer le consentement (§ 6).
>
> ⚠️ **Ne pas coller le snippet gtag.js** (`<script async src="https://www.googletagmanager.com/gtag/js?id=G-VVXGLCV6CR">…`) dans le site. GTM-TVBDT8RJ est déjà chargé sur toutes les pages et c'est lui qui porte la balise Google GA4 (export § 5). Le snippet en plus ferait compter chaque page vue deux fois et casserait le Consent Mode. L'ID est déjà renseigné dans `gtm/GTM-TVBDT8RJ-ga4-import.json`.

## 0 · En trois actions

| # | Action | Qui | Durée | Outil |
|---|---|---|---|---|
| 1 | ~~Créer~~ **Compléter** la propriété `G-VVXGLCV6CR` : mesure améliorée, conservation 14 mois, Google Signals off, 7 dimensions, 3 événements clés, accès | Guillaume (compte admin GA ESCAPAD) | 3 min | `scripts/create_ga4_property.py` **ou** l'interface (§ 3) |
| 2 | Importer la configuration dans GTM-TVBDT8RJ, tester, publier | Guillaume ou Simon | 10 min | `gtm/GTM-TVBDT8RJ-ga4-import.json` (§ 5) |
| 3 | ~~Déployer le consentement sur le site~~ **Fait le 05/10/2026** : PR [ESCAPAD-lecafecentral_lille#51](https://github.com/SwagHenri/ESCAPAD-lecafecentral_lille/pull/51) mergée, en production sur les 5 pages | — | — | § 6 |

Puis recette (§ 7) et message à l'équipe (§ 10).

## 1 · État des lieux (constaté le 02/10/2026)

- **Site** : `www.lecafecentral.fr`, 5 pages statiques sur Vercel (`/`, `/brunch`, `/dejeuner`, `/acces`, `/coupe-du-monde`), dépôt `SwagHenri/ESCAPAD-lecafecentral_lille`.
- **GTM** : `GTM-TVBDT8RJ` chargé sur toutes les pages. Version publiée lue depuis l'extérieur : balise Google `AW-17758350861`, éditeur de liens de conversion, **3 conversions Google Ads** déclenchées sur `reservation_click`, `phone_click`, `devis_submit` (posées par Simon le 30/09 – 01/10). **Aucun identifiant `G-`** : pas de GA4, ce que Clément a confirmé.
- **dataLayer** : `js/track.js` pousse `reservation_click`, `phone_click`, `cta_click` ; `index.html` pousse `devis_submit`. Les événements partent bien, ils n'ont juste nulle part où aller côté Analytics.
- **Consentement** : un bandeau n'existe que sur l'accueil, son texte dit « aucun traceur » (faux depuis que GTM charge Google Ads), et il ne pilote rien (pas de Consent Mode). Aucune page confidentialité sur lecafecentral.fr.
- **Zenchef** : les réservations se terminent sur `bookings.zenchef.com` (rid 386365) ; le site ne peut mesurer que le clic de départ.

## 2 · Décisions de configuration

| Réglage | Valeur | Pourquoi |
|---|---|---|
| Compte GA | compte ESCAPAD existant | une organisation, un compte ; Simon et Clément y retrouvent déjà escapad.fr |
| Nom de la propriété | `Café Central Lille · lecafecentral.fr` | lisible dans le sélecteur, sans confusion avec les pages resto d'escapad.fr |
| Fuseau / devise | Europe/Paris · EUR | |
| Secteur | Alimentation et boissons | |
| Flux web | `https://www.lecafecentral.fr` · nom `lecafecentral.fr · web` | |
| Mesure améliorée | scroll ✔ · clics sortants ✔ · téléchargements ✔ · recherche ✘ · vidéo ✘ · formulaires ✘ | pas de recherche ni vidéo ; le devis n'est pas un `<form>` natif, `devis_submit` fait foi |
| Conservation des données | 14 mois, réinitialisation à chaque activité | maximum d'une propriété standard |
| Google Signals | **désactivé** | pas d'opt-in explicite sur le site ; à activer seulement si le modèle de consentement change |
| Dimensions personnalisées | `cta`, `lp`, `loc`, `destination`, `phone_number`, `devis_type`, `devis_personnes` | voir `tracking-plan.md` |
| Événements clés | `reservation_click` (1×/session), `phone_click` (1×/session), `devis_submit` (1×/événement) | une personne qui clique trois fois « Réserver » = une intention |
| Trafic interne | paramètre `traffic_type=internal` posé par GTM (voir § 4) + filtre « Internal Traffic » actif | pas d'IP fixe connue, le marquage par appareil est plus fiable |
| Références indésirables | `zenchef.com` | évite qu'un retour depuis Zenchef ouvre une session « referral zenchef » |
| Google Ads | association GA4 ↔ Ads, **sans** importer les événements clés | les 3 conversions Ads existent déjà dans GTM ; importer en plus = double comptage |
| Consentement | **Consent Mode v2 en opt-out** : accordé par défaut, retiré uniquement sur refus explicite | décision ESCAPAD (même modèle qu'escapad.fr) |

## 3 · Compléter la propriété (créée le 05/10/2026 · `G-VVXGLCV6CR`)

La création est faite. Le script retrouve la propriété **par son ID de mesure** (constante `KNOWN_MEASUREMENT_ID`) et ne crée rien en double : il complète ce qui manque (flux, mesure améliorée, conservation, Google Signals, dimensions, événements clés, accès).

### Option A · script (recommandée, 3 minutes)

```bash
cd analytics/scripts
pip install -r requirements.txt
export GA_ACCESS_TOKEN="ya29…"        # voir ci-dessous
python3 create_ga4_property.py --list-accounts
python3 create_ga4_property.py --account ESCAPAD           # ou l'ID numérique du compte
```

Le jeton : https://developers.google.com/oauthplayground → connecté avec le compte Google admin du GA ESCAPAD → scopes `https://www.googleapis.com/auth/analytics.edit` et `https://www.googleapis.com/auth/analytics.manage.users` → « Exchange authorization code for tokens » → copier l'*access token* (valable 1 h). Alternative gcloud décrite en tête du script.

Le script est idempotent (relancer ne crée rien en double). Il retrouve la propriété `G-VVXGLCV6CR` dans le compte (sinon `--property <ID numérique>`), règle la mesure améliorée, la conservation, Google Signals, les dimensions, les événements clés, les accès (§ 8), puis :
- écrit `analytics/ga4-property.json` (IDs à committer) ;
- remplace `G-XXXXXXXXXX` par le vrai ID de mesure dans `gtm/GTM-TVBDT8RJ-ga4-import.json`.

Options : `--dry-run` (montre les appels sans rien créer), `--no-users`, `--ads-customer-id 123-456-7890` (association Google Ads, nécessite d'être admin du compte Ads).

### Option B · interface (10 minutes)

La propriété et le flux existent déjà : **sauter les points 1 à 3**, vérifier seulement la mesure améliorée (roue dentée du flux : décocher *Recherche sur le site*, *Engagement vidéo*, *Interactions avec les formulaires*), puis faire les points 4 à 7. Le point 8 est déjà fait.

1. https://analytics.google.com → Admin → compte **ESCAPAD** → **Créer** → **Propriété**.
   Nom `Café Central Lille · lecafecentral.fr` · fuseau **France (GMT+01:00) Paris** · devise **Euro**.
2. Détails de l'entreprise : secteur **Alimentation et boissons**, taille **Petite**. Objectifs : **Générer des prospects**.
3. Plateforme **Web** : URL `https://www.lecafecentral.fr`, nom du flux `lecafecentral.fr · web`. Mesure améliorée activée → roue dentée : décocher *Recherche sur le site*, *Engagement vidéo*, *Interactions avec les formulaires*. Noter l'**ID de mesure `G-…`**.
4. Admin → *Collecte et modification des données* → **Conservation des données** : 14 mois, « Réinitialiser les données utilisateur lors d'une nouvelle activité » activé.
5. Admin → *Collecte et modification des données* → **Collecte des données** : Google Signals **désactivé**.
6. Admin → *Affichage des données* → **Dimensions personnalisées** → créer les 7 dimensions (portée Événement) listées dans `tracking-plan.md` § 3.
7. Admin → *Affichage des données* → **Événements clés** → *Nouvel événement clé* : `reservation_click`, `phone_click`, `devis_submit`. Sur les deux premiers : « Modifier la méthode de comptabilisation » → *Une fois par session*.
8. Enregistrer l'ID de mesure dans l'export GTM :
   ```bash
   python3 analytics/scripts/create_ga4_property.py --set-measurement-id G-XXXXXXXXX
   ```

## 4 · Réglages dans l'interface (non couverts par l'API)

À faire une fois la propriété créée, quelle que soit l'option :

1. **Filtre trafic interne** : Admin → *Collecte et modification des données* → **Filtres de données** → `Internal Traffic` → état **Actif**. Le paramètre `traffic_type=internal` est posé par la variable GTM `js - traffic_type` (§ 5) : n'importe qui de l'équipe ouvre une page du site avec `?internal=1` une fois, son appareil est exclu des rapports (`?internal=0` pour annuler). Les URL `localhost` et `*.vercel.app` (prévisualisations) sont exclues d'office.
2. **Références indésirables** : Admin → **Flux de données** → `lecafecentral.fr · web` → *Configurer les paramètres de la balise* → *Afficher tout* → **Lister les références indésirables** → ajouter `zenchef.com`.
3. **Google Ads** : Admin → *Associations de produits* → **Google Ads** → associer le compte de Simon (personnalisation des annonces : désactivée). **Ne pas** importer les événements clés dans Ads (voir § 2).
4. Facultatif : Admin → *Affichage des données* → **Paramètres d'attribution** : laisser « Basée sur les données », fenêtre 30 jours pour les événements clés.

## 5 · GTM : importer, tester, publier

Le fichier `gtm/GTM-TVBDT8RJ-ga4-import.json` contient :

| Type | Nom | Rôle |
|---|---|---|
| Variable | `const - GA4 Measurement ID` | l'ID `G-…` (rempli par le script, sinon à saisir) |
| Variables | `dlv - cta/lp/loc/destination/phone_number/type/personnes/consent_choice` | lecture du dataLayer |
| Variables | `js - traffic_type`, `js - debug_mode` | trafic interne + DebugView automatique pour l'équipe |
| Déclencheurs | `CE - reservation_click`, `CE - phone_click`, `CE - devis_submit`, `CE - cta_click` | événements personnalisés |
| Balise | `GA4 - Google tag (configuration)` | balise Google, sur *Initialization - All Pages* |
| Balises | `GA4 - Event - reservation_click / phone_click / devis_submit / cta_click` | événements GA4 avec leurs paramètres |
| Balise | `Consent Mode - défaut (repli si le site ne l'a pas posé)` | HTML personnalisé sur *Consent Initialization* ; ne fait rien si le site a déjà posé le défaut (§ 6) |

Procédure :

1. https://tagmanager.google.com → conteneur **GTM-TVBDT8RJ** → **Admin** → **Importer le conteneur**.
2. Fichier : `GTM-TVBDT8RJ-ga4-import.json` · Espace de travail : **Nouveau** (`GA4 Café Central`) · Option : **Fusionner** → **Renommer les balises, déclencheurs et variables en conflit** → Confirmer. Les balises Google Ads de Simon ne sont pas touchées. Si Simon a un espace de travail non publié en cours, le prévenir avant de publier (§ 10).
3. Vérifier que la variable `const - GA4 Measurement ID` contient bien `G-VVXGLCV6CR` (déjà renseigné dans l'export).
4. **Aperçu** → ouvrir `https://www.lecafecentral.fr/?internal=1` → vérifier dans Tag Assistant : la balise Google part à l'initialisation ; un clic sur « Réserver » déclenche `GA4 - Event - reservation_click` avec `cta`, `lp`, `loc`, `destination` ; un clic sur le numéro déclenche `phone_click` ; un envoi de devis test déclenche `devis_submit` (penser à prévenir `privatisation.lille@` du test, le formulaire envoie un vrai mail).
5. **Envoyer** → **Publier** avec une description de version (ex. « GA4 Café Central : balise Google + 4 événements + Consent Mode »).

## 6 · Site : consentement (opt-out) sur toutes les pages

**Déployé le 05/10/2026** via la PR [ESCAPAD-lecafecentral_lille#51](https://github.com/SwagHenri/ESCAPAD-lecafecentral_lille/pull/51) (mergée, Vercel en production). Vérifié sur www.lecafecentral.fr : les 5 pages portent le bloc Consent Mode inline et chargent `js/consent.js`, l'ancien bandeau inline a disparu. Le patch reste ici pour l'historique.

`site/consent-mode.patch` s'appliquait au dépôt du site `ESCAPAD-lecafecentral_lille` (branche `main`, commit `38adbd2` ou postérieur) :

```bash
cd ESCAPAD-lecafecentral_lille
git pull
git am ../ESCAPAD_lecafecentral/analytics/site/consent-mode.patch
git push          # Vercel déploie
```

Ce que change le patch (5 pages + 1 fichier) :

- Un bloc inline dans `<head>`, **avant** le snippet GTM, pose les valeurs par défaut du Consent Mode v2. **Logique opt-out, telle que décidée** : `analytics_storage`, `ad_storage`, `ad_user_data`, `ad_personalization` sont `granted` tant que l'utilisateur n'a pas explicitement cliqué « Continuer sans accepter » ; après un refus (mémorisé dans `localStorage`, clé `cc-cookie-consent`), tout passe en `denied` dès le chargement suivant et GA4 ne reçoit plus que des pings sans cookie. Une constante `OPT_IN=false` dans chaque page permettrait un opt-in strict ; elle ne doit pas être changée sans décision d'ESCAPAD.
- `js/consent.js` : bandeau unique injecté sur **toutes** les pages (il n'existait que sur l'accueil), texte corrigé (« Nous utilisons Google Analytics… et Google Ads… Vous pouvez refuser »), lien « En savoir plus » vers `https://www.escapad.fr/confidentialite`, mémorisation du choix, `gtag('consent','update')` et événement `cc_consent_update` dans le dataLayer. API `ccConsent.get()` / `ccConsent.set()` / `ccConsent.reset()`.
- `index.html` : suppression de l'ancien bandeau inline (CSS, HTML, `initCookies`).

Points juridiques à garder en tête (pas bloquants pour le déploiement, à arbitrer avec ESCAPAD) :

- La CNIL n'exempte pas GA4 de consentement ; l'opt-out est un choix de risque assumé, identique à escapad.fr.
- lecafecentral.fr n'a pas de page confidentialité propre ; le bandeau renvoie à celle d'escapad.fr, qui devrait mentionner le site du Café Central.
- Prévoir un lien « Cookies » en pied de page appelant `ccConsent.reset()` pour permettre de changer d'avis.

La balise `Consent Mode - défaut` du conteneur GTM reste un repli (même logique opt-out) : elle ne fait rien tant que le site pose lui-même le défaut, ce qui est le cas depuis le 05/10.

## 7 · Recette de bout en bout

- [ ] GA4 → **Temps réel** : une visite sur `https://www.lecafecentral.fr/?internal=1` n'apparaît **pas** (filtre interne actif) ; une visite en navigation privée sans paramètre apparaît.
- [ ] GA4 → Admin → **DebugView** : l'appareil marqué `?internal=1` y apparaît automatiquement (`debug_mode`) ; on y voit `page_view`, `scroll`, `click` (sortant), `reservation_click` avec ses paramètres.
- [ ] Clic « Continuer sans accepter » → dans Tag Assistant, l'état du consentement passe en `denied` ; `gcs` des hits GA4 devient `G100`.
- [ ] GA4 → Rapports → **Événements** : `reservation_click`, `phone_click`, `devis_submit` marqués événement clé (après 24 h de données).
- [ ] Google Ads : les 3 conversions existantes continuent de remonter (rien ne change pour elles).
- [ ] `analytics/ga4-property.json` committé avec les IDs ; `const - GA4 Measurement ID` publié avec le bon `G-`.

## 8 · Accès

| Personne | Rôle propriété | Pourquoi |
|---|---|---|
| Guillaume (compte créateur) | Administrateur | gestion |
| simongroslegeron@gmail.com · Simon Gros | Administrateur | demandé le 30/09 ; pilote Google Ads et GTM |
| clement@growth-society.com · Clément Canfin | Éditeur | Growth Society, campagnes Meta |
| nicolas@escapad.city · victor@escapad.city | Lecteur | co-fondateurs |

Le script applique cette liste (`USERS` en tête du fichier). À la main : Admin → *Gestion des accès à la propriété* → **+** → *Ajouter des utilisateurs*.

## 9 · Zenchef : mesurer la réservation confirmée (phase 2)

Aujourd'hui `reservation_click` mesure l'intention. Pour la réservation confirmée, deux pistes à vérifier avec Zenchef (espace client → paramètres du module de réservation / intégrations) :

1. Si Zenchef permet de déclarer un ID GA4 ou un conteneur GTM sur le parcours de réservation : utiliser **le même `G-…`**, puis GA4 → Flux → *Configurer les paramètres de la balise* → **Configurer vos domaines** → ajouter `bookings.zenchef.com` (suivi inter-domaines, la session suit jusqu'à la confirmation). Marquer alors leur événement de confirmation en événement clé et l'importer dans Ads comme conversion principale, en passant `reservation_click` en secondaire.
2. Sinon, exploiter l'export / webhook de réservations Zenchef pour rapprocher les volumes (hors GA4).

## 10 · Message prêt à envoyer (après les actions 1 à 3)

> Salut Simon, Clément, Nicolas,
>
> La propriété GA4 du Café Central est créée dans le compte GA ESCAPAD : **Café Central Lille · lecafecentral.fr**, ID de mesure `G-VVXGLCV6CR`. Simon est admin, Clément éditeur, Nicolas et Victor lecteurs.
>
> Dans GTM-TVBDT8RJ j'ai publié la balise Google GA4 et les événements `reservation_click`, `phone_click`, `devis_submit`, `cta_click`, avec leurs paramètres en dimensions personnalisées ; les trois premiers sont des événements clés. Vos trois conversions Google Ads n'ont pas bougé : ne pas importer les événements clés GA4 dans Ads, ça compterait double. Le consentement est en opt-out (accordé sauf refus explicite), Consent Mode v2 branché sur toutes les pages.
>
> Pour vous exclure des stats : ouvrir une fois `https://www.lecafecentral.fr/?internal=1` sur chaque appareil.

## 11 · Fichiers

```
analytics/
├─ README.md                          ← ce runbook
├─ tracking-plan.md                   ← dictionnaire des événements, paramètres, dimensions, clés
├─ ga4-property.json                  ← IDs de la propriété et du flux (partiel tant que le script n'a pas tourné)
├─ gtm/GTM-TVBDT8RJ-ga4-import.json   ← export GTM à importer (Fusionner)
├─ scripts/create_ga4_property.py     ← création + configuration via l'API Admin GA4
├─ scripts/requirements.txt
└─ site/consent-mode.patch            ← Consent Mode v2 (opt-out) + bandeau sur toutes les pages, pour ESCAPAD-lecafecentral_lille
```

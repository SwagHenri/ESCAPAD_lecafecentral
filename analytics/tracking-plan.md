# Plan de tracking · lecafecentral.fr (Café Central Lille)

Référence des événements envoyés par le site et de leur traitement dans GTM (`GTM-TVBDT8RJ`) et GA4.
Source côté site : `js/track.js` (clics) et `index.html` (devis). Aucune donnée personnelle ne transite.

## 1. Événements du site → GA4

| Événement dataLayer | Déclenché quand | Paramètres poussés | Tag GTM (import) | Événement GA4 | Clé ? |
|---|---|---|---|---|---|
| `reservation_click` | Clic sur un bouton « Réserver » (`data-cta="reserver"`), départ vers Zenchef | `cta`, `lp`, `loc`, `destination`, `page` | GA4 - Event - reservation_click | `reservation_click` | **Oui** · 1×/session |
| `phone_click` | Clic sur un lien `tel:` (+33 7 75 76 31 66) | `phone_number`, `page` | GA4 - Event - phone_click | `phone_click` | **Oui** · 1×/session |
| `devis_submit` | Envoi réussi du formulaire de devis privatisation (`#contact`) | `type`, `personnes`, `page` | GA4 - Event - devis_submit | `devis_submit` (params renommés `devis_type`, `devis_personnes`) | **Oui** · 1×/événement |
| `cta_click` | Clic sur un autre lien taggé `data-cta` (ex. `brunch-savoir-plus`) | `cta`, `lp`, `loc`, `destination`, `page` | GA4 - Event - cta_click | `cta_click` | Non |
| `cc_consent_update` | Choix dans le bandeau cookies (après patch `site/consent-mode.patch`) | `consent_choice` | — (disponible pour un déclencheur) | — | Non |

`page` n'est pas envoyé à GA4 : `page_location` / `page_path` le couvrent déjà.

### Valeurs connues des paramètres

| Paramètre | Valeurs rencontrées dans le code |
|---|---|
| `cta` | `reserver`, `brunch-savoir-plus` |
| `lp` (page) | `home`, `brunch`, `dejeuner`, `acces`, `coupe-du-monde` |
| `loc` (emplacement) | `nav`, `hero`, `sticky`, `bar`, `final`, `footer`, `diffusion`, `section-brunch` |
| `destination` | `zenchef`, `interne` |
| `phone_number` | `+33775763166` |
| `type` → `devis_type` | libellés du select du formulaire (Anniversaire, Réunion d'équipe, Autre…) |
| `personnes` → `devis_personnes` | nombre saisi (texte libre) |

## 2. Événements automatiques GA4 (mesure améliorée)

Réglage du flux web : scroll **on**, clics sortants **on**, téléchargements **on**, recherche **off**, vidéo **off**, formulaires **off**.

| Événement GA4 | Utilité ici |
|---|---|
| `page_view`, `session_start`, `first_visit`, `user_engagement` | audience de base |
| `scroll` (90 %) | lecture des pages carte / brunch |
| `click` (sortant) avec `link_domain`, `link_url` | tous les départs : `bookings.zenchef.com`, `instagram.com`, `escapad.fr`, `google.com` (itinéraire) — complète `reservation_click` sans le remplacer |
| `file_download` | PDF carte / menus s'ils sont ajoutés un jour |

## 3. Dimensions personnalisées (portée événement)

| Paramètre | Nom affiché | Alimentée par |
|---|---|---|
| `cta` | CTA (nom) | reservation_click, cta_click |
| `lp` | Page LP (lp) | reservation_click, cta_click |
| `loc` | Emplacement CTA (loc) | reservation_click, cta_click |
| `destination` | Destination CTA | reservation_click, cta_click |
| `phone_number` | Numéro appelé | phone_click |
| `devis_type` | Type d'événement (devis) | devis_submit |
| `devis_personnes` | Nb de personnes (devis) | devis_submit |
| `traffic_type` | *(réservé GA4, pas à créer)* | balise Google : `internal` pour l'équipe |

## 4. Événements clés et Google Ads

- **Événements clés GA4** : `reservation_click`, `phone_click`, `devis_submit`. Aucune valeur monétaire par défaut (à ajouter plus tard si l'équipe veut une valeur de « réservation »).
- **Google Ads** : le conteneur contient déjà la balise Google `AW-17758350861`, l'éditeur de liens de conversion et **trois conversions Ads** déclenchées sur `reservation_click`, `phone_click` et `devis_submit` (posées par Simon, libellés `6aLMCL…`, `TUcMCL…`, `qXxzCL…`). Elles restent la source de vérité pour Ads. **Ne pas importer en plus les événements clés GA4 dans Ads**, sinon chaque conversion compte double. L'association GA4 ↔ Ads sert aux audiences et au reporting croisé.

## 5. Correspondance avec la propriété escapad.fr

Le Café Central existe aussi sur escapad.fr (`/cafe-central-lille`, `/resto`), mesuré dans la propriété GA4 `G-69YJMYRW24` (conteneur `GTM-P5JC9D97`). Mêmes intentions, noms différents :

| Intention | lecafecentral.fr (cette propriété) | escapad.fr (`G-69YJMYRW24`) |
|---|---|---|
| Réservation de table (départ Zenchef) | `reservation_click` | `resto_reservation_click` |
| Appel téléphonique | `phone_click` | `appel_click` |
| Devis privatisation resto | `devis_submit` | — |
| Devis séminaire / entreprise | — | `generate_lead` (target = entreprise) |

Pour une vue « Café Central » complète, additionner les deux propriétés (ou brancher les deux dans un même rapport Looker Studio).

## 6. Limites connues

- La réservation **confirmée** se termine chez Zenchef (`bookings.zenchef.com`, rid 386365). Le site ne mesure que l'intention (le clic). Voir README § Zenchef pour la phase 2.
- `phone_click` n'a de sens que sur mobile ; sur desktop le clic sur `tel:` n'aboutit presque jamais à un appel.
- Le formulaire de devis n'est pas un `<form>` natif (bouton + `fetch`) : seul `devis_submit` est fiable, la mesure améliorée « formulaires » doit rester désactivée.

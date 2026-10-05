#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crée et configure la propriété GA4 du Café Central Lille (lecafecentral.fr)
via l'API Google Analytics Admin, puis écrit l'ID de mesure dans l'export GTM.

Ce que fait le script, dans l'ordre (chaque étape est idempotente : relancer ne crée pas de doublon) :
  1. retrouve le compte GA (par nom ou ID) ;
  2. retrouve la propriété existante via son ID de mesure (KNOWN_MEASUREMENT_ID / --measurement-id / --property),
     sinon la crée (fuseau Europe/Paris, devise EUR, secteur Food & Drink) ;
  3. crée le flux web https://www.lecafecentral.fr et récupère l'ID de mesure G-… ;
  4. règle la mesure améliorée (scroll, clics sortants, téléchargements ; pas de recherche / vidéo / formulaires) ;
  5. conservation des données : 14 mois, réinitialisation à chaque nouvelle activité ;
  6. Google Signals désactivé (pas de consentement opt-in sur le site → prudence CNIL) ;
  7. dimensions personnalisées (cta, lp, loc, destination, phone_number, devis_type, devis_personnes) ;
  8. événements clés : reservation_click, phone_click (1×/session), devis_submit (1×/événement) ;
  9. accès utilisateurs (voir USERS) ;
 10. (optionnel) association Google Ads si --ads-customer-id est fourni ;
 11. écrit analytics/ga4-property.json et remplace G-XXXXXXXXXX dans analytics/gtm/GTM-TVBDT8RJ-ga4-import.json.

Authentification (au choix) :
  A) Jeton OAuth : export GA_ACCESS_TOKEN="ya29…"
     → https://developers.google.com/oauthplayground, scopes :
       https://www.googleapis.com/auth/analytics.edit
       https://www.googleapis.com/auth/analytics.manage.users
     (jeton valable ~1 h, largement suffisant)
  B) gcloud (Application Default Credentials) :
     gcloud auth application-default login \
       --scopes=https://www.googleapis.com/auth/analytics.edit,https://www.googleapis.com/auth/analytics.manage.users,https://www.googleapis.com/auth/cloud-platform
     gcloud services enable analyticsadmin.googleapis.com --project <projet-gcp>
     export GOOGLE_CLOUD_QUOTA_PROJECT=<projet-gcp>

Exemples :
  python3 create_ga4_property.py --list-accounts
  python3 create_ga4_property.py --account ESCAPAD --dry-run
  python3 create_ga4_property.py --account 123456789
  python3 create_ga4_property.py --account 123456789 --ads-customer-id 1234567890
  python3 create_ga4_property.py --set-measurement-id G-ABC123XYZ   # propriété créée à la main : n'écrit que le JSON GTM

Dépendances : requests (et google-auth pour l'option B). Voir requirements.txt.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("Module manquant : pip install -r requirements.txt")

# ───────────────────────────── Configuration (modifiable) ─────────────────────────────

PROPERTY_NAME = "Café Central Lille · lecafecentral.fr"
# Propriété déjà créée à la main (05/10/2026) : le script la retrouve par cet ID de mesure et COMPLÈTE sa
# configuration (flux, mesure améliorée, conservation, dimensions, événements clés, accès) sans rien recréer.
# Mettre "" pour repartir d'une création complète.
KNOWN_MEASUREMENT_ID = "G-VVXGLCV6CR"
TIME_ZONE = "Europe/Paris"
CURRENCY = "EUR"
INDUSTRY = "FOOD_AND_DRINK"

STREAM_NAME = "lecafecentral.fr · web"
STREAM_URI = "https://www.lecafecentral.fr"

# Mesure améliorée du flux web
ENHANCED_MEASUREMENT = {
    "streamEnabled": True,
    "scrollsEnabled": True,            # scroll 90 %
    "outboundClicksEnabled": True,     # clics sortants (Zenchef, Instagram, escapad.fr, Google Maps…)
    "siteSearchEnabled": False,        # pas de recherche sur le site
    "videoEngagementEnabled": False,   # pas de vidéo YouTube intégrée
    "fileDownloadsEnabled": True,      # PDF carte / menus si ajoutés un jour
    "pageChangesEnabled": True,        # changements d'historique (SPA) — sans effet ici, inoffensif
    "formInteractionsEnabled": False,  # le devis n'est pas un <form> natif : on garde l'événement devis_submit
}

DATA_RETENTION = "FOURTEEN_MONTHS"     # maximum pour une propriété standard
RESET_ON_NEW_ACTIVITY = True

# Dimensions personnalisées (portée événement). parameterName = nom du paramètre envoyé par GTM.
CUSTOM_DIMENSIONS = [
    ("cta",             "CTA (nom)",                     "Valeur de data-cta du bouton cliqué (reserver, brunch-savoir-plus…)"),
    ("lp",              "Page LP (lp)",                  "Page d'origine du clic : home, brunch, dejeuner, acces, coupe-du-monde"),
    ("loc",             "Emplacement CTA (loc)",         "Emplacement du bouton : nav, hero, sticky, bar, final, footer, diffusion…"),
    ("destination",     "Destination CTA",               "zenchef ou interne"),
    ("phone_number",    "Numéro appelé",                 "Numéro cliqué (tel:)"),
    ("devis_type",      "Type d'événement (devis)",      "Anniversaire, Réunion d'équipe, Autre… (formulaire privatisation)"),
    ("devis_personnes", "Nb de personnes (devis)",       "Nombre de personnes saisi dans le formulaire privatisation"),
]

# Événements clés (= conversions GA4). countingMethod : ONCE_PER_SESSION ou ONCE_PER_EVENT.
KEY_EVENTS = [
    ("reservation_click", "ONCE_PER_SESSION"),
    ("phone_click",       "ONCE_PER_SESSION"),
    ("devis_submit",      "ONCE_PER_EVENT"),
]

# Accès à la propriété. Rôles : admin, editor, marketer, analyst, viewer.
USERS = [
    ("simongroslegeron@gmail.com", "admin"),     # Simon Gros — l'a demandé en admin (Google Ads / GTM)
    ("clement@growth-society.com", "editor"),    # Clément Canfin — Growth Society (Meta)
    ("nicolas@escapad.city",       "viewer"),    # Nicolas Husson — co-fondateur
    ("victor@escapad.city",        "viewer"),    # Victor Schieber — co-fondateur
]

# ─────────────────────────────────────────────────────────────────────────────────────

API = "https://analyticsadmin.googleapis.com"
SCOPES = [
    "https://www.googleapis.com/auth/analytics.edit",
    "https://www.googleapis.com/auth/analytics.manage.users",
]
HERE = Path(__file__).resolve().parent
GTM_JSON = HERE.parent / "gtm" / "GTM-TVBDT8RJ-ga4-import.json"
OUTPUT_JSON = HERE.parent / "ga4-property.json"
PLACEHOLDER = "G-XXXXXXXXXX"


class Admin:
    """Mini client REST pour l'API Analytics Admin (v1beta + v1alpha)."""

    def __init__(self, token: str | None, dry_run: bool):
        self.dry_run = dry_run
        self.s = requests.Session()
        if token:
            self.s.headers["Authorization"] = f"Bearer {token}"
        qp = os.environ.get("GOOGLE_CLOUD_QUOTA_PROJECT")
        if qp:
            self.s.headers["x-goog-user-project"] = qp
        self.s.headers["Content-Type"] = "application/json"

    def call(self, method: str, path: str, body: dict | None = None, params: dict | None = None, fake: dict | None = None):
        url = f"{API}/{path}"
        if self.dry_run and method != "GET":
            print(f"   [dry-run] {method} {path} {json.dumps(body, ensure_ascii=False) if body else ''}")
            return fake or {}
        r = self.s.request(method, url, params=params, data=json.dumps(body) if body is not None else None, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} → HTTP {r.status_code}\n{r.text}")
        return r.json() if r.text else {}

    def get(self, path, params=None):
        if self.dry_run:
            # En dry-run on lit quand même si on a un jeton, sinon on renvoie vide.
            if "Authorization" not in self.s.headers:
                return {}
        return self.call("GET", path, params=params)

    def list_all(self, path: str, key: str, params: dict | None = None):
        items, token = [], None
        while True:
            p = dict(params or {})
            if token:
                p["pageToken"] = token
            data = self.get(path, p) or {}
            items += data.get(key, [])
            token = data.get("nextPageToken")
            if not token:
                return items


def get_token(args) -> str | None:
    if args.token:
        return args.token
    env = os.environ.get("GA_ACCESS_TOKEN")
    if env:
        return env
    try:
        import google.auth  # type: ignore
        import google.auth.transport.requests  # type: ignore
        creds, _ = google.auth.default(scopes=SCOPES)
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token
    except Exception as exc:  # noqa: BLE001
        if args.dry_run:
            print("ℹ️  Pas d'identifiants Google (dry-run : on continue avec des valeurs fictives).")
            return None
        sys.exit(
            "Aucun identifiant Google trouvé.\n"
            "  → export GA_ACCESS_TOKEN=\"ya29…\" (OAuth Playground, scopes analytics.edit + analytics.manage.users)\n"
            "  → ou gcloud auth application-default login --scopes=… (voir l'en-tête du script)\n"
            f"Détail : {exc}"
        )


def pick_account(api: Admin, wanted: str | None):
    summaries = api.list_all("v1beta/accountSummaries", "accountSummaries")
    if not summaries:
        if api.dry_run:
            return {"account": "accounts/000000000", "displayName": wanted or "(compte fictif)"}
        sys.exit("Aucun compte GA visible avec ces identifiants. Connecte-toi avec le compte Google qui administre le GA d'ESCAPAD.")
    if wanted:
        w = wanted.strip().lower().removeprefix("accounts/")
        for a in summaries:
            if a["account"].removeprefix("accounts/") == w or a.get("displayName", "").lower() == w:
                return a
        for a in summaries:
            if w in a.get("displayName", "").lower():
                return a
        sys.exit(f"Compte « {wanted} » introuvable. Comptes visibles :\n" + "\n".join(
            f"  {a['account'].removeprefix('accounts/'):>12}  {a.get('displayName')}" for a in summaries))
    if len(summaries) == 1:
        return summaries[0]
    sys.exit("Plusieurs comptes GA visibles, précise --account <nom|ID> :\n" + "\n".join(
        f"  {a['account'].removeprefix('accounts/'):>12}  {a.get('displayName')}" for a in summaries))


def find_property_by_measurement_id(api: Admin, account: dict, mid: str):
    """Retrouve (propriété, flux web) portant l'ID de mesure donné dans le compte, ou (None, None)."""
    for p in account.get("propertySummaries", []):
        try:
            streams = api.list_all(f"v1beta/{p['property']}/dataStreams", "dataStreams")
        except RuntimeError:
            continue
        for s in streams:
            if s.get("webStreamData", {}).get("measurementId", "").upper() == mid.upper():
                prop = api.get(f"v1beta/{p['property']}") or {"name": p["property"], "displayName": p.get("displayName")}
                print(f"✓ Propriété existante retrouvée via {mid} : {prop['name']} « {prop.get('displayName')} »")
                return prop, s
    return None, None


def ensure_property(api: Admin, account: dict) -> dict:
    for p in account.get("propertySummaries", []):
        if p.get("displayName") == PROPERTY_NAME:
            print(f"✓ Propriété déjà existante : {p['property']} ({PROPERTY_NAME})")
            return api.get(f"v1beta/{p['property']}") or p
    body = {
        "parent": account["account"],
        "displayName": PROPERTY_NAME,
        "timeZone": TIME_ZONE,
        "currencyCode": CURRENCY,
        "industryCategory": INDUSTRY,
        "propertyType": "PROPERTY_TYPE_ORDINARY",
    }
    prop = api.call("POST", "v1beta/properties", body, fake={"name": "properties/000000000", "displayName": PROPERTY_NAME})
    print(f"✓ Propriété créée : {prop['name']}")
    return prop


def ensure_stream(api: Admin, prop: str) -> dict:
    for s in api.list_all(f"v1beta/{prop}/dataStreams", "dataStreams"):
        if s.get("type") == "WEB_DATA_STREAM" and s.get("webStreamData", {}).get("defaultUri", "").rstrip("/") == STREAM_URI:
            print(f"✓ Flux web déjà existant : {s['name']} → {s['webStreamData'].get('measurementId')}")
            return s
    body = {"type": "WEB_DATA_STREAM", "displayName": STREAM_NAME, "webStreamData": {"defaultUri": STREAM_URI}}
    s = api.call("POST", f"v1beta/{prop}/dataStreams", body,
                 fake={"name": f"{prop}/dataStreams/0", "webStreamData": {"measurementId": PLACEHOLDER, "defaultUri": STREAM_URI}})
    print(f"✓ Flux web créé : {s['name']} → ID de mesure {s['webStreamData']['measurementId']}")
    return s


def set_enhanced_measurement(api: Admin, stream: str):
    mask = ",".join(ENHANCED_MEASUREMENT.keys())
    api.call("PATCH", f"v1beta/{stream}/enhancedMeasurementSettings", ENHANCED_MEASUREMENT, params={"updateMask": mask})
    print("✓ Mesure améliorée réglée (scroll, clics sortants, téléchargements ; recherche/vidéo/formulaires désactivés)")


def set_retention(api: Admin, prop: str):
    body = {"eventDataRetention": DATA_RETENTION, "resetUserDataOnNewActivity": RESET_ON_NEW_ACTIVITY}
    api.call("PATCH", f"v1beta/{prop}/dataRetentionSettings", body, params={"updateMask": "eventDataRetention,resetUserDataOnNewActivity"})
    print("✓ Conservation des données : 14 mois, réinitialisée à chaque nouvelle activité")


def disable_google_signals(api: Admin, prop: str):
    try:
        api.call("PATCH", f"v1alpha/{prop}/googleSignalsSettings", {"state": "GOOGLE_SIGNALS_DISABLED"}, params={"updateMask": "state"})
        print("✓ Google Signals désactivé (à activer plus tard seulement avec un consentement opt-in)")
    except RuntimeError as exc:
        print(f"⚠️  Google Signals non modifié (à vérifier dans l'interface) : {exc.splitlines()[0]}")


def ensure_custom_dimensions(api: Admin, prop: str):
    existing = {d.get("parameterName") for d in api.list_all(f"v1beta/{prop}/customDimensions", "customDimensions")}
    for param, label, desc in CUSTOM_DIMENSIONS:
        if param in existing:
            print(f"  = dimension déjà présente : {param}")
            continue
        api.call("POST", f"v1beta/{prop}/customDimensions",
                 {"parameterName": param, "displayName": label, "description": desc, "scope": "EVENT"})
        print(f"  + dimension créée : {param} « {label} »")
    print("✓ Dimensions personnalisées")


def ensure_key_events(api: Admin, prop: str):
    try:
        existing = {k.get("eventName") for k in api.list_all(f"v1beta/{prop}/keyEvents", "keyEvents")}
        path, key = f"v1beta/{prop}/keyEvents", "keyEvents"
    except RuntimeError:
        # anciens déploiements de l'API : conversionEvents
        existing = {k.get("eventName") for k in api.list_all(f"v1beta/{prop}/conversionEvents", "conversionEvents")}
        path, key = f"v1beta/{prop}/conversionEvents", "conversionEvents"
    for name, counting in KEY_EVENTS:
        if name in existing:
            print(f"  = événement clé déjà présent : {name}")
            continue
        api.call("POST", path, {"eventName": name, "countingMethod": counting})
        print(f"  + événement clé créé : {name} ({counting})")
    print(f"✓ Événements clés ({key})")


def ensure_users(api: Admin, prop: str):
    try:
        existing = {b.get("user", "").lower() for b in api.list_all(f"v1alpha/{prop}/accessBindings", "accessBindings")}
    except RuntimeError as exc:
        print(f"⚠️  Impossible de lire les accès (scope analytics.manage.users manquant ?) : {exc.splitlines()[0]}")
        return
    for email, role in USERS:
        if email.lower() in existing:
            print(f"  = accès déjà présent : {email}")
            continue
        try:
            api.call("POST", f"v1alpha/{prop}/accessBindings", {"user": email, "roles": [f"predefinedRoles/{role}"]})
            print(f"  + accès donné : {email} → {role}")
        except RuntimeError as exc:
            print(f"  ⚠️  {email} non ajouté : {exc.splitlines()[0]}")
    print("✓ Accès utilisateurs")


def link_google_ads(api: Admin, prop: str, customer_id: str):
    cid = customer_id.replace("-", "").strip()
    for link in api.list_all(f"v1beta/{prop}/googleAdsLinks", "googleAdsLinks"):
        if link.get("customerId") == cid:
            print(f"✓ Google Ads déjà associé : {cid}")
            return
    api.call("POST", f"v1beta/{prop}/googleAdsLinks", {"customerId": cid, "adsPersonalizationEnabled": False})
    print(f"✓ Google Ads associé : {cid} (personnalisation des annonces désactivée)")


def write_measurement_id(measurement_id: str) -> None:
    if not GTM_JSON.exists():
        print(f"⚠️  Export GTM introuvable : {GTM_JSON}")
        return
    txt = GTM_JSON.read_text(encoding="utf-8")
    if PLACEHOLDER not in txt and measurement_id in txt:
        print(f"✓ Export GTM déjà à jour ({measurement_id})")
        return
    import re
    txt2 = re.sub(r"G-[A-Z0-9]{6,12}", measurement_id, txt) if PLACEHOLDER not in txt else txt.replace(PLACEHOLDER, measurement_id)
    GTM_JSON.write_text(txt2, encoding="utf-8")
    print(f"✓ ID de mesure écrit dans {GTM_JSON.relative_to(HERE.parent.parent)} → {measurement_id}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", help="Nom ou ID du compte GA dans lequel créer la propriété (ex. ESCAPAD ou 123456789)")
    ap.add_argument("--list-accounts", action="store_true", help="Liste les comptes GA visibles et s'arrête")
    ap.add_argument("--property", help="ID numérique d'une propriété existante à configurer (sinon retrouvée via l'ID de mesure connu)")
    ap.add_argument("--measurement-id", help="ID de mesure G-… d'une propriété existante à retrouver (défaut : KNOWN_MEASUREMENT_ID)")
    ap.add_argument("--ads-customer-id", help="ID client Google Ads à associer (format 123-456-7890), optionnel")
    ap.add_argument("--no-users", action="store_true", help="Ne pas ajouter les accès utilisateurs")
    ap.add_argument("--set-measurement-id", metavar="G-XXXXXXXX", help="N'écrit que l'ID de mesure dans l'export GTM (propriété créée à la main)")
    ap.add_argument("--token", help="Jeton OAuth (sinon GA_ACCESS_TOKEN ou gcloud ADC)")
    ap.add_argument("--dry-run", action="store_true", help="Affiche les appels sans rien créer")
    args = ap.parse_args()

    if args.set_measurement_id:
        mid = args.set_measurement_id.strip().upper()
        if not mid.startswith("G-"):
            sys.exit("L'ID de mesure commence par G- (Admin GA4 → Flux de données → lecafecentral.fr).")
        write_measurement_id(mid)
        return

    token = get_token(args)
    api = Admin(token, args.dry_run)

    if args.list_accounts:
        for a in api.list_all("v1beta/accountSummaries", "accountSummaries"):
            print(f"{a['account'].removeprefix('accounts/'):>12}  {a.get('displayName')}")
            for p in a.get("propertySummaries", []):
                print(f"               └─ {p['property'].removeprefix('properties/'):>10}  {p.get('displayName')}")
        return

    print(f"\n▶ Propriété « {PROPERTY_NAME} » — {'DRY-RUN' if args.dry_run else 'création'}\n")
    account = pick_account(api, args.account)
    print(f"Compte GA : {account.get('displayName')} ({account['account']})")

    prop, stream = None, None
    mid_wanted = (args.measurement_id or KNOWN_MEASUREMENT_ID or "").strip()
    if args.property:
        prop = api.get(f"v1beta/properties/{args.property.removeprefix('properties/')}")
        if not prop:
            sys.exit(f"Propriété {args.property} introuvable ou inaccessible.")
        print(f"✓ Propriété existante : {prop['name']} « {prop.get('displayName')} »")
    elif mid_wanted:
        prop, stream = find_property_by_measurement_id(api, account, mid_wanted)
        if prop is None and not api.dry_run:
            sys.exit(f"Aucune propriété du compte ne porte l'ID de mesure {mid_wanted}. "
                     "Vérifie le compte (--account) ou passe --property <ID numérique>.")
    if prop is None:
        prop = ensure_property(api, account)
    prop_name = prop["name"]
    if stream is None:
        stream = ensure_stream(api, prop_name)
    measurement_id = stream["webStreamData"]["measurementId"]

    set_enhanced_measurement(api, stream["name"])
    set_retention(api, prop_name)
    disable_google_signals(api, prop_name)
    ensure_custom_dimensions(api, prop_name)
    ensure_key_events(api, prop_name)
    if not args.no_users:
        ensure_users(api, prop_name)
    if args.ads_customer_id:
        link_google_ads(api, prop_name, args.ads_customer_id)

    summary = {
        "account": account["account"],
        "property": prop_name,
        "propertyId": prop_name.removeprefix("properties/"),
        "displayName": PROPERTY_NAME,
        "dataStream": stream["name"],
        "measurementId": measurement_id,
        "adminUrl": f"https://analytics.google.com/analytics/web/#/p{prop_name.removeprefix('properties/')}/admin",
        "gtmContainer": "GTM-TVBDT8RJ",
    }
    if not args.dry_run:
        OUTPUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_measurement_id(measurement_id)
        print(f"✓ Récapitulatif écrit : {OUTPUT_JSON}")

    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(
        "\nÉtapes suivantes (interface, non couvertes par l'API) — voir analytics/README.md :\n"
        "  1. Admin → Collecte et modification des données → Filtres de données → « Internal Traffic » → Actif\n"
        "  2. Admin → Flux de données → lecafecentral.fr → Configurer les paramètres de la balise → Lister les références indésirables → zenchef.com\n"
        "  3. GTM : importer analytics/gtm/GTM-TVBDT8RJ-ga4-import.json (Fusionner), tester en aperçu, publier\n"
        "  4. Admin → Associations de produits → Google Ads (si non fait avec --ads-customer-id)\n"
    )


if __name__ == "__main__":
    main()

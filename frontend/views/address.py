import pandas as pd
import pydeck as pdk
import streamlit as st

from lib import api, charts, ui

st.title("Analyse d’adresse")
st.caption("Rapport complet d’un bien : bâtiment, urbanisme, risques, environnement, services, marché.")

# ----------------------------------------------------------------- Recherche et choix de l'adresse
saved = api.try_get("/addresses", {"items": []}, limit=200)["items"]
search, existing = st.columns(2)
with search:
    query = st.text_input("Rechercher une adresse", placeholder="2 rue de la République, Amiens")
    candidates = api.try_get("/geo/search", [], q=query, limit=6) if len(query.strip()) >= 3 else []
    labels = {c["banId"]: f"{c['label']} ({c['type']}, score {ui.number(c['score'], 2)})" for c in candidates}
    choice = st.selectbox("Résultats", list(labels), format_func=labels.get, placeholder="Saisir au moins 3 caractères", index=0 if labels else None)
    if choice and st.button("Analyser cette adresse", type="primary"):
        label = next(c["label"] for c in candidates if c["banId"] == choice)
        result = ui.run(
            "Collecte des données de l’adresse auprès d’une quarantaine de sources (1 à 3 minutes la première fois)",
            lambda: api.post("/addresses/collect", {"q": label}),
        )
        if result:
            st.session_state["address_id"] = result["addressId"]
            st.session_state["address_collect"] = result
            st.rerun()
with existing:
    names = {a["id"]: a["label"] for a in saved}
    # Lien direct vers un rapport : ?id=1
    linked = st.query_params.get("id", "")
    current = int(linked) if linked.isdigit() else st.session_state.get("address_id")
    picked = st.selectbox(
        "Adresses déjà analysées", list(names), format_func=names.get,
        index=list(names).index(current) if current in names else (0 if names else None),
        placeholder="Aucune adresse enregistrée",
    )
    if picked:
        st.session_state["address_id"] = picked

address_id = st.session_state.get("address_id")
if not address_id:
    st.info("Rechercher une adresse ou en choisir une déjà analysée.")
    st.stop()

if last := st.session_state.pop("address_collect", None):
    st.success(f"Collecte terminée en {ui.number(last['durationMs'] / 1000)} s : {ui.collect_summary(last['summary'])}.")
    with st.expander("Détail par source"):
        ui.outcomes_table([o for m in last["modules"] for o in m["outcomes"]])

try:
    report = api.get(f"/addresses/{address_id}/report")
except api.ApiError as err:
    st.error(err.message)
    st.stop()

address = report["address"]
p = {"lat": address["latitude"], "lon": address["longitude"]}
head, refresh = st.columns([4, 1], vertical_alignment="center")
head.header(address["label"])
head.caption(
    f"INSEE {address['inseeCode']} · parcelle {address.get('parcelIdu') or 'n.d.'} · "
    f"bâtiment RNB {address.get('rnbId') or 'n.d.'} · {address['latitude']}, {address['longitude']}"
)
if refresh.button("Actualiser la collecte", width="stretch"):
    result = ui.run("Nouvelle collecte (les sources encore valides sont lues dans le cache)", lambda: api.post(f"/addresses/{address_id}/collect"))
    if result:
        st.session_state["address_collect"] = result
        st.rerun()


def section(key: str) -> dict:
    """Section du rapport ; une section en erreur est signalée et rendue vide."""
    data = report.get(key) or {}
    if set(data) == {"error"}:
        st.error(f"Section indisponible : {data['error']}")
        return {}
    return data


building = section("building")
risks = section("risks")
services = section("services")
mobility = section("mobility")
energy = section("energy")
connectivity = section("connectivity")
price_index = report["market"]["priceIndex"]

# ----------------------------------------------------------------- Chiffres clés
b = building.get("building") or {}
dpe = (building.get("dpe") or {}).get("reference") or {}
overall = [x for x in price_index if x["propertyType"] == "Ensemble"]
present = [r for r in risks.get("atAddress", []) if r["present"]]
row = [*st.columns(3), *st.columns(3)]
ui.tile(row[0], "Construction", str(b.get("constructionYear") or "n.d."), f"{b.get('levels') or '?'} niveaux, {b.get('dwellings') or '?'} logements")
ui.tile(row[1], "DPE de référence", dpe.get("energyClass") or "n.d.", f"{ui.number(dpe.get('energyKwhM2'))} kWh/m²/an" if dpe else None)
ui.tile(
    row[2], "Prix médian commune",
    ui.euro(overall[-1]["medianPriceM2"]) + "/m²" if overall else "n.d.",
    f"{ui.number(overall[-1]['salesCount'])} ventes en {overall[-1]['year']}" if overall else None,
)
ui.tile(row[3], "Aléas recensés", ui.number(len(present)), "à l’adresse ou sur la commune")
ui.tile(row[4], "Arrêts à moins de 800 m", ui.number((mobility.get("transit") or {}).get("stopsWithin800m")))
ui.tile(row[5], "Fibre (commune)", ui.pct((connectivity.get("fixed") or {}).get("ftthRate")), "locaux éligibles FttH")

tabs = st.tabs([
    "Carte", "Bâtiment", "Urbanisme", "Risques", "Eau et climat", "Nuisances", "Énergie et réseaux",
    "Services et écoles", "Mobilité", "Marché",
])

# ----------------------------------------------------------------- Carte
with tabs[0]:
    LAYERS = {
        "Adresse": (charts.SERIES[7], [{"name": address["label"], "kind": "Adresse", "latitude": p["lat"], "longitude": p["lon"]}]),
        "Écoles": (charts.SERIES[0], [
            {"name": s["name"], "kind": s.get("schoolType") or "École", "latitude": s["latitude"], "longitude": s["longitude"]}
            for s in services.get("schools", [])[:60]
        ]),
        "Services": (charts.SERIES[2], [
            {"name": s.get("name") or category, "kind": category, "latitude": s["latitude"], "longitude": s["longitude"]}
            for category, group in (services.get("byCategory") or {}).items()
            for s in group["nearest"]
        ]),
        "Arrêts de transport": (charts.SERIES[1], [
            {"name": s.get("name") or "Arrêt", "kind": mode, "latitude": s["latitude"], "longitude": s["longitude"]}
            for mode, stops in ((mobility.get("transit") or {}).get("byMode") or {}).items()
            for s in stops
        ]),
    }
    shown = st.pills("Calques", list(LAYERS), selection_mode="multi", default=list(LAYERS))
    points = [
        {**pt, "color": charts.hex_to_rgb(color), "layer": name, "radius": 14 if name == "Adresse" else 8}
        for name, (color, pts) in LAYERS.items()
        if name in (shown or [])
        for pt in pts
        if pt["latitude"] is not None and pt["longitude"] is not None
    ]
    layers = []
    parcel = (address.get("parcel") or {}).get("geometry")
    if parcel:
        layers.append(pdk.Layer(
            "GeoJsonLayer", {"type": "Feature", "geometry": parcel, "properties": {"name": "Parcelle", "kind": address["parcelIdu"], "layer": "Cadastre"}},
            stroked=True, filled=True, get_fill_color=[42, 120, 214, 40], get_line_color=[42, 120, 214], line_width_min_pixels=2, pickable=True,
        ))
    layers.append(pdk.Layer(
        "ScatterplotLayer", points, get_position="[longitude, latitude]", get_fill_color="color", get_radius="radius",
        radius_units="pixels", stroked=True, get_line_color=[252, 252, 251], line_width_min_pixels=2, pickable=True,
    ))
    st.pydeck_chart(
        pdk.Deck(
            layers=layers,
            initial_view_state=pdk.ViewState(longitude=p["lon"], latitude=p["lat"], zoom=15),
            map_style="light",
            tooltip={"html": "<b>{name}</b><br/>{layer} · {kind}"},
        ),
        height=520,
    )
    legend = " ".join(
        f'<span style="margin-right:16px;white-space:nowrap"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
        f'background:{color};margin-right:6px"></span>{name}</span>'
        for name, (color, _) in LAYERS.items()
        if name in (shown or [])
    )
    st.markdown(f'<div style="font-size:13px;color:#52514e">{legend}</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------- Bâtiment
with tabs[1]:
    left, right = st.columns(2)
    with left:
        st.subheader("Bâtiment")
        facts = [
            ("Usage principal", b.get("mainUsage")), ("Année de construction", b.get("constructionYear")),
            ("Hauteur", f"{ui.number(b.get('heightM'))} m" if b.get("heightM") is not None else None),
            ("Niveaux", b.get("levels")), ("Logements", b.get("dwellings")),
            ("Emprise au sol", f"{ui.number(b.get('footprintM2'))} m²" if b.get("footprintM2") is not None else None),
            ("Murs", b.get("wallMaterial")), ("Toiture", b.get("roofMaterial")),
            ("Hauteur sous plafond", f"{ui.number(building.get('ceilingHeightM'), 1)} m" if building.get("ceilingHeightM") else None),
        ]
        st.dataframe(
            pd.DataFrame([{"Caractéristique": k, "Valeur": str(v)} for k, v in facts if v is not None]), hide_index=True, width="stretch"
        )
        st.caption("Sources : Référentiel national des bâtiments, BDNB.")
        presumptions = building.get("presumptions") or {}
        if presumptions:
            st.subheader("Diagnostics et location")
            st.write(
                f"Plomb : {'présomption (logement d’avant 1949)' if presumptions.get('leadRisk') else 'pas de présomption'}. "
                f"Amiante : {'présomption (permis d’avant juillet 1997)' if presumptions.get('asbestosRisk') else 'pas de présomption'}."
            )
            if presumptions.get("rentalBanDate"):
                st.write(
                    f"Interdiction de louer selon le DPE : {'déjà en vigueur' if presumptions.get('rentalBanned') else 'à compter du'} "
                    f"{presumptions['rentalBanDate']}."
                )
    with right:
        condo = building.get("condominium")
        if condo:
            st.subheader("Copropriété")
            st.write(
                f"**{condo.get('name') or condo['registrationNumber']}** : {condo.get('totalLots') or '?'} lots dont "
                f"{condo.get('housingLots') or '?'} d’habitation. Syndic {condo.get('syndicType') or 'n.d.'} "
                f"({condo.get('syndicName') or 'n.d.'}), {str(condo.get('mandateStatus') or '').lower()}."
            )
            st.caption("Source : registre national des copropriétés.")
        st.subheader("Diagnostics de performance énergétique à proximité")
        ui.table((building.get("dpe") or {}).get("all", []), {
            "addressLabel": "Adresse", "issuedAt": "Date", "energyClass": "DPE", "ghgClass": "GES", "energyKwhM2": "kWh/m²/an",
            "livingAreaM2": "Surface m²", "heatingEnergy": "Chauffage", "distanceM": "Distance m",
        }, height=330)
        st.caption("Source : ADEME.")

# ----------------------------------------------------------------- Urbanisme
with tabs[2]:
    urbanism = section("urbanism")
    zone = urbanism.get("currentZone")
    if zone:
        st.subheader(f"Zone {zone['label']} du PLU")
        st.write(f"{zone.get('labelLong') or ''} (type {zone.get('zoneType')}, document approuvé le {zone.get('approvedAt') or 'n.d.'}).")
    else:
        st.info("Aucune zone de PLU numérisée à cette adresse (commune au RNU ou document non publié).")
    left, right = st.columns(2)
    with left:
        st.subheader("Prescriptions à proximité")
        prescriptions = [*urbanism.get("reservedLocations", []), *urbanism.get("protectedLandscape", []), *urbanism.get("otherPrescriptions", [])]
        ui.table(prescriptions, {"label": "Libellé", "typeLabel": "Nature", "typeCode": "Code", "distanceM": "Distance m"}, height=300)
    with right:
        st.subheader("Monuments historiques")
        perimeters = urbanism.get("historicMonumentPerimeter", [])
        if perimeters:
            st.warning(f"L’adresse est dans {len(perimeters)} périmètre(s) de protection : avis de l’architecte des Bâtiments de France requis.")
        ui.table(urbanism.get("monuments", []), {"name": "Monument", "protectionType": "Protection", "distanceM": "Distance m"}, height=300)
    st.caption("Sources : Géoportail de l’urbanisme, ministère de la Culture.")

# ----------------------------------------------------------------- Risques
with tabs[3]:
    left, right = st.columns(2)
    with left:
        st.subheader("Aléas")
        ui.table(present, {"label": "Aléa", "category": "Famille", "addressStatus": "À l’adresse", "communeStatus": "Sur la commune"})
        commune = risks.get("commune") or {}
        st.write(f"Potentiel radon : classe {commune.get('radonClass') or 'n.d.'}. Sismicité : zone {commune.get('seismicZone') or 'n.d.'}.")
        catnat = risks.get("catnat") or {}
        if catnat.get("byHazard"):
            st.subheader(f"{catnat['total']} arrêtés de catastrophe naturelle")
            hazards = pd.DataFrame([{"Aléa": k, "Arrêtés": v} for k, v in catnat["byHazard"].items()]).sort_values("Arrêtés", ascending=False)
            charts.bars(hazards, "Aléa", "Arrêtés", horizontal=True, value_title="Arrêtés", sort=list(hazards["Aléa"]), height=40 + 44 * len(hazards))
    with right:
        st.subheader("Sites à proximité")
        sites = risks.get("sites") or {}
        kinds = {"seveso": "Seveso", "icpe": "Installation classée", "pollutedSoils": "Sol pollué ou ancien site industriel",
                 "cavities": "Cavité souterraine", "groundMovements": "Mouvement de terrain"}
        rows = [{**s, "kind": label} for key, label in kinds.items() for s in sites.get(key, [])]
        ui.table(sorted(rows, key=lambda s: s["distanceM"]), {"kind": "Type", "name": "Nom", "status": "État", "distanceM": "Distance m"}, height=420)
    st.caption("Source : Géorisques.")

# ----------------------------------------------------------------- Eau et climat
with tabs[4]:
    water = section("water")
    climate = section("climate")
    left, right = st.columns(2)
    with left:
        st.subheader("Eau potable")
        drinking = water.get("drinkingWater") or {}
        st.write(f"Réseau {drinking.get('network') or 'n.d.'}, distribué par {drinking.get('distributor') or 'n.d.'}.")
        rows = [
            {
                "Paramètre": x.get("label") or x["key"], "Valeur": ui.number(x["value"], 2) if x.get("value") is not None else "n.d.",
                "Unité": x.get("unit"), "Dépassement": {True: "⚠ Oui", False: "Non"}.get(x.get("exceedsLimit"), "n.d."),
                "Repère": x.get("reference"),
            }
            for x in drinking.get("parameters", [])
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        if drinking.get("lastConclusion"):
            st.caption(f"Dernière conclusion sanitaire : {drinking['lastConclusion']}")
        droughts = water.get("drought", [])
        if droughts:
            # Une même zone est publiée pour les eaux superficielles, souterraines et l'eau potable.
            zones = dict.fromkeys(f"{' '.join(d['zoneName'].split())} ({d['severity']})" for d in droughts)
            st.warning("Restrictions d’eau en cours : " + " ; ".join(zones) + ".")
        st.caption("Sources : Hub’Eau, VigiEau.")
    with right:
        st.subheader(f"Climat observé ({(climate.get('observedMeta') or {}).get('period', 'n.d.')})")
        names = {
            "hot_days_per_year": "Jours de forte chaleur", "tropical_nights_per_year": "Nuits tropicales", "frost_days_per_year": "Jours de gel",
            "snow_days_per_year": "Jours de neige", "strong_wind_days_per_year": "Jours de vent fort",
            "precipitation_per_year": "Précipitations", "sunshine_hours_per_year": "Ensoleillement",
        }
        rows = [
            {"Indicateur": label, "Valeur": f"{ui.number(v['value'], 1)} {v['unit']}"}
            for key, label in names.items()
            if (v := (climate.get("observed") or {}).get(key))
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        ensemble = (climate.get("projections2050") or {}).get("ensemble") or {}
        hot = ensemble.get("hot_days_per_year")
        if hot:
            st.write(
                f"Projection 2041-2050 : {ui.number(hot.get('2041-2050'), 1)} jours de forte chaleur par an, "
                f"contre {ui.number(hot.get('2005-2014'), 1)} sur 2005-2014 (moyenne de {len(climate['projections2050'].get('models', []))} modèles)."
            )
        solar = climate.get("solar")
        if solar:
            st.write(f"Potentiel solaire : {ui.number(solar['yearlyKwhPerKwp'])} kWh par kWc installé et par an.")
        st.caption("Sources : Open-Meteo (ERA5, CMIP6), PVGIS.")

# ----------------------------------------------------------------- Nuisances
with tabs[5]:
    nuisances = section("nuisances")
    names = {
        "nightlife": "Bars et vie nocturne", "place_of_worship": "Lieux de culte", "marketplace": "Marchés", "concert_venue": "Salles de spectacle",
        "railway": "Voies ferrées", "power_line": "Lignes électriques", "motorway": "Autoroutes et voies rapides", "industrial": "Zones industrielles",
        "airport": "Aérodromes", "school": "Établissements scolaires", "stadium": "Stades",
    }
    rows = [
        {"Source de nuisance": names.get(k, k), "Nombre": v["count"], "Le plus proche (m)": v.get("nearestM"),
         "Nom": (v.get("nearest") or {}).get("name") or (v.get("nearest") or {}).get("subcategory")}
        for k, v in (nuisances.get("summary") or {}).items()
    ]
    st.subheader(f"Dans un rayon de {ui.number(nuisances.get('radiusM'))} m")
    if rows:
        st.dataframe(pd.DataFrame(rows).sort_values("Le plus proche (m)"), hide_index=True, width="stretch")
    else:
        st.info("Aucune donnée (la source OpenStreetMap peut être saturée : relancer la collecte).")
    plans = nuisances.get("airportNoisePlans", [])
    if plans:
        st.write("Plans d’exposition au bruit à proximité : " + ", ".join(f"{x['name']} ({ui.number(x['distanceM'])} m)" for x in plans) + ".")
    st.caption("Sources : OpenStreetMap, Géoplateforme (PEB), OpenSky.")
    ui.not_covered(nuisances.get("notCovered"))

# ----------------------------------------------------------------- Énergie et réseaux
with tabs[6]:
    left, right = st.columns(2)
    with left:
        st.subheader("Réseaux d’énergie")
        heat, gas = energy.get("heatNetwork") or {}, energy.get("gasNetwork") or {}
        st.write(
            f"Réseau de chaleur : {'disponible' if heat.get('available') else 'non disponible'}"
            + (f" à {ui.number(heat['distanceM'])} m ({heat.get('networkName')})." if heat.get("distanceM") is not None else ".")
        )
        st.write(f"Gaz de ville : {'commune desservie' if gas.get('available') else 'commune non desservie'} ({gas.get('operatorName') or 'n.d.'}).")
        average = (energy.get("electricity") or {}).get("communeAverage") or []
        if average:
            st.write(f"Consommation électrique résidentielle moyenne de la commune : {ui.number(average[0]['communeAvgMwh'], 2)} MWh par logement ({average[0]['year']}).")
        st.caption("Sources : France Chaleur Urbaine, GRDF, Enedis.")
    with right:
        st.subheader("Internet et mobile")
        fixed = connectivity.get("fixed") or {}
        st.write(f"Fibre : {ui.pct(fixed.get('ftthRate'))} des locaux de la commune éligibles ({fixed.get('periodDate') or 'n.d.'}).")
        ui.table(connectivity.get("mobile", []), {
            "operator": "Opérateur", "sitesWithin1km": "Sites à moins de 1 km", "nearest4gM": "4G la plus proche (m)", "nearest5gM": "5G la plus proche (m)",
        })
        st.caption("Source : ARCEP.")

# ----------------------------------------------------------------- Services et écoles
with tabs[7]:
    names = {"bakery": "Boulangeries", "childcare": "Crèches", "general_practitioner": "Médecins généralistes",
             "hospital": "Hôpitaux et cliniques", "pharmacy": "Pharmacies", "supermarket": "Supermarchés"}
    rows = [
        {"Service": names.get(k, k), "À moins de 2 km": v["countWithin2km"],
         "Le plus proche": (v["nearest"][0].get("name") if v["nearest"] else None),
         "Distance (m)": (v["nearest"][0]["distanceM"] if v["nearest"] else None)}
        for k, v in (services.get("byCategory") or {}).items()
    ]
    left, right = st.columns(2)
    with left:
        st.subheader("Services de proximité")
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        kinds = {"nearest_emergency": "Urgences", "nearest_general_practitioner": "Médecin généraliste", "nearest_pharmacy": "Pharmacie"}
        modes = {"car": "Voiture", "pedestrian": "À pied"}
        st.subheader("Temps de trajet")
        ui.table(
            [
                {
                    **t, "kind": kinds.get(t["destinationKind"], t["destinationKind"]), "mode": modes.get(t["profile"], t["profile"]),
                    "minutes": round(t["durationS"] / 60),
                }
                for t in services.get("travelTimes", [])
            ],
            {"kind": "Destination", "destinationLabel": "Lieu", "mode": "Mode", "minutes": "Minutes", "distanceM": "Distance m"},
        )
        st.caption("Sources : Recherche d’entreprises, OpenStreetMap, IGN.")
    with right:
        st.subheader("Établissements scolaires")
        ui.table(services.get("schools", []), {
            "name": "Établissement", "schoolType": "Type", "sector": "Secteur", "ips": "IPS", "avgClassSize": "Élèves par classe", "distanceM": "Distance m",
        }, height=420)
        st.caption("IPS : indice de position sociale. Source : ministère de l’Éducation nationale.")

# ----------------------------------------------------------------- Mobilité
with tabs[8]:
    transit = mobility.get("transit") or {}
    charging = mobility.get("charging") or {}
    cycling = mobility.get("cycling") or {}
    row = st.columns(4)
    ui.tile(row[0], "Arrêts à moins de 800 m", ui.number(transit.get("stopsWithin800m")))
    ui.tile(row[1], "Points de recharge à moins de 2 km", ui.number(charging.get("pointsWithin2km")), f"dont {ui.number(charging.get('fastChargers'))} rapides")
    ui.tile(row[2], "Aménagements cyclables", ui.number(((cycling.get("cycle_infrastructure_within_1km") or {}).get("value") or 0) / 1000, 1, "km"), "dans un rayon de 1 km")
    ui.tile(row[3], "Piste la plus proche", ui.number((cycling.get("nearest_cycle_infrastructure") or {}).get("value"), 0, "m"))
    left, right = st.columns(2)
    with left:
        st.subheader("Arrêts les plus proches")
        stops = [{**s, "mode": mode} for mode, group in (transit.get("byMode") or {}).items() for s in group]
        ui.table(sorted(stops, key=lambda s: s["distanceM"]), {"name": "Arrêt", "mode": "Mode", "network": "Réseau", "distanceM": "Distance m"})
    with right:
        st.subheader("Bornes de recharge")
        ui.table(charging.get("nearest", []), {"stationName": "Station", "operatorName": "Opérateur", "powerKw": "kW", "distanceM": "Distance m"})
    st.caption("Sources : OpenStreetMap, base nationale IRVE, transport.data.gouv.fr.")

# ----------------------------------------------------------------- Marché
with tabs[9]:
    left, right = st.columns(2)
    with left:
        st.subheader("Prix médian au m² dans la commune")
        types = ["Ensemble", "Appartement", "Maison"]
        df = pd.DataFrame(price_index)
        if df.empty:
            st.info("Aucune vente DVF chargée.")
        else:
            df = df[df["propertyType"].isin(types)].rename(columns={"year": "Année", "propertyType": "Type", "medianPriceM2": "Prix médian"})
            charts.line(df, "Année", "Prix médian", series="Type", order=types, y_title="€/m²")
    with right:
        radius = st.select_slider("Ventes autour de l’adresse, rayon en mètres", [100, 200, 300, 500, 1000], value=300)
        sales = api.try_get(f"/addresses/{address_id}/dvf", [], radius=radius)
        sales = sales if isinstance(sales, list) else sales.get("items", [])
        dwellings = [s for s in sales if s.get("propertyType") in ("Appartement", "Maison")]
        st.subheader(f"{len(dwellings)} ventes de logements à moins de {radius} m")
        ui.table(sorted(dwellings, key=lambda s: s["mutationDate"], reverse=True), {
            "mutationDate": "Date", "propertyType": "Type", "priceEur": "Prix €", "builtAreaM2": "Surface m²",
            "priceM2": "€/m²", "rooms": "Pièces", "distanceM": "Distance m",
        }, height=330)
    nearby = api.try_get(f"/addresses/{address_id}/listings", {"items": []}, radius=1500)["items"]
    st.subheader(f"{len(nearby)} annonces en ligne à moins de 1,5 km")
    if nearby:
        ui.table(nearby, {"title": "Annonce", "transactionType": "Transaction", "propertyType": "Bien", "priceEur": "Prix €",
                          "areaM2": "Surface m²", "priceM2": "€/m²", "distanceM": "Distance m", "source": "Site"})
    st.caption("Sources : DVF (DGFiP), annonces remontées par le scraping.")

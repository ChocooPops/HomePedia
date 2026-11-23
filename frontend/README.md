# HomePedia — Frontend

Carte de la France (Vue 3 + Leaflet) : régions, départements et communes, recherche de lieux et d'adresses,
et logements disponibles dans la zone affichée. Les données viennent de l'API du [backend](../backend/README.md).

## Démarrage

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

L'API doit tourner (`docker compose up -d` dans `backend/`). En développement, les appels à `/api/*` passent par le
proxy Vite vers `http://127.0.0.1:8000` (variable `API_PROXY_TARGET` pour en changer) : pas de souci de CORS.
`127.0.0.1` plutôt que `localhost`, car sous Windows `[::1]:8000` peut être occupé par WSL (`wslrelay`).

`VITE_API_URL` remplace `/api` par une URL d'API directe (le backend doit alors autoriser l'origine en CORS) ;
la laisser vide pour utiliser le proxy.

## Utilisation

| Zoom      | Contours affichés                     | Logements |
|-----------|---------------------------------------|-----------|
| < 7       | régions                               | aucun : « Zoomez sur un département » |
| 7 à 9     | départements des régions visibles     | ceux de la zone affichée |
| ≥ 10      | communes du département au centre     | ceux de la zone affichée |

- **Logements de la zone** : à chaque déplacement, la carte envoie l'emprise visible et le département au centre.
  L'API répond tout de suite avec les annonces déjà en base. Si ce département n'en a encore aucune, elle interroge
  SeLoger en arrière-plan (≈ 90 annonces, jusqu'à une minute) : la liste affiche « Recherche de nouvelles
  annonces sur SeLoger… elles s'afficheront automatiquement », le frontend redemande la zone toutes les 4 s sans
  vider la liste, puis indique le nombre d'annonces récupérées.
- **Clic sur une commune** (zoom ≥ 10), ou commune choisie dans la recherche : toutes ses annonces, où que soit la
  carte ; la commune passe en orange et un bandeau « Commune : … ✕ » permet de revenir à la zone affichée.
  Recliquer la commune annule aussi le choix.
- **Filtres** : Louer / Acheter, type de bien (tous, appartement, maison).
- **Carte** : un point par annonce, qui ouvre sa fiche à droite. Les annonces géocodées au même endroit (souvent le
  centre d'une commune) partagent un cercle numéroté : un clic liste ces offres, et l'on choisit celle à afficher.
  Le survol d'un point résume l'offre (ou indique le nombre d'offres).
- **Liste** : photo, prix, caractéristiques, adresse et site d'origine ; cliquer une annonce la montre sur la carte,
  et inversement. Une icône remplace la photo quand l'annonce n'en a pas encore (enregistrée avant le stockage des
  photos) ou qu'elle a été retirée du site.
- **Fiche de l'annonce** (à droite, à la sélection d'une annonce) : photos, prix, caractéristiques, description,
  DPE/GES, coûts, prix au m² du secteur, écoles, visite virtuelle. La première ouverture d'une annonce lit sa page
  sur le site (un crédit, jusqu'à une minute) ; ensuite la fiche vient de la base. « Actualiser » relit la page.
  Quand plusieurs offres partagent l'endroit, la fiche affiche « Offre 2 / 3 à cet endroit » avec des flèches
  et des mini-cartes pour passer de l'une à l'autre.

Seules les annonces géocodées apparaissent ; la liste est limitée à 1 000 annonces par zone.

## Organisation

```
src/
├── App.vue                      # mise en page, état partagé (vue de la carte, filtres, commune, annonce choisie)
├── components/
│   ├── TopBar.vue               # recherche de lieux et d'adresses
│   ├── FilterPanel.vue          # filtres Louer / Acheter, type de bien
│   ├── ListingsPanel.vue        # liste des logements et messages (chargement, scraping, erreurs)
│   ├── ListingDetailPanel.vue   # fiche complète de l'annonce choisie (colonne de droite)
│   └── MapView.vue              # carte : contours, marqueurs d'annonces, clic sur une commune
├── composables/
│   ├── useListings.js           # annonces selon la vue, la commune et les filtres ; redemande toutes les 4 s pendant un scraping
│   └── useListingDetail.js      # fiche de l'annonce choisie (mise en cache pour la session)
├── services/
│   ├── api.js                   # fetch vers l'API (/api par défaut)
│   ├── geoData.js               # /geodata (contours mis en cache pour la session)
│   └── annonces.js              # /annonces/map, /annonces/{id}/details
└── utils/
    └── listing.js               # mise en forme d'une annonce (prix, pièces, adresse…)
```

## Dépannage

- **Carte vide ou liste qui ne s'affiche pas** : ouvrir la console du navigateur (F12). Une erreur du type
  « Property "…" was accessed during render but is not defined » après une modification de fichier signifie que
  Vite sert une version périmée du composant : relancer `npm run dev`.
- **Appels à l'API qui ne répondent jamais** : vérifier `curl http://127.0.0.1:8000/docs`. Sous Windows,
  `localhost:8000` peut être intercepté par WSL (`wslrelay`) ; le proxy utilise donc `127.0.0.1`.
- **« Recherche de nouvelles annonces… » qui dure** : l'API interroge SeLoger en arrière-plan (jusqu'à une minute) ;
  les journaux de l'API (`docker compose logs api`) indiquent la fin du scraping ou l'erreur.

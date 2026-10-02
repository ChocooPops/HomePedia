import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { parse } from 'csv-parse/sync';
import { DataFairClient, TabularClient } from '../../common/clients/open-data.clients';
import { LatLon } from '../../common/geo/geo.utils';
import { HttpClientService } from '../../common/http/http-client.service';

@Injectable()
export class RnbClient {
  static readonly BASE = 'https://rnb-api.beta.gouv.fr/api/alpha';

  constructor(private readonly http: HttpClientService) {}

  /** Bâtiments les plus proches d'un point (triés par distance). */
  async closest(p: LatLon, radiusM = 30): Promise<any[]> {
    const res: any = await this.http.get(`${RnbClient.BASE}/buildings/closest/`, {
      source: 'rnb',
      params: { point: `${p.lat},${p.lon}`, radius: radiusM },
    });
    return res.results ?? [];
  }
}

const BDNB_FIELDS = [
  'batiment_groupe_id', 'code_commune_insee', 'annee_construction', 'hauteur_mean', 'nb_niveau', 'nb_log',
  'mat_mur_txt', 'mat_toit_txt', 'usage_niveau_1_txt', 'classe_bilan_dpe', 'numero_immat_principal',
  'code_iris', 'surface_emprise_sol', 'altitude_sol_mean', 'l_parcelle_id',
].join(',');

/** BDNB (API PostgREST). Lien RNB -> BDNB via la table batiment_construction. */
@Injectable()
export class BdnbClient {
  static readonly BASE = 'https://api.bdnb.io/v1/bdnb/donnees';
  private readonly headers: Record<string, string>;

  constructor(
    private readonly http: HttpClientService,
    config: ConfigService,
  ) {
    const key = config.get<string>('keys.bdnb');
    this.headers = key ? { 'X-Gravitee-Api-Key': key } : {};
  }

  async groupIdForRnb(rnbId: string): Promise<string | null> {
    const rows: any[] = await this.http.get(`${BdnbClient.BASE}/batiment_construction`, {
      source: 'bdnb',
      headers: this.headers,
      params: { rnb_id: `eq.${rnbId}`, select: 'batiment_groupe_id', limit: 1 },
    });
    return rows[0]?.batiment_groupe_id ?? null;
  }

  async group(groupId: string): Promise<any | null> {
    const rows: any[] = await this.http.get(`${BdnbClient.BASE}/batiment_groupe_complet`, {
      source: 'bdnb',
      headers: this.headers,
      params: { batiment_groupe_id: `eq.${groupId}`, select: BDNB_FIELDS, limit: 1 },
    });
    return rows[0] ?? null;
  }
}

const DPE_FIELDS = [
  'numero_dpe', 'date_etablissement_dpe', 'etiquette_dpe', 'etiquette_ges', 'conso_5_usages_par_m2_ep',
  'emission_ges_5_usages_par_m2', 'annee_construction', 'periode_construction', 'type_batiment',
  'surface_habitable_logement', 'hauteur_sous_plafond', 'type_energie_principale_chauffage', 'cout_total_5_usages',
  'id_rnb', 'identifiant_ban', 'adresse_ban', 'code_insee_ban', '_geopoint',
].join(',');

@Injectable()
export class DpeClient {
  static readonly DATASET = 'https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant';

  constructor(private readonly dataFair: DataFairClient) {}

  /** DPE géolocalisés dans un rayon (m) autour du point. */
  near(p: LatLon, radiusM = 30, max = 200) {
    return this.dataFair.lines('ademe_dpe', DpeClient.DATASET, { geo_distance: `${p.lon},${p.lat},${radiusM}`, select: DPE_FIELDS }, max);
  }

  byRnb(rnbId: string, max = 200) {
    return this.dataFair.lines('ademe_dpe', DpeClient.DATASET, { id_rnb_eq: rnbId, select: DPE_FIELDS }, max);
  }
}

/** DVF géolocalisé : un CSV par commune et par année (2021 -> dernière année publiée). */
@Injectable()
export class DvfClient {
  static readonly BASE = 'https://files.data.gouv.fr/geo-dvf/latest/csv';

  constructor(private readonly http: HttpClientService) {}

  async availableYears(): Promise<number[]> {
    const html: string = await this.http.get(`${DvfClient.BASE}/`, { source: 'dvf', responseType: 'text' });
    return [...new Set([...html.matchAll(/href="[^"]*?(\d{4})\/"/g)].map((m) => Number(m[1])))].sort();
  }

  async communeYear(insee: string, year: number): Promise<Record<string, string>[]> {
    const dep = insee.startsWith('97') ? insee.slice(0, 3) : insee.slice(0, 2);
    const csv: string = await this.http.get(`${DvfClient.BASE}/${year}/communes/${dep}/${insee}.csv`, {
      source: 'dvf',
      responseType: 'text',
      allowStatuses: [404],
      timeout: 120000,
    });
    if (!csv || csv.startsWith('<')) return [];
    return parse(csv, { columns: true, skip_empty_lines: true });
  }
}

/** Registre national des copropriétés (RNIC) via l'API tabulaire data.gouv. */
@Injectable()
export class RnicClient {
  /** « Registre d'Immatriculation des Copropriétés T3 2025 - nouveau format de colonnes ». */
  static readonly RESOURCE_ID = 'cc062fa7-4a80-449c-ab73-d2856b455ec9';

  constructor(private readonly tabular: TabularClient) {}

  byRegistration(numero: string) {
    return this.tabular.query('rnic', RnicClient.RESOURCE_ID, { numero_d_immatriculation: numero }, { maxRows: 5 });
  }

  byParcel(idu: string) {
    return this.tabular.query('rnic', RnicClient.RESOURCE_ID, { reference_cadastrale_1: idu }, { maxRows: 20 });
  }
}

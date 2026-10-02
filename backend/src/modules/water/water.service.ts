import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { LatLon, pointWkt } from '../../common/geo/geo.utils';
import { entitiesWithDistance, withinRadius } from '../../common/geo/spatial-query';
import { chunk, int, isoDate, num, str } from '../../common/utils/parse';
import { CollectOutcome, CollectorService, Stamp } from '../../sources/collector.service';
import { AddressEntity } from '../geo/geo.entities';
import { HubeauClient, VigieauClient, WATER_PARAMETERS } from './water.clients';
import { DroughtRestrictionEntity, GroundwaterStationEntity, WaterQualityResultEntity } from './water.entities';

const GROUNDWATER_RADIUS_M = 10000;
const HISTORY_YEARS = 3;

/** Seuils réglementaires / repères pour l'interprétation. */
const REFERENCES: Record<string, { limit?: number; unit: string; note: string }> = {
  nitrates: { limit: 50, unit: 'mg/L', note: 'Limite de qualité : 50 mg/L' },
  total_pesticides: { limit: 0.5, unit: 'µg/L', note: 'Limite de qualité : 0,5 µg/L (total)' },
  pfas_sum_20: { limit: 0.1, unit: 'µg/L', note: 'Limite de qualité : 0,1 µg/L (somme de 20 PFAS, depuis 2026)' },
  pfas_sum_4: { unit: 'µg/L', note: 'Somme PFOA + PFNA + PFHxS + PFOS' },
  hardness: { unit: '°f', note: 'Dureté : < 15 °f eau douce, > 30 °f eau très calcaire' },
};

function normalizeWater(r: any, stamp: Stamp): Partial<WaterQualityResultEntity> {
  return {
    inseeCode: r.code_commune,
    sampleCode: r.code_prelevement,
    parameterCode: String(r.code_parametre),
    parameterLabel: str(r.libelle_parametre, 255) ?? String(r.code_parametre),
    resultNumeric: num(r.resultat_numerique),
    resultText: str(r.resultat_alphanumerique, 32),
    unit: str(r.libelle_unite, 24),
    qualityLimit: str(r.limite_qualite_parametre, 64),
    sampledAt: new Date(r.date_prelevement),
    networkName: str(r.reseaux?.[0]?.nom ?? r.nom_uge, 160),
    distributor: str(r.nom_distributeur, 160),
    physchemCompliance: str(r.conformite_limites_pc_prelevement, 1),
    bacterioCompliance: str(r.conformite_limites_bact_prelevement, 1),
    conclusion: str(r.conclusion_conformite_prelevement, 1000),
    ...stamp,
  };
}

@Injectable()
export class WaterService {
  constructor(
    private readonly collector: CollectorService,
    private readonly hubeau: HubeauClient,
    private readonly vigieau: VigieauClient,
    @InjectRepository(WaterQualityResultEntity) private readonly quality: Repository<WaterQualityResultEntity>,
    @InjectRepository(GroundwaterStationEntity) private readonly stations: Repository<GroundwaterStationEntity>,
    @InjectRepository(DroughtRestrictionEntity) private readonly droughts: Repository<DroughtRestrictionEntity>,
  ) {}

  async collect(address: AddressEntity, force = false): Promise<CollectOutcome[]> {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const insee = address.inseeCode;

    const quality = this.collector.run('hubeau_eau_potable', `commune:${insee}`, { force }, async (stamp) => {
      const since = new Date();
      since.setFullYear(since.getFullYear() - HISTORY_YEARS);
      const raw = await this.hubeau.drinkingWater(insee, since.toISOString().slice(0, 10));
      const rows = raw.filter((r) => r.code_prelevement && r.date_prelevement).map((r) => normalizeWater(r, stamp));
      for (const c of chunk(rows, 300)) await this.quality.upsert(c, ['sampleCode', 'parameterCode', 'inseeCode']);
      return { items: rows.length };
    });

    const groundwater = this.collector.run('hubeau_nappes', `address:${address.id}`, { force }, async (stamp) => {
      const raw = await this.hubeau.groundwaterStations(p, GROUNDWATER_RADIUS_M);
      // Dernière mesure pour les stations encore actives les plus proches.
      const active = raw
        .filter((s) => s.date_fin_mesure && new Date(s.date_fin_mesure) > new Date(Date.now() - 2 * 365 * 86400000))
        .slice(0, 5);
      const lastMeasures = new Map<string, any>();
      for (const s of active) lastMeasures.set(s.code_bss, await this.hubeau.lastGroundwaterMeasure(s.code_bss));

      const rows: Partial<GroundwaterStationEntity>[] = raw
        .filter((s) => s.x && s.y)
        .map((s) => {
          const m = lastMeasures.get(s.code_bss);
          return {
            codeBss: s.code_bss,
            bssId: str(s.bss_id, 16),
            inseeCode: str(s.code_commune_insee, 5),
            communeName: str(s.nom_commune, 120),
            altitudeM: num(s.altitude_station),
            depthM: num(s.profondeur_investigation),
            measuresCount: int(s.nb_mesures_piezo),
            firstMeasureDate: isoDate(s.date_debut_mesure),
            lastMeasureDate: isoDate(m?.date_mesure ?? s.date_fin_mesure),
            lastWaterDepthM: num(m?.profondeur_nappe),
            lastLevelNgfM: num(m?.niveau_nappe_eau),
            latitude: s.y,
            longitude: s.x,
            location: pointWkt(s.x, s.y),
            ...stamp,
          };
        });
      for (const c of chunk(rows, 200)) await this.stations.upsert(c, ['codeBss']);
      return { items: rows.length };
    });

    const drought = this.collector.run('vigieau', `address:${address.id}`, { force }, async (stamp) => {
      const rows: Partial<DroughtRestrictionEntity>[] = [];
      for (const zoneType of ['SUP', 'SOU', 'AEP'] as const) {
        for (const z of await this.vigieau.zones(p, insee, zoneType)) {
          rows.push({
            inseeCode: insee,
            zoneId: z.id,
            zoneCode: str(z.code, 32),
            zoneName: str(z.nom, 160),
            zoneType: z.type ?? zoneType,
            severity: z.niveauGravite ?? 'inconnu',
            decreeStart: isoDate(z.arrete?.dateDebutValidite),
            decreeEnd: isoDate(z.arrete?.dateFinValidite),
            decreeUrl: str(z.arrete?.cheminFichier, 500),
            usages: (z.usages ?? []).map((u: any) => ({ name: u.nom, theme: u.thematique, description: u.description })),
            ...stamp,
          });
        }
      }
      // Les restrictions levées disparaissent de l'API : on remplace l'état de la commune.
      await this.droughts.delete({ inseeCode: insee });
      if (rows.length) await this.droughts.upsert(rows, ['inseeCode', 'zoneId', 'zoneType']);
      return { items: rows.length };
    });

    return Promise.all([quality, groundwater, drought]);
  }

  async read(address: AddressEntity) {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const latest = await this.quality
      .createQueryBuilder('w')
      .where('w.insee_code = :insee', { insee: address.inseeCode })
      .andWhere(
        'w.sampled_at = (SELECT MAX(w2.sampled_at) FROM water_quality_result w2 WHERE w2.insee_code = w.insee_code AND w2.parameter_code = w.parameter_code)',
      )
      .getMany();

    const parameters = Object.entries(WATER_PARAMETERS).map(([code, key]) => {
      const r = latest.find((l) => l.parameterCode === code);
      const ref = REFERENCES[key];
      return {
        key,
        code,
        label: r?.parameterLabel ?? null,
        value: r?.resultNumeric ?? null,
        rawValue: r?.resultText ?? null,
        unit: r?.unit ?? ref?.unit ?? null,
        sampledAt: r?.sampledAt ?? null,
        exceedsLimit: r && ref?.limit !== undefined && r.resultNumeric !== null ? r.resultNumeric > ref.limit : null,
        reference: ref?.note ?? null,
      };
    });

    const lastSample = latest.sort((a, b) => +b.sampledAt - +a.sampledAt)[0];
    // Stations encore suivies (mesure de moins de 3 ans) d'abord, puis par distance.
    const recentLimit = new Date(Date.now() - 3 * 365 * 86400000).toISOString().slice(0, 10);
    const isActive = (s: GroundwaterStationEntity) => !!s.lastMeasureDate && s.lastMeasureDate >= recentLimit;
    const stations = (await entitiesWithDistance(withinRadius(this.stations.createQueryBuilder('g'), 'g', 'location', p, GROUNDWATER_RADIUS_M)))
      .map((s) => ({ ...s, active: isActive(s) }))
      .sort((a, b) => Number(b.active) - Number(a.active) || a.distanceM - b.distanceM);

    return {
      drinkingWater: {
        network: lastSample?.networkName ?? null,
        distributor: lastSample?.distributor ?? null,
        lastConclusion: lastSample?.conclusion ?? null,
        parameters,
      },
      drought: await this.droughts.find({ where: { inseeCode: address.inseeCode } }),
      groundwater: stations.slice(0, 5),
      sanitation: { covered: false, note: 'Raccordement à l’assainissement collectif : aucune source ouverte à l’adresse' },
    };
  }

  history(insee: string, parameterCode: string) {
    return this.quality.find({ where: { inseeCode: insee, parameterCode }, order: { sampledAt: 'ASC' } });
  }
}

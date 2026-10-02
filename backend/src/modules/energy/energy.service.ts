import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { DataFairClient, OdsClient } from '../../common/clients/open-data.clients';
import { LatLon } from '../../common/geo/geo.utils';
import { HttpClientService } from '../../common/http/http-client.service';
import { int, normalizeLabel, num, str } from '../../common/utils/parse';
import { CollectOutcome, CollectorService } from '../../sources/collector.service';
import { AddressEntity } from '../geo/geo.entities';
import { ElectricityConsumptionEntity, EnergyNetworkAccessEntity } from './energy.entities';

const ENEDIS_RESIDENTIAL_BY_ADDRESS = 'https://opendata.enedis.fr/data-fair/api/v1/datasets/msevy38s3ddly25n79bh8v-r';
const GRDF_BASE = 'https://opendata.grdf.fr/api/explore/v2.1';
const COMMUNE_KEY = '__COMMUNE__';

/** Abréviations de type de voie utilisées par Enedis (« 2 RUE DE LA REPUBLIQUE »). */
export function enedisAddressKey(housenumber: string | null, street: string | null): string | null {
  if (!housenumber || !street) return null;
  return normalizeLabel(`${housenumber} ${street}`);
}

@Injectable()
export class EnergyService {
  constructor(
    private readonly collector: CollectorService,
    private readonly http: HttpClientService,
    private readonly ods: OdsClient,
    private readonly dataFair: DataFairClient,
    @InjectRepository(EnergyNetworkAccessEntity) private readonly networks: Repository<EnergyNetworkAccessEntity>,
    @InjectRepository(ElectricityConsumptionEntity) private readonly consumption: Repository<ElectricityConsumptionEntity>,
  ) {}

  async collect(address: AddressEntity, force = false): Promise<CollectOutcome[]> {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const target = `address:${address.id}`;

    const heat = this.collector.run('fcu', target, { force }, async (stamp) => {
      const res: any = await this.http.get('https://france-chaleur-urbaine.beta.gouv.fr/api/v1/eligibility', {
        source: 'fcu',
        params: { lat: p.lat, lon: p.lon },
      });
      await this.networks.upsert(
        {
          addressId: address.id,
          networkType: 'heat',
          available: Boolean(res.isEligible),
          distanceM: int(res.distance),
          operatorName: str(res.gestionnaire, 160),
          networkName: str(res.name, 160),
          details: { networkId: res.id, renewableRate: res.rateENRR, co2Rate: res.rateCO2, futureNetwork: res.futurNetwork, priorityZone: res.inPDP },
          ...stamp,
        },
        ['addressId', 'networkType'],
      );
      return { items: 1, raw: res };
    });

    const gas = this.collector.run('grdf', target, { force }, async (stamp) => {
      const rows = await this.ods.records('grdf', GRDF_BASE, 'cartographie-du-reseau-grdf-en-service', {
        where: `code_insee_administratif="${address.inseeCode}"`,
        select: 'etat_serv,propane,code_insee_administratif',
      }, 5);
      const served = rows.some((r) => /service/i.test(r.etat_serv ?? ''));
      await this.networks.upsert(
        {
          addressId: address.id,
          networkType: 'gas',
          available: served,
          distanceM: null,
          operatorName: served ? 'GRDF' : null,
          networkName: null,
          details: { scope: 'commune', propane: rows[0]?.propane ?? null, note: 'Commune desservie par GRDF ; le raccordement du logement n’est pas publié' } as any,
          ...stamp,
        },
        ['addressId', 'networkType'],
      );
      return { items: rows.length };
    });

    const electricity = this.collector.run('enedis', target, { force }, async (stamp) => {
      const key = enedisAddressKey(address.housenumber, address.street);
      let rows = key
        ? await this.dataFair.lines('enedis', ENEDIS_RESIDENTIAL_BY_ADDRESS, { code_commune_eq: address.inseeCode, adresse_eq: key }, 50)
        : [];
      let addressKey = key ?? COMMUNE_KEY;
      if (rows.length === 0) {
        // Pas de ligne pour l'adresse (moins de 10 logements, secret statistique) : moyenne communale.
        rows = await this.dataFair.lines('enedis', ENEDIS_RESIDENTIAL_BY_ADDRESS, { code_commune_eq: address.inseeCode, sort: '-annee' }, 1);
        addressKey = COMMUNE_KEY;
      }
      const values = rows.map((r) => ({
        inseeCode: address.inseeCode,
        addressKey,
        year: int(r.annee)!,
        irisCode: addressKey === COMMUNE_KEY ? null : str(r.code_iris, 9),
        dwellings: addressKey === COMMUNE_KEY ? null : int(r.nombre_de_logements),
        totalMwh: addressKey === COMMUNE_KEY ? null : num(r.consommation_annuelle_totale_de_ladresse_mwh),
        avgPerSiteMwh: addressKey === COMMUNE_KEY ? null : num(r.consommation_annuelle_moyenne_par_site_de_ladresse_mwh),
        communeAvgMwh: num(r.consommation_annuelle_moyenne_de_la_commune_mwh),
        ...stamp,
      }));
      if (values.length) await this.consumption.upsert(values, ['inseeCode', 'addressKey', 'year']);
      return { items: values.length };
    });

    return Promise.all([heat, gas, electricity]);
  }

  async read(address: AddressEntity) {
    const key = enedisAddressKey(address.housenumber, address.street);
    const [networks, consumption] = await Promise.all([
      this.networks.find({ where: { addressId: address.id } }),
      this.consumption.find({
        where: [{ inseeCode: address.inseeCode, addressKey: key ?? COMMUNE_KEY }, { inseeCode: address.inseeCode, addressKey: COMMUNE_KEY }],
        order: { year: 'DESC' },
      }),
    ]);
    return {
      heatNetwork: networks.find((n) => n.networkType === 'heat') ?? null,
      gasNetwork: networks.find((n) => n.networkType === 'gas') ?? null,
      electricity: {
        atAddress: consumption.filter((c) => c.addressKey !== COMMUNE_KEY),
        communeAverage: consumption.filter((c) => c.addressKey === COMMUNE_KEY),
      },
      notCovered: ['Historique des coupures électriques à l’adresse'],
    };
  }
}

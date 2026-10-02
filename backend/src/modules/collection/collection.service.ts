import { BadRequestException, Injectable } from '@nestjs/common';
import { CollectOutcome } from '../../sources/collector.service';
import { BuildingService } from '../building/building.service';
import { ClimateService } from '../climate/climate.service';
import { ConnectivityService } from '../connectivity/connectivity.service';
import { EnergyService } from '../energy/energy.service';
import { AddressEntity } from '../geo/geo.entities';
import { GeoService } from '../geo/geo.service';
import { UrbanismService } from '../geo/urbanism.service';
import { MobilityService } from '../mobility/mobility.service';
import { NuisanceService } from '../nuisance/nuisance.service';
import { RiskService } from '../risk/risk.service';
import { ServicesService } from '../services/services.service';
import { SocioService } from '../socio/socio.service';
import { WaterService } from '../water/water.service';

export const MODULES = ['geo', 'building', 'risk', 'water', 'climate', 'nuisance', 'energy', 'services', 'socio', 'mobility', 'connectivity'] as const;
export type ModuleName = (typeof MODULES)[number];

export interface ModuleReport {
  module: ModuleName;
  durationMs: number;
  outcomes: CollectOutcome[];
  error?: string;
}

/**
 * Orchestration : lance la collecte de tous les modules pour une adresse.
 * Les modules tournent en parallèle (chaque source garde sa propre limite de débit) ;
 * l'échec d'un module n'interrompt pas les autres.
 */
@Injectable()
export class CollectionService {
  constructor(
    private readonly geo: GeoService,
    private readonly urbanism: UrbanismService,
    private readonly building: BuildingService,
    private readonly risk: RiskService,
    private readonly water: WaterService,
    private readonly climate: ClimateService,
    private readonly nuisance: NuisanceService,
    private readonly energy: EnergyService,
    private readonly services: ServicesService,
    private readonly socio: SocioService,
    private readonly mobility: MobilityService,
    private readonly connectivity: ConnectivityService,
  ) {}

  parseModules(raw?: string): ModuleName[] {
    if (!raw) return [...MODULES];
    const asked = raw.split(',').map((m) => m.trim()).filter(Boolean);
    const unknown = asked.filter((m) => !MODULES.includes(m as ModuleName));
    if (unknown.length) throw new BadRequestException(`Modules inconnus : ${unknown.join(', ')} (attendus : ${MODULES.join(', ')})`);
    return asked as ModuleName[];
  }

  private runner(name: ModuleName, address: AddressEntity, force: boolean): Promise<CollectOutcome[]> {
    switch (name) {
      case 'geo':
        return Promise.all([this.geo.collectParcel(address, force), this.geo.ensureCommune(address.inseeCode, force)]).then(async (o) => [
          ...o,
          ...(await this.urbanism.collect(address, force)),
        ]);
      case 'building':
        return this.building.collect(address, force);
      case 'risk':
        return this.risk.collect(address, force);
      case 'water':
        return this.water.collect(address, force);
      case 'climate':
        return this.climate.collect(address, force);
      case 'nuisance':
        return this.nuisance.collect(address, force);
      case 'energy':
        return this.energy.collect(address, force);
      case 'services':
        return this.services.collect(address, force);
      case 'socio':
        return this.socio.collect(address.inseeCode, force);
      case 'mobility':
        return this.mobility.collect(address, force);
      case 'connectivity':
        return this.connectivity.collect(address, force);
    }
  }

  async collectAll(addressId: number, modules: ModuleName[], force = false) {
    const started = Date.now();
    const address = await this.geo.getAddress(addressId);
    // Le module géo d'abord : la parcelle et le bâtiment servent de clés aux autres modules.
    const ordered = modules.includes('geo') ? (['geo', ...modules.filter((m) => m !== 'geo')] as ModuleName[]) : modules;
    const reports: ModuleReport[] = [];

    const run = async (name: ModuleName) => {
      const t0 = Date.now();
      try {
        reports.push({ module: name, durationMs: Date.now() - t0, outcomes: await this.runner(name, address, force) });
      } catch (err) {
        reports.push({ module: name, durationMs: Date.now() - t0, outcomes: [], error: err?.message ?? String(err) });
      }
      reports[reports.length - 1].durationMs = Date.now() - t0;
    };

    if (ordered[0] === 'geo') await run('geo');
    if (ordered.includes('building')) await run('building'); // renseigne address.rnbId
    await Promise.all(ordered.filter((m) => m !== 'geo' && m !== 'building').map(run));

    const all = reports.flatMap((r) => r.outcomes);
    return {
      addressId,
      durationMs: Date.now() - started,
      summary: {
        success: all.filter((o) => o.status === 'success').length,
        cached: all.filter((o) => o.status === 'cached').length,
        skipped: all.filter((o) => o.status === 'skipped').length,
        error: all.filter((o) => o.status === 'error').length,
      },
      modules: reports.sort((a, b) => MODULES.indexOf(a.module) - MODULES.indexOf(b.module)),
    };
  }

  /** Rapport consolidé : lecture seule, à partir de la base. */
  async report(addressId: number) {
    const details = await this.geo.getAddressDetails(addressId);
    const address = await this.geo.getAddress(addressId);
    const safe = async <T>(fn: () => Promise<T>) => {
      try {
        return await fn();
      } catch (err) {
        return { error: err?.message ?? String(err) } as unknown as T;
      }
    };
    const [urbanism, building, risks, water, climate, nuisances, energy, services, socio, mobility, connectivity] = await Promise.all([
      safe(() => this.urbanism.read(address)),
      safe(() => this.building.read(address)),
      safe(() => this.risk.read(address)),
      safe(() => this.water.read(address)),
      safe(() => this.climate.read(address)),
      safe(() => this.nuisance.read(address)),
      safe(() => this.energy.read(address)),
      safe(() => this.services.read(address)),
      safe(() => this.socio.read(address.inseeCode)),
      safe(() => this.mobility.read(address)),
      safe(() => this.connectivity.read(address)),
    ]);
    return {
      address: details,
      market: { priceIndex: await this.building.priceIndex(address.inseeCode) },
      urbanism,
      building,
      risks,
      water,
      climate,
      nuisances,
      energy,
      services,
      socio,
      mobility,
      connectivity,
      generatedAt: new Date(),
    };
  }
}

import { DvfMutationEntity } from './building.entities';
import { buildingPresumptions, computePriceIndex, normalizeDvfRow } from './building.normalizers';

const stamp = { sourceCode: 'dvf', fetchedAt: new Date(), expiresAt: new Date() };

function sale(mutationId: string, type: string, price: number, area: number, date = '2024-03-01'): DvfMutationEntity {
  return Object.assign(new DvfMutationEntity(), {
    mutationId, mutationDate: date, nature: 'Vente', propertyType: type, priceEur: price, builtAreaM2: area, inseeCode: '80021',
  });
}

describe('computePriceIndex', () => {
  it('ne garde que les ventes à un seul logement et écarte les valeurs aberrantes', () => {
    const rows = [
      sale('m1', 'Appartement', 200000, 100), // 2 000 €/m²
      sale('m2', 'Appartement', 300000, 100), // 3 000 €/m²
      sale('m3', 'Maison', 250000, 100),
      sale('m4', 'Appartement', 100000, 50), // vente de 2 logements : ignorée
      sale('m4', 'Appartement', 100000, 50),
      sale('m5', 'Appartement', 10, 100), // 0,1 €/m² : aberrant
      sale('m6', 'Dépendance', 5000, 10), // pas un logement
    ];
    const index = computePriceIndex(rows);
    const appart = index.find((i) => i.propertyType === 'Appartement')!;
    expect(appart.salesCount).toBe(2);
    expect(appart.medianPriceM2).toBe(2500);
    const all = index.find((i) => i.propertyType === 'Ensemble')!;
    expect(all.salesCount).toBe(3);
  });
});

describe('normalizeDvfRow', () => {
  it('produit un hachage stable et ignore les lignes incomplètes', () => {
    const row = { id_mutation: '2024-1', date_mutation: '2024-01-03', nature_mutation: 'Vente', valeur_fonciere: '88000', code_commune: '80021', type_local: 'Appartement', surface_reelle_bati: '57' };
    const a = normalizeDvfRow(row, stamp)!;
    const b = normalizeDvfRow({ ...row }, stamp)!;
    expect(a.rowHash).toHaveLength(40);
    expect(a.rowHash).toBe(b.rowHash);
    expect(a.priceEur).toBe(88000);
    expect(normalizeDvfRow({ ...row, id_mutation: '' }, stamp)).toBeNull();
  });
});

describe('buildingPresumptions', () => {
  const now = new Date('2026-10-02');
  it('applique les seuils plomb / amiante', () => {
    expect(buildingPresumptions(1930, null, now)).toMatchObject({ leadRisk: true, asbestosRisk: true });
    expect(buildingPresumptions(1980, null, now)).toMatchObject({ leadRisk: false, asbestosRisk: true });
    expect(buildingPresumptions(2005, null, now)).toMatchObject({ leadRisk: false, asbestosRisk: false });
    expect(buildingPresumptions(null, null, now).leadRisk).toBeNull();
  });

  it('suit le calendrier d’interdiction de location', () => {
    expect(buildingPresumptions(1970, 'G', now)).toMatchObject({ rentalBanned: true, rentalBanDate: '2025-01-01' });
    expect(buildingPresumptions(1970, 'F', now)).toMatchObject({ rentalBanned: false, rentalBanDate: '2028-01-01' });
    expect(buildingPresumptions(1970, 'C', now)).toMatchObject({ rentalBanned: false, rentalBanDate: null });
  });
});

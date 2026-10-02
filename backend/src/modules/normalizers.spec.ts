import { fixMojibake, normalizeMonument } from './geo/geo.normalizers';
import { normalizeReport } from './risk/risk.normalizers';
import { opensOnSunday } from './services/services.service';
import { housingIndicators } from './socio/socio.normalizers';

const stamp = { sourceCode: 'test', fetchedAt: new Date(), expiresAt: new Date() };

describe('normaliseurs', () => {
  it('répare les libellés GPU doublement encodés', () => {
    expect(fixMojibake('PÃ©rimÃ¨tre dÃ©limitÃ©')).toBe('Périmètre délimité');
    expect(fixMojibake('Déjà correct')).toBe('Déjà correct');
  });

  it('lit les coordonnées « lat,lon » des monuments historiques', () => {
    const m = normalizeMonument({ Reference: 'PA1', COG_Insee_lors_de_la_protection: '80021', coordonnees_au_format_WGS84: '49.89,2.30' }, stamp)!;
    expect(m).toMatchObject({ reference: 'PA1', latitude: 49.89, longitude: 2.3 });
    expect(normalizeMonument({}, stamp)).toBeNull();
  });

  it('aplatit le rapport Géorisques en une ligne par aléa', () => {
    const rows = normalizeReport(
      {
        risquesNaturels: { radon: { present: true, libelle: 'Radon', libelleStatutAdresse: 'Risque Existant - faible' } },
        risquesTechnologiques: { icpe: { present: false, libelle: 'ICPE' } },
      },
      7,
      stamp,
    );
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ addressId: 7, hazardCode: 'radon', category: 'natural', present: true });
    expect(rows[1]).toMatchObject({ hazardCode: 'icpe', category: 'technological', present: false });
  });

  it('détecte les horaires OSM ouverts le dimanche', () => {
    expect(opensOnSunday('Mo-Sa 07:00-19:30; Su 07:00-12:30')).toBe(true);
    expect(opensOnSunday('Mo-Sa 07:00-19:00; Su off')).toBe(false);
    expect(opensOnSunday('Tu-Sa 07:00-19:00')).toBe(false);
    expect(opensOnSunday(null)).toBeNull();
  });

  it('calcule les parts de résidences secondaires et de logements vacants', () => {
    const obs = (ocs: string, v: number) => ({ dimensions: { TIME_PERIOD: '2023', OCS: ocs }, measures: { OBS_VALUE_NIVEAU: { value: v } } });
    const rows = housingIndicators([obs('_T', 1000), obs('DW_SEC_DW_OCC', 50), obs('DW_VAC', 100)], [], '80021', stamp);
    const byKey = Object.fromEntries(rows.map((r) => [r.indicator, r.value]));
    expect(byKey.share_secondary_homes).toBe(5);
    expect(byKey.share_vacant_dwellings).toBe(10);
  });
});

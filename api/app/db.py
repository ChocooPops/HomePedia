"""
Accès MariaDB (SQLAlchemy Core asynchrone, sans classes d'entités).

Les lignes sont des dicts aux clés camelCase (« insee_code » <-> « inseeCode ») ; la conversion est déduite
du schéma lu dans information_schema au démarrage. Types gérés automatiquement :
  - DECIMAL -> nombre (int si la valeur est entière) ; TINYINT(1) -> bool ; DATE -> chaîne « AAAA-MM-JJ » ;
  - LONGTEXT avec CHECK JSON_VALID -> objet Python (sérialisé à l'écriture) ;
  - colonnes géométriques : écrites en WKT (SRID 4326), jamais renvoyées par défaut (option `geometry`).
Dans les fragments SQL libres (`where_sql`, `order`), la table porte l'alias « t » et les colonnes gardent
leur nom SQL ; un « : » littéral s'écrit « \\: ».
"""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .config import settings
from .geo_utils import bbox_around, bbox_polygon_wkt, point_wkt

SRID = 4326
GEOMETRY_TYPES = {
    "geometry", "point", "linestring", "polygon", "multipoint", "multilinestring", "multipolygon", "geometrycollection",
}


def snake_to_camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(p[:1].upper() + p[1:] for p in rest)


@dataclass
class TableMeta:
    name: str
    kinds: dict[str, str] = field(default_factory=dict)  # colonne -> geometry | json | bool | plain
    columns: dict[str, str] = field(default_factory=dict)  # propriété camelCase -> colonne
    props: dict[str, str] = field(default_factory=dict)  # colonne -> propriété camelCase
    primary: set[str] = field(default_factory=set)

    def column(self, prop: str) -> str:
        if prop in self.columns:
            return self.columns[prop]
        if prop in self.kinds:
            return prop
        raise KeyError(f"Colonne inconnue : {self.name}.{prop}")


class Database:
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.tables: dict[str, TableMeta] = {}

    # ------------------------------------------------------------ Cycle de vie

    async def connect(self):
        self.engine = create_async_engine(
            settings.db_url, pool_size=10, max_overflow=5, pool_pre_ping=True, pool_recycle=1800, echo=settings.db_logging,
        )

    async def close(self):
        if self.engine:
            await self.engine.dispose()

    async def load_schema(self):
        """Lit la structure des tables : sert à la conversion des noms et des types."""
        columns = await self.query(
            "SELECT TABLE_NAME AS t, COLUMN_NAME AS c, DATA_TYPE AS d, COLUMN_TYPE AS ct, COLUMN_KEY AS k "
            "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME, ORDINAL_POSITION"
        )
        checks = await self.query(
            "SELECT TABLE_NAME AS t, CHECK_CLAUSE AS clause FROM information_schema.CHECK_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE()"
        )
        json_columns = {
            (c["t"], m)
            for c in checks
            for m in re.findall(r"json_valid\(`?(\w+)`?\)", c["clause"], flags=re.IGNORECASE)
        }
        tables: dict[str, TableMeta] = {}
        for c in columns:
            meta = tables.setdefault(c["t"], TableMeta(c["t"]))
            if c["d"].lower() in GEOMETRY_TYPES:
                kind = "geometry"
            elif (c["t"], c["c"]) in json_columns:
                kind = "json"
            elif c["ct"].lower().startswith("tinyint(1)"):
                kind = "bool"
            else:
                kind = "plain"
            meta.kinds[c["c"]] = kind
            meta.columns[snake_to_camel(c["c"])] = c["c"]
            meta.props[c["c"]] = snake_to_camel(c["c"])
            if c["k"] == "PRI":
                meta.primary.add(c["c"])
        self.tables = tables

    def meta(self, table: str) -> TableMeta:
        try:
            return self.tables[table]
        except KeyError:
            raise KeyError(f"Table inconnue : {table}") from None

    # ------------------------------------------------------------ SQL brut

    async def query(self, sql: str, params: dict | None = None) -> list[dict]:
        """SELECT libre : lignes aux noms de colonnes SQL (DECIMAL convertis en float)."""
        async with self.engine.connect() as conn:
            result = await conn.execute(text(sql), params or {})
            return [{k: _plain(v) for k, v in row.items()} for row in result.mappings().all()]

    async def execute(self, sql: str, params: dict | None = None) -> int:
        """INSERT / UPDATE / DELETE libre : nombre de lignes affectées."""
        async with self.engine.begin() as conn:
            return (await conn.execute(text(sql), params or {})).rowcount

    # ------------------------------------------------------------ Lecture

    def decode(self, table: str, row: dict) -> dict:
        """Ligne SQL (colonnes snake_case) -> dict camelCase, types convertis, géométries retirées."""
        meta = self.meta(table)
        out = {}
        for col, value in row.items():
            kind = meta.kinds.get(col)
            if kind == "geometry":
                continue
            if kind is None:
                out[col] = _plain(value)
            elif value is None:
                out[meta.props[col]] = None
            elif kind == "json":
                out[meta.props[col]] = _json_loads(value)
            elif kind == "bool":
                out[meta.props[col]] = bool(value)
            else:
                out[meta.props[col]] = _plain(value)
        return out

    def _select(self, meta: TableMeta, geometry: str | None) -> str:
        cols = [f"t.`{c}`" for c, kind in meta.kinds.items() if kind != "geometry"]
        if geometry:
            cols.append(f"ST_AsGeoJSON(t.`{meta.column(geometry)}`) AS __geojson")
        return ", ".join(cols)

    def _where(self, meta: TableMeta, where: dict | None, where_sql: str | None, params: dict) -> str:
        clauses = []
        for i, (prop, value) in enumerate((where or {}).items()):
            col = f"t.`{meta.column(prop)}`"
            if value is None:
                clauses.append(f"{col} IS NULL")
            elif isinstance(value, (list, tuple, set)):
                names = []
                for j, v in enumerate(value):
                    params[f"w{i}_{j}"] = _bind(v)
                    names.append(f":w{i}_{j}")
                clauses.append(f"{col} IN ({', '.join(names)})" if names else "1 = 0")
            else:
                params[f"w{i}"] = _bind(value)
                clauses.append(f"{col} = :w{i}")
        if where_sql:
            clauses.append(f"({where_sql})")
        return " WHERE " + " AND ".join(clauses) if clauses else ""

    def _rows(self, table: str, rows: list[dict]) -> list[dict]:
        out = []
        for row in rows:
            geojson = row.pop("__geojson", None)
            distance = row.pop("__distance_m", None)
            item = self.decode(table, row)
            if geojson is not None:
                item["geometry"] = _json_loads(geojson)
            if distance is not None:
                item["distanceM"] = int(distance)
            out.append(item)
        return out

    async def find(
        self,
        table: str,
        where: dict | None = None,
        *,
        where_sql: str | None = None,
        params: dict | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        geometry: str | None = None,
    ) -> list[dict]:
        """
        Lignes d'une table. `where` : égalités sur des propriétés camelCase (None -> IS NULL, liste -> IN).
        `geometry` : nom d'une colonne géométrique à renvoyer en GeoJSON sous la clé « geometry ».
        """
        meta = self.meta(table)
        p = dict(params or {})
        sql = f"SELECT {self._select(meta, geometry)} FROM `{table}` t" + self._where(meta, where, where_sql, p)
        if order:
            sql += f" ORDER BY {order}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
            if offset:
                sql += f" OFFSET {int(offset)}"
        return self._rows(table, await self.query(sql, p))

    async def find_one(self, table: str, where: dict | None = None, **kwargs) -> dict | None:
        rows = await self.find(table, where, limit=1, **kwargs)
        return rows[0] if rows else None

    async def count(self, table: str, where: dict | None = None, *, where_sql: str | None = None, params: dict | None = None) -> int:
        p = dict(params or {})
        rows = await self.query(f"SELECT COUNT(*) AS n FROM `{table}` t" + self._where(self.meta(table), where, where_sql, p), p)
        return int(rows[0]["n"])

    async def exists(self, table: str, where: dict) -> bool:
        return await self.find_one(table, where) is not None

    async def geometry(self, table: str, where: dict, column: str = "geom") -> dict | None:
        row = await self.find_one(table, where, geometry=column)
        return row["geometry"] if row else None

    async def within_radius(
        self,
        table: str,
        column: str,
        center: dict,
        radius_m: float,
        where: dict | None = None,
        *,
        where_sql: str | None = None,
        params: dict | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Points dans un rayon, du plus proche au plus lointain, avec leur distance (« distanceM », en mètres) :
        MBRContains sur une boîte englobante (index spatial) puis ST_Distance_Sphere pour la distance exacte.
        """
        meta = self.meta(table)
        col = f"t.`{meta.column(column)}`"
        center_expr = f"ST_GeomFromText(:__center, {SRID})"
        p = dict(params or {})
        base = self._where(meta, where, where_sql, p)
        p |= {
            "__center": point_wkt(center["lon"], center["lat"]),
            "__bbox": bbox_polygon_wkt(bbox_around(center, radius_m)),
            "__radius": radius_m,
        }
        spatial = (
            f"MBRContains(ST_GeomFromText(:__bbox, {SRID}), {col}) AND ST_Distance_Sphere({col}, {center_expr}) <= :__radius"
        )
        sql = (
            f"SELECT {self._select(meta, None)}, ROUND(ST_Distance_Sphere({col}, {center_expr})) AS __distance_m "
            f"FROM `{table}` t" + (f"{base} AND {spatial}" if base else f" WHERE {spatial}") + " ORDER BY __distance_m ASC"
        )
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        return self._rows(table, await self.query(sql, p))

    async def intersects_area(
        self,
        table: str,
        column: str,
        center: dict,
        radius_m: float,
        where: dict | None = None,
        *,
        where_sql: str | None = None,
        params: dict | None = None,
    ) -> list[dict]:
        """
        Géométries (lignes, polygones) dont l'emprise intersecte la zone, renvoyées avec leur GeoJSON
        sous « geometry » : la distance exacte se calcule ensuite avec geo_utils.
        """
        meta = self.meta(table)
        p = dict(params or {})
        base = self._where(meta, where, where_sql, p)
        p["__area"] = bbox_polygon_wkt(bbox_around(center, radius_m))
        spatial = f"MBRIntersects(ST_GeomFromText(:__area, {SRID}), t.`{meta.column(column)}`)"
        sql = f"SELECT {self._select(meta, column)} FROM `{table}` t" + (f"{base} AND {spatial}" if base else f" WHERE {spatial}")
        return self._rows(table, await self.query(sql, p))

    # ------------------------------------------------------------ Écriture

    def _values(self, meta: TableMeta, row: dict, params: dict, prefix: str) -> dict[str, str]:
        """Colonne -> expression SQL de la valeur ; remplit `params`."""
        exprs = {}
        for i, (prop, value) in enumerate(row.items()):
            col = meta.column(prop)
            kind = meta.kinds[col]
            name = f"{prefix}{i}"
            if kind == "json" and value is not None:
                value = json.dumps(value, ensure_ascii=False, default=str)
            params[name] = _bind(value)
            exprs[col] = f"ST_GeomFromText(:{name}, {SRID})" if kind == "geometry" else f":{name}"
        return exprs

    async def insert(self, table: str, row: dict) -> int:
        """Insère une ligne et renvoie son identifiant auto-incrémenté."""
        params: dict = {}
        exprs = self._values(self.meta(table), row, params, "v")
        sql = f"INSERT INTO `{table}` ({', '.join(f'`{c}`' for c in exprs)}) VALUES ({', '.join(exprs.values())})"
        async with self.engine.begin() as conn:
            return (await conn.execute(text(sql), params)).lastrowid

    async def upsert(self, table: str, rows: dict | list[dict]) -> None:
        """
        INSERT ... ON DUPLICATE KEY UPDATE : la clé primaire ou n'importe quelle clé unique sert de clé de conflit.
        Toutes les lignes d'un appel doivent porter les mêmes propriétés.
        """
        rows = [rows] if isinstance(rows, dict) else rows
        if not rows:
            return
        meta = self.meta(table)
        params: dict = {}
        tuples = []
        cols: list[str] = []
        for n, row in enumerate(rows):
            exprs = self._values(meta, row, params, f"r{n}_")
            if n == 0:
                cols = list(exprs)
            elif list(exprs) != cols:
                raise ValueError(f"upsert {table} : les lignes n'ont pas toutes les mêmes colonnes")
            tuples.append(f"({', '.join(exprs.values())})")
        updates = [f"`{c}` = VALUES(`{c}`)" for c in cols if c not in meta.primary] or [f"`{cols[0]}` = `{cols[0]}`"]
        sql = (
            f"INSERT INTO `{table}` ({', '.join(f'`{c}`' for c in cols)}) VALUES {', '.join(tuples)} "
            f"ON DUPLICATE KEY UPDATE {', '.join(updates)}"
        )
        await self.execute(sql, params)

    async def update(self, table: str, where: dict, values: dict) -> int:
        meta = self.meta(table)
        params: dict = {}
        exprs = self._values(meta, values, params, "v")
        sets = ", ".join(f"t.`{c}` = {e}" for c, e in exprs.items())
        return await self.execute(f"UPDATE `{table}` t SET {sets}" + self._where(meta, where, None, params), params)

    async def delete(self, table: str, where: dict | None = None, *, where_sql: str | None = None, params: dict | None = None) -> int:
        if not where and not where_sql:
            raise ValueError("delete sans condition")
        p = dict(params or {})
        # « DELETE t FROM table t » : seule forme qui accepte un alias.
        return await self.execute(f"DELETE t FROM `{table}` t" + self._where(self.meta(table), where, where_sql, p), p)


def _plain(value):
    if isinstance(value, Decimal):
        # Une valeur entière sort sans décimale (31 et non 31.0), comme un nombre JSON.
        return int(value) if value == value.to_integral_value() else float(value)
    # Colonnes DATE : chaîne « AAAA-MM-JJ », comme à l'écriture.
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    return value


def _bind(value):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, datetime) and value.tzinfo:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _json_loads(value):
    if not isinstance(value, (str, bytes)):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return value


db = Database()

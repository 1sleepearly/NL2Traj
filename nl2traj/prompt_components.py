"""Neutral components that do not encode a method's reasoning policy."""

from functools import lru_cache
from pathlib import Path


SHARED_TIME_CONVENTIONS = """/* Shared benchmark time conventions:
- All clock-time ranges use a left-closed, right-open interval [start, end).
- 早高峰 (morning peak) is 07:00-09:00 local time.
- 晚高峰 (evening peak) is 17:00-19:00 local time.
- Benchmark timestamps use UTC+08:00 unless the question explicitly specifies
  another offset.
These definitions are shared by every evaluated method and do not prescribe
whether a question filters departure, arrival, or movement during the period.
*/
"""


DDL_ONLY = """
/* Table Schemas:
CREATE TABLE trips (
    trip_id BIGSERIAL PRIMARY KEY,
    trip_date DATE NOT NULL,
    label BIGINT,
    trip_trajectory TGEOMPOINT NOT NULL
);

CREATE TABLE districts (
    name TEXT,
    adcode INTEGER,
    geometry GEOMETRY(MultiPolygon, 4326)
);
*/
"""

SPATIAL_SCHEMA_NOTES = """
/* Spatial schema notes:
- districts.geometry is a WGS84 (SRID 4326) administrative-area MultiPolygon.
- Spatial predicates operate on geometry values. Metric distance/length calculations
  may cast derived geometry values to geography.
*/
"""

GEOGRAPHIC_DESCRIPTIONS = """
/* Geographic descriptions:
- trips records taxi trajectories collected in Hangzhou for the benchmark dates.
- districts records Hangzhou administrative districts and their boundaries.
*/
"""

# Shared callable PostGIS facts used by the experimental NL2Traj prompt.
POSTGIS_RAWDOCS = """/* PostGIS callable reference:
- ST_Distance(geography, geography) returns distance in meters.
- ST_DWithin(geography, geography, meters) tests a metric distance threshold.
- ST_Length(geography) returns length in meters.
- ST_Area(geography) returns area in square meters.
- ST_Centroid(geometry) returns a centroid geometry.
- ST_Intersects(geometry, geometry) returns boolean.
- ST_Touches(geometry, geometry) returns boolean.
- ST_Covers(geometry, geometry) returns boolean.
- ST_Within(geometry, geometry) returns boolean.
- ST_Intersection(geometry, geometry) returns geometry.
- ST_Point(longitude, latitude) constructs a point; ST_SetSRID(geometry, 4326)
  assigns WGS84 coordinates.
- Cast geometry to geography for metric distance, length, or radius values.
*/
"""

TRAJECTORY_KNOWLEDGE_PATH = Path(__file__).resolve().parent / "knowledge" / "trajectory_domain_knowledge.md"


@lru_cache(maxsize=1)
def load_trajectory_knowledge() -> str:
    """Load the trajectory-query knowledge used by NL2Traj."""
    return TRAJECTORY_KNOWLEDGE_PATH.read_text(encoding="utf-8")


def examples_block(examples: str) -> str:
    if not examples:
        return ""
    return f"/* Similar natural-language/SQL examples */\n{examples}\n\n"


def sql_output_contract(question: str) -> str:
    return f"""请生成一条可直接执行的 PostgreSQL SQL 查询。
数据库已安装 PostGIS 和 MobilityDB。
只能使用给定的表、字段和可用函数，不要虚构字段。
查询可以用 SELECT 或 WITH 开头。
只输出 SQL，不要解释。
问题：{question}"""

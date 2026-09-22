from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Boolean, JSON, Index
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.db.base_class import Base
from datetime import datetime
import uuid

class GovernmentInfrastructureFeature(Base):
    __tablename__ = "government_infrastructure_features"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    infrastructure_type = Column(String, index=True, nullable=False) # 'buildings', 'roads', 'facilities'
    source = Column(String, nullable=False) # 'OSM', 'Bhuvan', etc.
    properties = Column(JSON, nullable=False, default=dict)
    
    # Can be POINT, LINESTRING, POLYGON, we use GEOMETRY to allow multiple types
    geometry = Column(Geometry("GEOMETRY", srid=4326), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_gov_infra_geom", "geometry", postgresql_using="gist"),
    )


class GovernmentDataset(Base):
    __tablename__ = "government_datasets"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    original_path = Column(String, nullable=False, unique=True, index=True)
    source_filename = Column(String, nullable=False)
    format = Column(String, nullable=False) # e.g., ZIP, SHP, GEOJSON
    classification = Column(String, index=True) # DAM, RESERVOIR, RIVER, UNKNOWN, REVIEW_REQUIRED
    source_agency = Column(String, nullable=True)
    crs = Column(String, nullable=True)
    geometry_type = Column(String, nullable=True)
    feature_count = Column(Integer, default=0)
    bounding_box = Column(JSON, nullable=True) # [xmin, ymin, xmax, ymax]
    attribute_names = Column(JSON, nullable=True)
    file_size = Column(Integer, nullable=True)
    archive_status = Column(String, nullable=True) # EXTRACTED, PENDING
    validation_status = Column(String, nullable=True) # VALID, INVALID
    ingestion_status = Column(String, nullable=True) # INGESTED, PENDING, ERROR
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GovernmentDam(Base):
    __tablename__ = "government_dams"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String, ForeignKey("government_datasets.id", ondelete="CASCADE"), index=True)
    
    # Normalized fields
    dam_name = Column(String, index=True)
    source_id = Column(String, index=True)
    nrld_id = Column(String, index=True)
    state = Column(String, index=True)
    district = Column(String, index=True)
    river_code = Column(String, index=True)
    basin_code = Column(String, index=True)
    dam_type = Column(String)
    construction_year = Column(Integer)
    
    # Raw source data preservation
    source_data = Column(JSON, nullable=False, default=dict)
    
    # Geometry (Points generally for dams) - preserve source CRS if possible, but 
    # for simplicity in a unified table, we often store them as EPSG:4326 or standard metric.
    # We will use EPSG:4326 for unified storage of point data for the dashboard, 
    # and keep original CRS in GovernmentDataset metadata.
    geometry = Column(Geometry("POINT", srid=4326), nullable=True)
    
    # Readiness
    spatial_data_readiness = Column(String, default="REVIEW_REQUIRED", index=True) # AVAILABLE, MISSING, REVIEW_REQUIRED
    
    dataset = relationship("GovernmentDataset")
    
    # Add spatial index
    __table_args__ = (
        Index("idx_gov_dams_geom", "geometry", postgresql_using="gist"),
    )

class GovernmentReservoir(Base):
    __tablename__ = "government_reservoirs"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String, ForeignKey("government_datasets.id", ondelete="CASCADE"), index=True)
    
    source_id = Column(String, index=True)
    name = Column(String, index=True)
    source_data = Column(JSON, nullable=False, default=dict)
    
    geometry = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    
    dataset = relationship("GovernmentDataset")
    __table_args__ = (
        Index("idx_gov_reservoirs_geom", "geometry", postgresql_using="gist"),
    )

class GovernmentRiver(Base):
    __tablename__ = "government_rivers"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String, ForeignKey("government_datasets.id", ondelete="CASCADE"), index=True)
    
    source_id = Column(String, index=True)
    name = Column(String, index=True)
    river_code = Column(String, index=True)
    source_data = Column(JSON, nullable=False, default=dict)
    
    geometry = Column(Geometry("MULTILINESTRING", srid=4326), nullable=True)
    
    dataset = relationship("GovernmentDataset")
    __table_args__ = (
        Index("idx_gov_rivers_geom", "geometry", postgresql_using="gist"),
    )

class GovernmentRiverPolygon(Base):
    __tablename__ = "government_river_polygons"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String, ForeignKey("government_datasets.id", ondelete="CASCADE"), index=True)
    
    source_id = Column(String, index=True)
    name = Column(String, index=True)
    source_data = Column(JSON, nullable=False, default=dict)
    
    geometry = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    
    dataset = relationship("GovernmentDataset")
    __table_args__ = (
        Index("idx_gov_river_polygons_geom", "geometry", postgresql_using="gist"),
    )

class DamRelationship(Base):
    __tablename__ = "dam_relationships"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    
    dam_id = Column(String, ForeignKey("government_dams.id", ondelete="CASCADE"), index=True)
    target_type = Column(String, nullable=False) # RESERVOIR, RIVER
    target_id = Column(String, nullable=False, index=True) # ID from government_reservoirs or government_rivers
    
    match_method = Column(String, nullable=False) # SPATIAL_INTERSECT, SPATIAL_DWITHIN, ATTRIBUTE_MATCH
    match_distance = Column(Float, nullable=True) # distance in meters if spatial
    match_confidence = Column(Float, nullable=False) # 0.0 to 1.0
    match_status = Column(String, nullable=False, index=True) # DIRECT, HIGH_CONFIDENCE, REVIEW_REQUIRED, UNMATCHED
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    dam = relationship("GovernmentDam")

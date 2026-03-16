# backend/db/models/schemas.py
from sqlalchemy import Column, Integer, String, Numeric, Boolean, TIMESTAMP, ForeignKey, Text, ARRAY, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from db.database import Base
import datetime

class Country(Base):
    __tablename__ = "countries"

    country_code = Column(String(3), primary_key=True)
    country_name = Column(String(100), nullable=False)
    continent = Column(String(50))
    region = Column(String(50))
    economy_type = Column(String(20))          # 'developed' | 'emerging'
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    indicator_data = relationship("IndicatorData", back_populates="country", cascade="all, delete-orphan")
    predictions = relationship("ModelPrediction", back_populates="country", cascade="all, delete-orphan")

class Indicator(Base):
    __tablename__ = "indicators"

    indicator_id = Column(Integer, primary_key=True, autoincrement=True)
    indicator_code = Column(String(50), unique=True, nullable=False)
    indicator_name = Column(String(200), nullable=False)
    simplified_name = Column(String(100))
    unit = Column(String(50))
    category = Column(String(50))
    source = Column(String(100), default="World Bank")
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    indicator_data = relationship("IndicatorData", back_populates="indicator", cascade="all, delete-orphan")
    feature_importance = relationship("FeatureImportance", back_populates="indicator", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_indicators_code', 'indicator_code'),
        Index('idx_indicators_category', 'category'),
    )

class IndicatorData(Base):
    __tablename__ = "indicator_data"

    country_code = Column(String(3), ForeignKey("countries.country_code", ondelete="CASCADE"), primary_key=True)
    indicator_id = Column(Integer, ForeignKey("indicators.indicator_id", ondelete="CASCADE"), primary_key=True)
    year = Column(Integer, primary_key=True)
    value = Column(Numeric(15, 4))
    is_extrapolated = Column(Boolean, default=False)   # True = backfilled, forward-filled, or interpolated
    data_quality = Column(String(20), default="good")
    data_source = Column(String(50), default="World Bank API")
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    country = relationship("Country", back_populates="indicator_data")
    indicator = relationship("Indicator", back_populates="indicator_data")

    __table_args__ = (
        Index('idx_data_country_year', 'country_code', 'year'),
        Index('idx_data_indicator_year', 'indicator_id', 'year'),
        Index('idx_data_extrapolated', 'is_extrapolated'),
    )

class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    country_code = Column(String(3), ForeignKey("countries.country_code", ondelete="CASCADE"), nullable=False)
    year = Column(Integer, nullable=False)
    model_version = Column(String(50))

    # Forecast values
    predicted_gdp_per_capita = Column(Numeric(15, 2))
    ci_80_lower = Column(Numeric(15, 2))
    ci_80_upper = Column(Numeric(15, 2))

    # Baseline anchor — True only for the row representing the last actual year (e.g. 2024)
    # predicted_gdp_per_capita holds the real observed value on this row,
    # giving every downstream calculation a clean anchor point
    is_baseline = Column(Boolean, default=False)

    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    country = relationship("Country", back_populates="predictions")

    __table_args__ = (
        UniqueConstraint('country_code', 'year', 'model_version', name='uq_prediction'),
        Index('idx_predictions_country_year',  'country_code', 'year'),
        Index('idx_predictions_model_version', 'model_version'),
        Index('idx_predictions_is_baseline',   'is_baseline'),
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"

    version_id = Column(Integer, primary_key=True, autoincrement=True)
    version_name = Column(String(50), unique=True, nullable=False)
    model_type = Column(String(50))
    description = Column(Text)
    hyperparameters = Column(JSONB)
    feature_list = Column(ARRAY(String))

    training_start_year = Column(Integer)
    training_end_year = Column(Integer)
    holdout_start_year = Column(Integer)
    holdout_end_year = Column(Integer)

    cv_r2 = Column(Numeric(5, 4))
    cv_rmse = Column(Numeric(10, 4))
    holdout_r2 = Column(Numeric(5, 4))
    holdout_rmse = Column(Numeric(10, 4))
    holdout_mape = Column(Numeric(5, 4))

    is_active = Column(Boolean, default=True)
    trained_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    deployed_at = Column(TIMESTAMP)

    feature_importance = relationship("FeatureImportance", back_populates="model_version", cascade="all, delete-orphan")

class FeatureImportance(Base):
    __tablename__ = "feature_importance"

    importance_id = Column(Integer, primary_key=True, autoincrement=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.version_id", ondelete="CASCADE"), nullable=False)
    indicator_id = Column(Integer, ForeignKey("indicators.indicator_id", ondelete="CASCADE"), nullable=False)
    
    importance_score = Column(Numeric(6, 4))
    rank = Column(Integer)
    catboost_importance = Column(Numeric(6, 4))
    xgboost_importance = Column(Numeric(6, 4))
    ensemble_importance = Column(Numeric(6, 4))

    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    model_version = relationship("ModelVersion", back_populates="feature_importance")
    indicator = relationship("Indicator", back_populates="feature_importance")

    __table_args__ = (
        UniqueConstraint('model_version_id', 'indicator_id', name='uq_feature_importance'),
        Index('idx_importance_version', 'model_version_id'),
        Index('idx_importance_rank', 'rank'),
    )
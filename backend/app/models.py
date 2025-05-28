from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=False)  # Consider hashing/encrypting
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    api_specifications = relationship("APISpecification", back_populates="owner")
    har_uploads = relationship("HARUpload", back_populates="uploader")
    validation_runs = relationship("ValidationRun", back_populates="trigger_user")
    environments = relationship("Environment", back_populates="owner")


class APISpecification(Base):
    __tablename__ = "api_specifications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    version_string = Column(String, nullable=False)
    openapi_content = Column(JSON, nullable=False)  # Consider using JSONB for PostgreSQL
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="api_specifications")
    mock_configurations = relationship("MockConfiguration", back_populates="api_specification")
    validation_runs = relationship("ValidationRun", back_populates="api_specification")


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "Production", "Staging", "Local Dev"
    base_url = Column(String, nullable=False)  # e.g., "https://api.example.com"
    description = Column(String)  # Optional description
    environment_type = Column(
        String, default="custom"
    )  # "production", "staging", "development", "custom"
    is_active = Column(String, default="true")  # For soft deletion
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="environments")
    validation_runs = relationship("ValidationRun", back_populates="environment")


class HARUpload(Base):
    __tablename__ = "har_uploads"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    raw_content = Column(String, nullable=False)  # Consider using TEXT type
    processed_artifacts_references = Column(JSON)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    uploader = relationship("User", back_populates="har_uploads")


class MockConfiguration(Base):
    __tablename__ = "mock_configurations"

    id = Column(Integer, primary_key=True, index=True)
    api_specification_id = Column(Integer, ForeignKey("api_specifications.id"), nullable=False)
    wiremock_mapping_json = Column(JSON, nullable=False)  # Consider JSONB for PostgreSQL
    deployed_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String)  # e.g., 'active', 'inactive', 'error'

    api_specification = relationship("APISpecification", back_populates="mock_configurations")


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True, index=True)
    api_specification_id = Column(Integer, ForeignKey("api_specifications.id"), nullable=False)
    # Keep provider_url for backward compatibility and custom URLs
    provider_url = Column(String, nullable=False)
    # Add environment reference for predefined environments
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=True)
    auth_method = Column(String, default="none")  # Authentication method
    auth_config = Column(JSON)  # Authentication configuration
    test_strategies = Column(JSON)  # Test strategies to use
    max_examples = Column(Integer, default=100)  # Max test examples
    timeout = Column(Integer, default=300)  # Timeout in seconds
    schemathesis_results = Column(JSON)  # Consider JSONB for PostgreSQL
    status = Column(String, default="pending")  # e.g., 'pending', 'running', 'completed', 'failed'
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    api_specification = relationship("APISpecification", back_populates="validation_runs")
    trigger_user = relationship("User", back_populates="validation_runs")
    environment = relationship("Environment", back_populates="validation_runs")


# Ensure all models are imported here so Alembic can find them.
# This can also be managed in app.db.base, by importing all model modules
# there.

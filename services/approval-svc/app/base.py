# AIVO Approval Service - Database Base
# Shared declarative base to avoid circular imports

from sqlalchemy.orm import declarative_base

Base = declarative_base()

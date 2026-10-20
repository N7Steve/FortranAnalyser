"""Fortran analysis independent of any web framework."""

from .engine import analyse_source
from .project import analyse_project

__all__ = ["analyse_project", "analyse_source"]

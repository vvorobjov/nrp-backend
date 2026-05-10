"""Version string for hbp_nrp_simserver.

Re-exports from :mod:`hbp_nrp_commons.version`, which holds the single
canonical resolver (env override → SCM script → fallback). EBR2-70
consolidated three byte-identical copies — keep that single source
of truth here.
"""
from hbp_nrp_commons.version import VERSION  # noqa: F401

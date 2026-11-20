"""Duplicate detection (entity resolution) in an Acadian genealogy database.

RQ1: do R-GCN family-neighbourhood embeddings rank the true duplicate higher
than attribute-only methods?  RQ2: does a 2-hop neighbourhood help an LLM
verify a candidate pair?

General-purpose code lives in `genealogie_acadienne` (the library);
`acadian_er.lib_staging` is the (currently empty) staging area for new
library-bound code. Everything else here is project-specific.
"""

__version__ = "0.1.0"

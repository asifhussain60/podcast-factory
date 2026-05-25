"""Source-extractor: SQL database → podcast-pipeline source bundle.

Independent of scripts/podcast/. Adapters provide database-specific schema
knowledge; stages run against any adapter. Output is a self-contained bundle
that the podcast pipeline can intake via a forthcoming --from-bundle flag.

Currently implemented: KAHSKOLE adapter (Urdu).
Scaffolded but not implemented: KSESSIONS adapter (English).
"""

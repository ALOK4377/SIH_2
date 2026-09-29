"""Samanvay ML / entity-resolution package.

Pipeline stages (each in its own module):
    normalize -> embed -> block -> score -> cluster -> canonical
with `explain` producing per-match, human-readable justifications.

Every stage is dependency-light: heavy libraries (sentence-transformers,
RapidFuzz, pgvector) are optional and, when absent, a pure-stdlib fallback
keeps the whole pipeline runnable offline.
"""

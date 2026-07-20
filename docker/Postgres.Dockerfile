FROM pgvector/pgvector:pg17 AS pgvector

FROM postgres:17

COPY --from=pgvector /usr/lib/postgresql/17/lib/vector.so /usr/lib/postgresql/17/lib/vector.so
COPY --from=pgvector /usr/lib/postgresql/17/lib/bitcode/vector /usr/lib/postgresql/17/lib/bitcode/vector
COPY --from=pgvector /usr/lib/postgresql/17/lib/bitcode/vector.index.bc /usr/lib/postgresql/17/lib/bitcode/vector.index.bc
COPY --from=pgvector /usr/share/postgresql/17/extension/vector* /usr/share/postgresql/17/extension/

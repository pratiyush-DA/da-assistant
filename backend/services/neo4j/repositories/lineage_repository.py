class LineageRepository:
    """Phase 2 — SQL lineage graph operations."""

    def ingest_sql_files(self, *args, **kwargs):
        raise NotImplementedError("Phase 2 — SQL Lineage Explorer")

    def get_table_lineage(self, table_name: str):
        raise NotImplementedError("Phase 2 — SQL Lineage Explorer")

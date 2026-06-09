"""
Database facade — single entry point for raw SQL operations.
"""
from core.database.connection import (
    close_all_pools,
    get_connection,
    get_connection_pool,
    health_check,
)
from core.database.crud_queries import (
    delete_query,
    insert_query,
    insert_query_returning,
    select_one,
    select_query,
    update_query,
)
from core.database.raw_queries import execute, execute_values_insert
from core.database.transaction import atomic, savepoint

__all__ = [
    "atomic",
    "savepoint",
    "execute",
    "execute_values_insert",
    "select_query",
    "select_one",
    "insert_query",
    "insert_query_returning",
    "update_query",
    "delete_query",
    "get_connection",
    "get_connection_pool",
    "health_check",
    "close_all_pools",
]

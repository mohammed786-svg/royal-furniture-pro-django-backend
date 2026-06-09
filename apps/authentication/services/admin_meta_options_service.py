from __future__ import annotations

from apps.authentication.repositories.role_repository import role_repository
from core.helpers.text import from_db_text


class AdminMetaOptionsService:
    def get_options(self) -> dict[str, object]:
        roles = [
            {
                "id": str(row["role_id"]),
                "code": row["role_code"],
                "name": row["role_name"],
                "description": from_db_text(row.get("description")),
            }
            for row in role_repository.list_admin_roles()
        ]
        return {
            "roles": roles,
            "loginTypes": ["admin", "customer"],
            "loginStatuses": ["success", "failed"],
        }


admin_meta_options_service = AdminMetaOptionsService()

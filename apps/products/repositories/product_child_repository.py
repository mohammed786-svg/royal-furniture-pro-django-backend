from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import select_query, update_query
from core.database.raw_queries import execute


class ProductChildRepository:
    schema = "royal"

    def list_images(self, product_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT * FROM {self.schema}.product_imagestbl
            WHERE product_id = %s AND is_deleted = FALSE
            ORDER BY is_primary DESC, display_order ASC, product_image_id ASC
        """
        return select_query(sql, [product_id])

    def list_variants(self, product_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT * FROM {self.schema}.product_varianttbl
            WHERE product_id = %s AND is_deleted = FALSE
            ORDER BY is_default DESC, product_variant_id ASC
        """
        return select_query(sql, [product_id])

    def fetch_default_variant_id(self, product_id: int) -> Optional[int]:
        variants = self.list_variants(product_id)
        if not variants:
            return None
        return int(variants[0]["product_variant_id"])

    def list_specifications(self, product_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT * FROM {self.schema}.product_specificationtbl
            WHERE product_id = %s AND is_deleted = FALSE
            ORDER BY display_order ASC, product_specification_id ASC
        """
        return select_query(sql, [product_id])

    def list_features(self, product_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT * FROM {self.schema}.product_featuretbl
            WHERE product_id = %s AND is_deleted = FALSE
            ORDER BY display_order ASC, product_feature_id ASC
        """
        return select_query(sql, [product_id])

    def soft_delete_images(self, product_id: int, *, conn: PgConnection) -> None:
        sql = f"""
            UPDATE {self.schema}.product_imagestbl
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE product_id = %s AND is_deleted = FALSE
        """
        execute(sql, [product_id], conn=conn)

    def soft_delete_variant(self, variant_id: int, *, conn: PgConnection) -> None:
        sql = f"""
            UPDATE {self.schema}.product_varianttbl
            SET is_deleted = TRUE,
                is_active = FALSE,
                sku = sku || '__del__' || product_variant_id::text,
                updated_at = NOW()
            WHERE product_variant_id = %s AND is_deleted = FALSE
        """
        execute(sql, [variant_id], conn=conn)

    def soft_delete_variants(self, product_id: int, *, conn: PgConnection) -> None:
        sql = f"""
            UPDATE {self.schema}.product_varianttbl
            SET is_deleted = TRUE,
                is_active = FALSE,
                sku = sku || '__del__' || product_variant_id::text,
                updated_at = NOW()
            WHERE product_id = %s AND is_deleted = FALSE
        """
        execute(sql, [product_id], conn=conn)

    def soft_delete_specifications(self, product_id: int, *, conn: PgConnection) -> None:
        sql = f"""
            UPDATE {self.schema}.product_specificationtbl
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE product_id = %s AND is_deleted = FALSE
        """
        execute(sql, [product_id], conn=conn)

    def soft_delete_features(self, product_id: int, *, conn: PgConnection) -> None:
        sql = f"""
            UPDATE {self.schema}.product_featuretbl
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE product_id = %s AND is_deleted = FALSE
        """
        execute(sql, [product_id], conn=conn)

    def insert_image(self, data: dict[str, Any], *, conn: PgConnection) -> None:
        sql = f"""
            INSERT INTO {self.schema}.product_imagestbl
                (product_id, product_variant_id, image_url, alt_text, image_type,
                 is_360, is_primary, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute(sql, list(data.values()), conn=conn)

    def insert_variant(self, data: dict[str, Any], *, conn: PgConnection) -> None:
        sql = f"""
            INSERT INTO {self.schema}.product_varianttbl
                (product_id, variant_name, sku, barcode, color, fabric, size, material,
                 price, sale_price, mrp, weight, dimensions, is_default, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute(sql, list(data.values()), conn=conn)

    def update_variant(self, variant_id: int, data: dict[str, Any], *, conn: PgConnection) -> None:
        sql = f"""
            UPDATE {self.schema}.product_varianttbl
            SET variant_name = %s,
                sku = %s,
                barcode = %s,
                color = %s,
                fabric = %s,
                size = %s,
                material = %s,
                price = %s,
                sale_price = %s,
                mrp = %s,
                weight = %s,
                dimensions = %s,
                is_default = %s,
                is_active = %s,
                updated_at = NOW()
            WHERE product_variant_id = %s AND is_deleted = FALSE
        """
        params = [
            data["variant_name"],
            data["sku"],
            data["barcode"],
            data["color"],
            data["fabric"],
            data["size"],
            data["material"],
            data["price"],
            data["sale_price"],
            data["mrp"],
            data["weight"],
            data["dimensions"],
            data["is_default"],
            data["is_active"],
            variant_id,
        ]
        execute(sql, params, conn=conn)

    def insert_specification(self, data: dict[str, Any], *, conn: PgConnection) -> None:
        sql = f"""
            INSERT INTO {self.schema}.product_specificationtbl
                (product_id, spec_group, spec_key, spec_value, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        execute(sql, list(data.values()), conn=conn)

    def insert_feature(self, data: dict[str, Any], *, conn: PgConnection) -> None:
        sql = f"""
            INSERT INTO {self.schema}.product_featuretbl
                (product_id, feature_title, feature_description, icon_url,
                 display_order, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        execute(sql, list(data.values()), conn=conn)

    def variant_sku_exists(self, sku: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT product_variant_id FROM {self.schema}.product_varianttbl
            WHERE sku = %s AND is_deleted = FALSE
        """
        from core.database import select_one

        params: list[Any] = [sku]
        if exclude_id:
            sql += " AND product_variant_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None


product_child_repository = ProductChildRepository()

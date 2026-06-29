# Shiprocket integration (Royal Furniture Pro)

Orders placed on the storefront are synced to [Shiprocket](https://apidocs.shiprocket.in/) automatically. Tracking on `/track-order` and admin **Shipping** / **Orders → Tracking** use Shiprocket data.

## 1. Create Shiprocket API user

1. Log in to [Shiprocket Panel](https://app.shiprocket.in/)
2. **Settings → API → Configure → Create an API User**
3. Use an email **not** registered as your main Shiprocket login
4. Set a strong password and note the **pickup location** name (e.g. `Primary`)

Reference: [Shiprocket API helpsheet](https://support.shiprocket.in/support/solutions/articles/43000337456-shiprocket-api-document-helpsheet)

## 2. Backend `.env` (VPS)

Add to `/root/royal-furniture-pro-django-backend/.env`:

```env
SHIPROCKET_ENABLED=True
SHIPROCKET_API_BASE_URL=https://apiv2.shiprocket.in
SHIPROCKET_EMAIL=your-api-user@example.com
SHIPROCKET_PASSWORD=your-api-password
SHIPROCKET_PICKUP_LOCATION=Primary
SHIPROCKET_DEFAULT_WEIGHT_KG=1.0
SHIPROCKET_DEFAULT_LENGTH_CM=10
SHIPROCKET_DEFAULT_BREADTH_CM=10
SHIPROCKET_DEFAULT_HEIGHT_CM=10
```

`SHIPROCKET_PICKUP_LOCATION` must match the warehouse name in Shiprocket **Settings → Pickup Locations**.

Restart after changes:

```bash
sudo systemctl restart royal-furniture-gunicorn
```

## 3. Webhook (live tracking updates)

In Shiprocket → **Settings → API → Webhooks**, add:

```
https://royalfurniturepro.azdeploy.com/api/v1/shipping/webhook/shiprocket/
```

Do not use the words `shiprocket`, `kartrocket`, `sr`, or `kr` in the URL path (Shiprocket restriction). Our path uses `/shipping/webhook/shiprocket/` which is acceptable.

## 4. What happens on checkout

1. Customer completes `POST /api/v1/storefront/checkout/`
2. Order is saved in `ordertbl`
3. Backend calls Shiprocket `POST /v1/external/orders/create/adhoc`
4. Shipment row is stored in `shipmenttbl` with Shiprocket order/shipment IDs
5. Tracking events are stored in `shipment_trackingtbl`

If Shiprocket fails, the storefront order still succeeds (error is logged).

## 5. Storefront tracking

- **Track order:** `GET /api/v1/storefront/orders/track/?orderNumber=RF-ORD-...&mobile=9876543210`
- **My orders (logged in):** `GET /api/v1/storefront/orders/`

## 6. Admin Shiprocket panel

Under **SHIPROCKET** in the admin sidebar (below Orders):

| Page | API |
|------|-----|
| SR Orders | `GET /api/v1/shipping/shiprocket/orders/` |
| Order detail | `GET /api/v1/shipping/shiprocket/orders/{sr_order_id}/` |
| SR Tracking | `GET /api/v1/shipping/shiprocket/track/?awb=` |
| SR Rate Calculator | `GET /api/v1/shipping/shiprocket/serviceability/` |

## 7. Product package dimensions

Run migration on PostgreSQL:

```bash
psql -U postgres -d royal_furniture_db -f database/migrations_sql/add_product_shipping_dimensions.sql
```

In **Catalog → Products → Physical Details**, enter package length/breadth/height in cm, inches, feet, or meters. Values are stored in **cm** and sent to Shiprocket on checkout.

## 8. Admin (local shipments)

- **Orders → order detail → Tracking tab:** internal order tracking + Shiprocket shipment events
- **Shipping → Shipments:** all Shiprocket-linked shipments
- **Shipping → Tracking:** courier scan timeline

## 9. Troubleshooting

| Issue | Check |
|-------|--------|
| Order not in Shiprocket | `SHIPROCKET_ENABLED`, email/password, pickup location name |
| 401 from Shiprocket | Regenerate API user; token caches 9 days in Redis — `redis-cli DEL royal:shiprocket:auth_token` |
| Track page empty | AWB assigned later; webhook or revisit track page to refresh |
| Wrong weight/dims | Adjust `SHIPROCKET_DEFAULT_*` env vars |

Never commit `SHIPROCKET_PASSWORD` to git.

# Firebase Google Sign-In Setup

Storefront customers sign in with **Google (Gmail)** only. Admin login is separate (`/my-admin/login`).

---

## 1. Create a Firebase project

1. Open [Firebase Console](https://console.firebase.google.com/)
2. **Add project** (e.g. `royal-furniture-pro`)
3. Disable Google Analytics if you do not need it (optional)

---

## 2. Enable Google Authentication

1. Firebase Console → **Build** → **Authentication**
2. **Get started** → **Sign-in method**
3. Enable **Google**
4. Set a support email and save

---

## 3. Register the web app (frontend)

1. Project overview → **Add app** → **Web** (`</>`)
2. App nickname: `Royal Furniture Pro Web`
3. Copy the `firebaseConfig` values into frontend env:

```env
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
```

**Local:** `frontend/.env.local`  
**Production:** `frontend/.env.production`

---

## 4. Authorized domains

Firebase Console → **Authentication** → **Settings** → **Authorized domains**

Add:

- `localhost`
- `royalfurniturepro.azdeploy.com`
- Any custom domain you use later

---

## 5. Backend service account (token verification)

1. Firebase Console → **Project settings** (gear) → **Service accounts**
2. **Generate new private key** → download JSON
3. Upload to VPS (keep private), e.g.:

```bash
/root/royal-furniture-pro-django-backend/secrets/firebase-service-account.json
chmod 600 /root/royal-furniture-pro-django-backend/secrets/firebase-service-account.json
```

4. Add to backend `.env`:

```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=/root/royal-furniture-pro-django-backend/secrets/firebase-service-account.json
```

5. Install dependency on VPS:

```bash
cd /root/royal-furniture-pro-django-backend
source venv/bin/activate
pip install 'firebase-admin>=6.5,<7'
sudo systemctl restart royal-furniture-gunicorn
```

---

## 6. API endpoint

After deploy, login flow calls:

`POST /api/v1/storefront/auth/google/`  
Body: `{ "idToken": "<Firebase ID token>" }`

Response: same shape as OTP login (`user`, `accessToken`, `refreshToken`).

---

## 7. Rebuild frontend

```bash
cd /var/www/html/royal_furniture_pro_website/royal-furniture-pro-frontend
npm run build
sudo systemctl restart royal-furniture-frontend
```

---

## 8. Test

1. Open `https://royalfurniturepro.azdeploy.com/login`
2. Click **Continue with Google**
3. Pick a Gmail account
4. You should land on `/account` and be able to add to cart / wishlist

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Google sign-in is not configured` | Set all `NEXT_PUBLIC_FIREBASE_*` vars and rebuild frontend |
| `auth/unauthorized-domain` | Add your domain under Firebase Authorized domains |
| `Invalid or expired Google sign-in token` | Check `FIREBASE_CREDENTIALS_PATH` and `FIREBASE_PROJECT_ID` on backend |
| Cart/wishlist still blocked | Clear site data; sign in again so JWT is stored |

---

## Stock still shows Out of Stock after adding inventory

Product detail is cached in Redis. After adding stock in admin:

```bash
redis-cli KEYS 'royal:product:*'
redis-cli DEL royal:product:your-product-slug
```

New inventory updates now auto-clear product cache when stock is created or updated.

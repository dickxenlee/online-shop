# Méiyì — Go-Live Guide (simple English)

Follow these steps in order. Steps marked 🔑 need YOUR accounts/passwords —
never share those keys or passwords with anyone (including AI chats).
Set them only as environment variables on the host.

## Step 0 — Test everything locally first

```powershell
python manage.py runserver
```
Open http://127.0.0.1:8000/ and click through: add to bag → checkout →
order page. In demo mode no money moves.

## Step 1 — 🔑 Create your admin login (2 minutes)

```powershell
python manage.py createsuperuser
```
Then open http://127.0.0.1:8000/admin/ — this is your control room:
products, stock, orders, discount codes, reviews, subscribers.

## Step 2 — Put the code on GitHub

```powershell
git init
git add .
git commit -m "Meiyi shop"
```
Create an empty repository on github.com, then:
```powershell
git remote add origin https://github.com/YOUR-USERNAME/meiyi.git
git push -u origin main
```
Note: `db.sqlite3` (your local test data) and `media/` should NOT go to
GitHub — create a `.gitignore` first if you haven't.

## Step 3 — Host it on Render (free to start)

1. Sign up at render.com (login with GitHub).
2. Click **New + → Blueprint**, choose your `meiyi` repository.
   Render reads `render.yaml` and creates the website + a Postgres database.
3. After the first deploy, note your address, e.g. `meiyi-abcd.onrender.com`.
4. In Render → your service → **Environment**, fix these two values to match:
   - `ALLOWED_HOSTS` = `meiyi-abcd.onrender.com`
   - `SITE_URL` = `https://meiyi-abcd.onrender.com`
5. Open a Render **Shell** and run, one time:
   ```
   python manage.py createsuperuser
   python manage.py seed        # demo products (optional)
   ```

⚠️ Free plan notes:
- The free web service sleeps after idle — first visit takes ~30s to wake.
- Uploaded photos (media/) are wiped on each deploy on the free plan.
  Fix: use image URLs for products, or add a Render Disk (paid),
  or use Cloudinary later.

## Step 4 — 🔑 Real payments (toyyibPay)

**No toyyibPay yet? You can already sell!** On the live site (DEBUG=false),
when no gateway keys are set, **bank-transfer mode** turns on by itself:
- The customer places the order → it stays **Pending** (stock is reserved)
- She gets an email + a WhatsApp button with your order number
- She transfers the money to your bank, you check your bank app
- In the admin, select the order → action **"Mark as PAID + email receipt"**
- Then **"Mark as SHIPPED"** when you post it. That's a real business already.

When you're ready for automatic FPX/card payments:

1. Practice first on the sandbox: https://dev.toyyibpay.com — register,
   create a **Category**, copy the **Secret Key** and **Category Code**.
2. In Render → Environment add:
   - `TOYYIBPAY_SECRET_KEY` = your key
   - `TOYYIBPAY_CATEGORY_CODE` = your category code
   (Sandbox is the default server. Test a full FPX payment on the site.)
3. When ready for REAL money: register at https://toyyibpay.com
   (they will ask for your SSM business registration + bank account),
   then set the live keys and add:
   - `TOYYIBPAY_BASE_URL` = `https://toyyibpay.com`

## Step 5 — 🔑 Real order emails

Easiest: a Gmail account + App Password (Google Account → Security →
2-Step Verification → App passwords). In Render → Environment add:
- `EMAIL_BACKEND` = `django.core.mail.backends.smtp.EmailBackend`
- `EMAIL_HOST` = `smtp.gmail.com`
- `EMAIL_HOST_USER` = `you@gmail.com`
- `EMAIL_HOST_PASSWORD` = the app password
- `DEFAULT_FROM_EMAIL` = `Méiyì <you@gmail.com>`

## Step 6 — Final business touches

- `WHATSAPP_NUMBER` env var = your real number, e.g. `60123456789`
- Replace placeholder illustrations with real product photos (admin upload,
  or paste image URLs on each product)
- Buy a real domain (e.g. meiyi.my) and add it in Render → Custom Domains;
  then add the domain to `ALLOWED_HOSTS` and `SITE_URL`

## Security on the live site

- Use a **long password** for your admin login (a phrase of 4+ random words).
  Never reuse a password from another site.
- Optional but smart: move the admin door. In Render → Environment add
  `ADMIN_URL` = a secret path like `manage-meiyi-x7k2/` — then your admin is
  at `https://your-site/manage-meiyi-x7k2/` and bots that try `/admin/`
  just get a 404. Don't tell anyone the path.
- Payments are double-checked with toyyibPay's own servers before an order
  is ever marked paid — a fake "payment done" message can't fool the shop.

## Money & legal (Malaysia)

- toyyibPay charges ~RM1 per FPX transaction (check their current rates)
- To receive real payments you need an SSM-registered business
- Show your business name/registration in the site footer once registered

That's it. One step a day and you're live within a week. 🌸

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

## Step 3 — Host it online for FREE (about 30 minutes)

Two free accounts, no credit card:
**Neon** = the database (keeps your orders) · **Render** = the website.

Do the database FIRST, or the website has nowhere to save orders.

### 3a. Free database — Neon (5 min)

1. Go to https://neon.com → **Sign up with GitHub**.
2. Create a project. Name: `meiyi`. Region: pick **Singapore**
   (closest to Malaysia = faster).
3. On the dashboard, find **Connection string** and click copy.
   It looks like `postgresql://user:password@ep-xxx.aws.neon.tech/neondb?sslmode=require`
4. Paste it in Notepad for a minute. 🔑 **It contains a password — keep it
   private.** Never put it in GitHub, never paste it into a chat.

> Why not Render's own free database? Render deletes free databases after
> 30 days. Neon's free plan has no expiry, so your orders stay safe.

### 3b. Free website — Render (10 min)

1. Go to https://render.com → **Sign up with GitHub**.
2. Click **New + → Blueprint** → choose your `online-shop` repository →
   **Connect**. Render reads `render.yaml`.
3. It will ask you for `DATABASE_URL` — paste the Neon string from 3a.
4. Click **Apply / Deploy** and wait ~5 minutes (watch the build log).

### 3c. Fix your address (3 min)

The name `meiyi` may be taken, so your real address might be
`meiyi-abcd.onrender.com`. Look at the top of your Render service page.

In Render → your service → **Environment**, correct these two:
- `ALLOWED_HOSTS` = `meiyi-abcd.onrender.com`  (no `https://`)
- `SITE_URL` = `https://meiyi-abcd.onrender.com`

Save — Render redeploys by itself.

> If you skip this you get a **"DisallowedHost"** error page. That is normal
> and this fixes it.

### 3d. Fill the live shop (5 min)

Render → your service → **Shell** tab:
```
python manage.py createsuperuser
python manage.py seed        # demo products (optional)
```
This admin login is separate from your computer's one.

Now open `https://your-address.onrender.com` — your shop is live on the
internet. Send the link to a friend to test. 🌸

### 3e. Keep product photos safe — Cloudinary (5 min)

Render deletes files uploaded to its local disk during a new deployment.
Connect the free Cloudinary image service before you upload real product
photos:

1. Create a free account at https://cloudinary.com.
2. In the Cloudinary dashboard, open **API Keys** and copy **Environment
   variable**. It starts with `CLOUDINARY_URL=cloudinary://`.
3. In Render → your service → **Environment**, add:
   - Key: `CLOUDINARY_URL`
   - Value: paste only the value after the `=` sign.
4. Save changes. Render redeploys automatically.
5. Open your admin dashboard → **Quick Add Product**. Choose one or more
   photos. The first photo is the cover and the others become the gallery.

🔑 `CLOUDINARY_URL` contains a secret. Do not put it in GitHub, screenshots,
or chat messages. After it is set, Quick Add Product and normal admin image
uploads stay safe across Render redeployments.

⚠️ What "free" costs you:
- The site **sleeps after 15 minutes** with no visitors. The next visitor
  waits ~50 seconds for it to wake up. Fine for testing and first customers.
  Render's cheapest paid plan (~USD 7/month) removes the sleeping.
- Neon free: 0.5 GB storage — that is tens of thousands of orders. Plenty.

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

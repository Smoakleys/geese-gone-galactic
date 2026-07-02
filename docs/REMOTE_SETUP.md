# Remote setup — email digests + (next) remote control

Owner-facing activation steps for the notifier and the remote control site. The **code** is
built and tested; these are the one-time steps that need *your* accounts/secrets. Nothing here
is ever committed — secrets live in gitignored `*.local.json`.

## 1. Email digests (SMTP + Gmail app password)

The harness sends a **concise digest per work session** to `bridgerhumphreys03@gmail.com` (plus
an immediate alert on a blocked run / STOP). Delivery is plain SMTP with a Gmail **app password**
(Google requires this for SMTP when 2-Step Verification is on; your normal password won't work).

**Steps:**
1. Turn on 2-Step Verification if it isn't already: Google Account → **Security**.
2. Google Account → Security → **2-Step Verification** → **App passwords** → generate one
   (name it e.g. "GGG harness"). You'll get a 16-character password.
3. Create the gitignored config from the template:
   ```
   cp ops/notify_config.example.json ops/notify_config.local.json
   ```
   and paste the 16-char app password into `"app_password"`. (Or just hand the app password to
   Claude in-session and it will write the file for you — it stays local, never committed.)
4. Verify it works:
   ```
   python ops/notify.py test        # sends a one-line "it works" email to your inbox
   python ops/notify.py preview     # prints the next digest WITHOUT sending
   python ops/notify.py digest      # builds + sends the session digest, advances the marker
   ```

If `ops/notify_config.local.json` is absent, the notifier runs a harmless **console dry-run** —
so the harness (and the test suite) works with no credentials; you just don't get email until
the config is filled.

**What's in the digest:** a headline (`GGG harness: N changes, 131 tests green`), the test-count
rollup, and one line per harness change since the last email (subject + PR/commit ref).

## 2. Remote control site (Cloudflare Tunnel)

_Built in the next increment — this section will cover: start the token-authed dashboard, run
`cloudflared tunnel login` once, and open the HTTPS URL on your phone to Start/Pause/Stop._

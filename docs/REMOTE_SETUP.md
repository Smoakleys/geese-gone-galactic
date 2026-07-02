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

A token-protected **status + Start/Pause/Stop** dashboard, reachable from your phone via a
Cloudflare tunnel. **Stop** halts the whole autonomous system (writes `ops/STOP`, which the
Claude loop obeys, and sets the runner to STOPPED); **Start** clears it and re-arms
`ops/AUTOPILOT_ON`; **Pause** parks the runner only (resumable).

**One-time install:** get `cloudflared` on PATH:
```
winget install --id Cloudflare.cloudflared
```
(No Cloudflare account or login is needed for the quick-tunnel mode below.)

**Run it** (share the store with the autopilot by matching `--workdir`):
```
# terminal 1 — the build, using a persistent workspace so control is shared:
python scripts/run_onepond_autopilot.py --workdir .autopilot --serve   # (or your normal run)

# terminal 2 — the remote control site + tunnel:
python ops/serve_remote.py --store .autopilot/.harness/state.json
```
`serve_remote` serves the token-gated dashboard on `127.0.0.1:8787`, generates an access token
into `ops/dashboard_token.local` (gitignored), launches a Cloudflare **quick tunnel**, and prints
(and, if the email notifier is set up, emails you) the live `https://<random>.trycloudflare.com`
URL **and the token**. Open the URL on your phone, enter the token once, and you're in.

Notes:
- The quick-tunnel URL **changes each launch**. For a permanent URL, set up a *named* tunnel
  (`cloudflared tunnel login` → `cloudflared tunnel create ggg` → route a hostname → run it
  against `http://127.0.0.1:8787`); the dashboard side is identical.
- No `cloudflared`? `serve_remote` falls back to serving locally and prints the LAN/local URL;
  add `--no-tunnel` to force local-only.
- Access token: read from `$GGG_DASHBOARD_TOKEN`, else `ops/dashboard_token.local`, else generated.

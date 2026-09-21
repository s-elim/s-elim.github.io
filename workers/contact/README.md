# Anonymous messages for s-elim.github.io

Visitors write a message in the footer dialog; this Cloudflare Worker checks it
and emails it to one inbox. It uses only free tiers:

| Piece | What it does | Free allowance (check the vendor's page) |
| --- | --- | --- |
| Cloudflare Workers | receives the message | 100,000 requests per day |
| Cloudflare Turnstile | invisible spam check | free |
| Resend | sends the email | 3,000 emails per month, 100 per day |

Cloudflare's own Email Routing would avoid Resend, but it only works for a domain
you own on Cloudflare, and a domain costs money. Resend's free tier can deliver to
the address you sign up with, which is all this needs.

Nothing is stored. The visitor's IP address is not forwarded to Turnstile or
Resend and is never logged. Messages are plain text, and visitor text never
reaches the email subject or headers; a valid email typed in the optional contact
field becomes the Reply-To address.

## Set up (about 20 minutes, no terminal needed)

1. **Cloudflare account.** Sign up at dash.cloudflare.com (free, no card).
2. **Turnstile widget.** Dashboard > Turnstile > Add widget. Name it
   `homepage`, add the hostnames `s-elim.github.io` and `localhost`, choose
   **Managed**. Keep the **site key** (public) and the **secret key** (private).
3. **Resend account.** Sign up at resend.com with the Gmail address where you want
   the messages. API Keys > Create API key, permission **Sending access**. Keep
   the key.
4. **The Worker.** Dashboard > Workers & Pages > Create > Create Worker. Name it
   `homepage-contact`, click Deploy, then **Edit code**. Replace everything in
   the editor with the contents of `src/worker.js` and click Deploy.
5. **Settings.** Worker > Settings > Variables and secrets > Add:
   - `ALLOWED_ORIGINS`, type Text: `https://s-elim.github.io`
   - `TURNSTILE_SECRET`, type Secret: the Turnstile secret key
   - `RESEND_API_KEY`, type Secret: the Resend key
   - `TO_EMAIL`, type Secret: the Gmail address you signed up to Resend with

   Deploy again after saving.
6. **Connect the site.** Copy the Worker's URL (it looks like
   `https://homepage-contact.<your-subdomain>.workers.dev`) and put it, with the
   Turnstile site key, in `_config.yml`:

   ```yaml
   contact:
     endpoint: "https://homepage-contact.<your-subdomain>.workers.dev"
     turnstile_sitekey: "0x4AAAA..."
   ```

   Both values are public by design. The footer button stays hidden until both
   are set.

Terminal route instead of step 4 and 5: `npx wrangler deploy` in this folder, then
`npx wrangler secret put` for each secret listed in `wrangler.toml`.

## Test

```
node --test
```

The tests inject a fake `fetch`, so they never call Turnstile or Resend.

To try the live Worker from your own machine, add `http://localhost:4000` to
`ALLOWED_ORIGINS` while you test and remove it afterwards.

## If something goes wrong

- **"Messages are not set up yet"**: one of the three secrets is missing.
- **"The spam check failed"**: the Turnstile hostnames do not include the page's
  host, or the site key and secret key come from different widgets.
- **"could not be delivered"**: the Resend key is wrong, or `TO_EMAIL` is not the
  address the Resend account was created with.
- Worker > Logs shows the reason without the message text.

// Anonymous messages from s-elim.github.io, delivered by email.
//
// The site posts JSON here; this Worker checks the origin, a honeypot field and
// a Cloudflare Turnstile token, then sends the text to one inbox through
// Resend's free tier. Nothing is stored, and the visitor's IP address is never
// forwarded or logged.
//
// Settings (Cloudflare dashboard > Worker > Settings > Variables and secrets):
//   ALLOWED_ORIGINS   text    comma-separated, e.g. "https://s-elim.github.io"
//   TURNSTILE_SECRET  secret  from Cloudflare Turnstile
//   RESEND_API_KEY    secret  from resend.com
//   TO_EMAIL          secret  the inbox; on Resend's free tier without your own
//                             domain it must be the address you signed up with
//   FROM_EMAIL        text    optional, defaults to onboarding@resend.dev
//   RATE_LIMITER      binding optional Workers rate-limit binding

export const LIMITS = { body: 12000, message: 2000, minMessage: 10, contact: 200 };

const TURNSTILE_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';
const RESEND_URL = 'https://api.resend.com/emails';
const DEFAULT_FROM = 'Homepage messages <onboarding@resend.dev>';
const EMAIL_RE = /^[^\s@<>()",;:]+@[^\s@<>()",;:]+\.[a-z]{2,}$/i;

export default {
  fetch(request, env) {
    return handle(request, env, fetch);
  },
};

export async function handle(request, env, fetchImpl) {
  const origin = request.headers.get('Origin') || '';
  const allowed = String(env.ALLOWED_ORIGINS || '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
  if (!origin || !allowed.includes(origin)) {
    return new Response('Forbidden', { status: 403 });
  }
  const cors = {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
  const reply = (status, body) =>
    new Response(JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json' } });
  const fail = (status, error) => reply(status, { ok: false, error });

  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
  if (request.method !== 'POST') return fail(405, 'Only POST is accepted.');
  if (!(request.headers.get('Content-Type') || '').toLowerCase().startsWith('application/json')) {
    return fail(415, 'Send the message as JSON.');
  }

  const raw = await request.text();
  if (raw.length > LIMITS.body) return fail(413, 'That message is too long.');
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return fail(400, 'The message could not be read. Reload the page and try again.');
  }
  if (!data || typeof data !== 'object') return fail(400, 'The message could not be read.');

  // Bots fill every field; people never see this one.
  if (typeof data.website === 'string' && data.website.trim() !== '') return reply(200, { ok: true });

  const message = typeof data.message === 'string' ? data.message.trim() : '';
  const contact = typeof data.contact === 'string' ? data.contact.trim() : '';
  const token = typeof data.token === 'string' ? data.token : '';
  const page = typeof data.page === 'string' ? data.page.slice(0, 200) : '';
  if (message.length < LIMITS.minMessage) {
    return fail(400, 'Write at least ' + LIMITS.minMessage + ' characters.');
  }
  if (message.length > LIMITS.message) {
    return fail(400, 'Keep the message under ' + LIMITS.message + ' characters.');
  }
  if (contact.length > LIMITS.contact) return fail(400, 'The contact field is too long.');
  if (!token) return fail(400, 'The spam check has not finished. Wait a moment and send again.');

  if (!env.TURNSTILE_SECRET || !env.RESEND_API_KEY || !env.TO_EMAIL) {
    console.error('contact worker: missing TURNSTILE_SECRET, RESEND_API_KEY or TO_EMAIL');
    return fail(500, 'Messages are not set up yet. Please try again later.');
  }

  if (env.RATE_LIMITER) {
    const key = request.headers.get('CF-Connecting-IP') || 'anonymous';
    const { success } = await env.RATE_LIMITER.limit({ key });
    if (!success) return fail(429, 'Too many messages in a short time. Try again in a minute.');
  }

  const form = new FormData();
  form.append('secret', env.TURNSTILE_SECRET);
  form.append('response', token);
  const check = await fetchImpl(TURNSTILE_URL, { method: 'POST', body: form })
    .then(r => r.json())
    .catch(() => ({ success: false }));
  const hosts = allowed.map(o => {
    try { return new URL(o).hostname; } catch { return ''; }
  });
  if (!check.success || (check.hostname && !hosts.includes(check.hostname))) {
    return fail(403, 'The spam check failed. Reload the page and try again.');
  }

  const replyTo = EMAIL_RE.test(contact) && !/[\r\n]/.test(contact) ? contact : undefined;
  const text = [
    message,
    '',
    '----',
    'Reply contact: ' + (contact || 'not given'),
    'Sent from: ' + (page || 'unknown page'),
    'Received: ' + new Date().toISOString(),
  ].join('\n');
  const mail = {
    from: env.FROM_EMAIL || DEFAULT_FROM,
    to: [env.TO_EMAIL],
    subject: 'New anonymous message from your homepage',
    text,
  };
  if (replyTo) mail.reply_to = replyTo;

  const sent = await fetchImpl(RESEND_URL, {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + env.RESEND_API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify(mail),
  }).catch(() => null);
  if (!sent || !sent.ok) {
    console.error('contact worker: delivery failed with status', sent ? sent.status : 'network error');
    return fail(502, 'The message could not be delivered. Please try again later.');
  }
  return reply(200, { ok: true });
}

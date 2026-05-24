const CHECK_INTERVAL_HOURS = 6;

const HM_SCHEMA_RE = /<script[^>]+id="product-group-schema"[^>]*>([\s\S]*?)<\/script>/;

async function fetchPage(url, useCredentials = false) {
  const resp = await fetch(url, {
    credentials: useCredentials ? 'include' : 'omit',
    headers: {
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
      'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8',
      'Cache-Control': 'no-cache',
    },
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.text();
}

async function scrapeHm(url, useCredentials) {
  const html = await fetchPage(url, useCredentials);
  const match = HM_SCHEMA_RE.exec(html);
  if (!match) throw new Error('No product-group-schema found');
  const data = JSON.parse(match[1]);
  const first = (data.hasVariant || [])[0] || {};
  const offer = first.offers || {};
  return {
    name: data.name || 'Unknown',
    price: parseFloat(offer.price),
    url: offer.url || url,
    id: null,
  };
}

async function scrapeSchemaOrg(url, useCredentials) {
  const html = await fetchPage(url, useCredentials);
  const re = /<script[^>]+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g;
  for (const match of html.matchAll(re)) {
    try {
      const data = JSON.parse(match[1]);
      if (data['@type'] === 'Product' && data.offers) {
        return {
          name: data.name || 'Unknown',
          price: parseFloat(data.offers.price),
          url: data.offers.url || url,
          id: data.sku || null,
        };
      }
    } catch (e) {}
  }
  throw new Error('No Product JSON-LD found');
}

async function scrapeProduct(url, strategy, useCredentials) {
  switch (strategy) {
    case 'hm': return scrapeHm(url, useCredentials);
    case 'schema-org': return scrapeSchemaOrg(url, useCredentials);
    default: throw new Error(`Unknown strategy: ${strategy}`);
  }
}

function matchStore(url, storeConfigs) {
  for (const [key, cfg] of Object.entries(storeConfigs)) {
    if (url.includes(cfg.hostPattern)) return { key, cfg };
  }
  return null;
}

async function checkPrices() {
  const { homelabUrl = '', lastCheck = 0 } = await chrome.storage.sync.get(['homelabUrl', 'lastCheck']);
  const nowMs = Date.now();
  if (nowMs - lastCheck < CHECK_INTERVAL_HOURS * 60 * 60 * 1000) return;
  if (!homelabUrl) return;

  let products, storeConfigs;
  try {
    [products, storeConfigs] = await Promise.all([
      fetch(`${homelabUrl}/api/products`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }),
      fetch(`${homelabUrl}/api/stores`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }),
    ]);
  } catch (e) {
    console.error('Failed to fetch from homelab:', e.message);
    return;
  }

  if (!products.length) return;

  for (const product of products) {
    const storeMatch = matchStore(product.url, storeConfigs);
    if (!storeMatch) {
      console.warn(`No store config for URL: ${product.url}`);
      continue;
    }

    try {
      const result = await scrapeProduct(product.url, storeMatch.cfg.scrapeStrategy, storeMatch.cfg.useCredentials ?? false);
      await fetch(`${homelabUrl}/api/price`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: result.id || product.id,
          store: product.store,
          name: result.name,
          price: result.price,
          url: result.url,
        }),
      });
    } catch (e) {
      console.error(`Error for ${product.url}:`, e.message);
    }

    await new Promise(r => setTimeout(r, 2000 + Math.random() * 3000));
  }

  await chrome.storage.sync.set({ lastCheck: nowMs });
}

chrome.alarms.create('priceCheck', { periodInMinutes: CHECK_INTERVAL_HOURS * 60 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'priceCheck') checkPrices();
});

chrome.runtime.onStartup.addListener(checkPrices);
chrome.runtime.onInstalled.addListener(checkPrices);

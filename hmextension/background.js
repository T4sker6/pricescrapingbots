const CHECK_INTERVAL_HOURS = 6;
const SCHEMA_RE = /<script[^>]+id="product-group-schema"[^>]*>([\s\S]*?)<\/script>/;

async function scrapeProduct(url) {
  const resp = await fetch(url, {
    credentials: 'include',
    headers: {
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
      'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8',
      'Cache-Control': 'no-cache',
    },
  });

  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

  const html = await resp.text();
  const match = SCHEMA_RE.exec(html);
  if (!match) throw new Error('No product-group-schema found');

  const data = JSON.parse(match[1]);
  const variants = data.hasVariant || [];
  const first = variants[0] || {};
  const offer = first.offers || {};

  return {
    name: data.name || 'Unknown',
    price: parseFloat(offer.price),
    url: offer.url || url,
  };
}

async function checkPrices() {
  const { homelabUrl = '', lastCheck = 0 } = await chrome.storage.sync.get(['homelabUrl', 'lastCheck']);

  const nowMs = Date.now();
  if (nowMs - lastCheck < CHECK_INTERVAL_HOURS * 60 * 60 * 1000) return;
  if (!homelabUrl) return;

  let products;
  try {
    const resp = await fetch(`${homelabUrl}/api/products`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    products = await resp.json();
  } catch (e) {
    console.error('Failed to fetch products from homelab:', e.message);
    return;
  }

  if (!products.length) return;

  for (const product of products) {
    try {
      const result = await scrapeProduct(product.url);

      await fetch(`${homelabUrl}/api/price`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: product.id,
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

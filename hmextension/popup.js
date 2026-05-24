async function load() {
  const { homelabUrl = '', lastCheck = 0 } = await chrome.storage.sync.get(['homelabUrl', 'lastCheck']);
  document.getElementById('homelabUrl').value = homelabUrl;

  const status = document.getElementById('status');
  if (lastCheck) {
    const mins = Math.round((Date.now() - lastCheck) / 60000);
    status.textContent = `Ostatni scrape: ${mins < 60 ? mins + ' min temu' : Math.round(mins / 60) + 'h temu'}`;
  }
}

document.getElementById('saveBtn').addEventListener('click', async () => {
  const url = document.getElementById('homelabUrl').value.trim().replace(/\/$/, '');
  const status = document.getElementById('status');

  if (!url) {
    status.textContent = 'Podaj URL homelabu.';
    status.className = 'status err';
    return;
  }

  await chrome.storage.sync.set({ homelabUrl: url });

  try {
    const resp = await fetch(`${url}/api/products`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const products = await resp.json();
    status.textContent = `Połączono. Śledzone produkty: ${products.length}`;
    status.className = 'status ok';
  } catch (e) {
    status.textContent = `Zapisano, ale brak połączenia: ${e.message}`;
    status.className = 'status err';
  }
});

load();

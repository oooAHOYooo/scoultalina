// MVP dashboard wiring: Leaflet map, filters, KPIs, routes/properties, watchlist
(function () {
  const api = {
    async getJSON(url, opts = {}) {
      const res = await fetch(url, opts);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    },
  };

  function getApiKey() {
    return localStorage.getItem('api_key') || '';
  }

  function authHeaders() {
    const k = getApiKey();
    return k ? { 'X-API-Key': k } : {};
  }

  // Leaflet map
  let map;
  let routesLayer;

  function ensureMap() {
    if (map) return map;
    const el = document.getElementById('map');
    if (!el) return null;
    map = L.map(el).setView([41.5, -72.7], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap',
    }).addTo(map);
    routesLayer = L.layerGroup().addTo(map);
    return map;
  }

  function rarityThresholdValue(v) {
    const order = { common: 0, rare: 1, epic: 2, legendary: 3 };
    return order[v] ?? 0;
  }

  async function loadStats() {
    try {
      const data = await api.getJSON('/api/stats', { headers: authHeaders() });
      const byId = (id, val) => { const n = document.getElementById(id); if (n) n.textContent = String(val); };
      byId('total-properties', data.total_properties ?? 0);
      byId('total-distance', (data.total_distance_km ?? 0).toFixed(1));
      byId('total-routes', data.total_routes ?? 0);
      byId('neighborhoods', data.neighborhoods_covered ?? 0);
    } catch (e) { /* ignore for MVP */ }
  }

  async function loadRoutesAndRender(filters) {
    ensureMap(); if (!map) return;
    routesLayer.clearLayers();

    // date filter: use preset end date
    let query = '';
    if (filters?.dateRange?.preset && filters.dateRange.start) {
      // API supports single date; we fallback to last 30d or selected day for MVP
      const d = new Date(filters.dateRange.start);
      const iso = d.toISOString().slice(0, 10);
      query = `?date=${encodeURIComponent(iso)}`;
    }

    const data = await api.getJSON(`/api/routes${query}`, { headers: authHeaders() });
    const routes = data.routes || [];
    let anyBounds;
    for (const r of routes) {
      if (!r.geojson || !r.geojson.coordinates) continue;
      // Filter by type toggles
      if (!filters.activeTypes?.includes('routes')) continue;
      const coords = r.geojson.coordinates.map(([lon, lat]) => [lat, lon]);
      const poly = L.polyline(coords, { color: '#00d9ff', weight: 4, opacity: 0.9 });
      poly.addTo(routesLayer);
      if (!anyBounds) anyBounds = L.latLngBounds(coords);
      else anyBounds.extend(L.latLngBounds(coords));
      poly.on('click', () => loadPropertiesForRoute(r.id, filters));
    }
    if (anyBounds) map.fitBounds(anyBounds.pad(0.2));
  }

  function passesRarity(min, prop) {
    const val = rarityThresholdValue(min);
    return rarityThresholdValue(prop.rarity || 'common') >= val;
  }

  async function loadPropertiesForRoute(routeId, filters) {
    try {
      const data = await api.getJSON(`/api/properties?route_id=${routeId}`, { headers: authHeaders() });
      const props = (data.properties || []).filter(p => {
        if (filters?.activeTypes && !filters.activeTypes.includes('properties')) return false;
        return passesRarity(filters?.rarityMin || 'common', p);
      });
      renderWatchlistPanel(props);
    } catch (e) { /* ignore */ }
  }

  function renderWatchlistPanel(properties) {
    const c = document.getElementById('watchlist-content');
    if (!c) return;
    c.innerHTML = '';
    for (const p of properties) {
      const item = document.createElement('div');
      item.className = 'border border-white/10 rounded-lg p-3 flex justify-between items-center';
      const left = document.createElement('div');
      left.innerHTML = `<div class="font-semibold">${p.address || 'Property'}</div>
        <div class="text-sm text-[var(--color-text-dim)]">${p.city || ''} ${p.state || ''} ${p.zip || ''}</div>
        <div class="text-sm">${p.price ? `$${Number(p.price).toLocaleString()}` : ''} • ${p.bedrooms || '-'} bd • ${p.bathrooms || '-'} ba</div>`;
      const btn = document.createElement('button');
      btn.className = 'px-3 py-2 text-sm rounded-md border border-white/10 hover:bg-white/5';
      btn.textContent = p.is_in_watchlist ? 'Remove' : 'Add';
      btn.addEventListener('click', async () => {
        try {
          if (p.is_in_watchlist) {
            await fetch(`/api/watchlist/${p.id}`, { method: 'DELETE', headers: authHeaders() });
            p.is_in_watchlist = false;
          } else {
            await fetch(`/api/watchlist`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', ...authHeaders() },
              body: JSON.stringify({ property_id: p.id })
            });
            p.is_in_watchlist = true;
          }
          btn.textContent = p.is_in_watchlist ? 'Remove' : 'Add';
        } catch (e) { /* noop */ }
      });
      item.appendChild(left);
      item.appendChild(btn);
      c.appendChild(item);
    }
  }

  // Filters hookup
  function currentFiltersFromStore() {
    const s = Alpine?.store?.('filtersStore');
    if (!s) return { activeTypes: ['routes', 'properties'], rarityMin: 'common', dateRange: { preset: '7d' } };
    return {
      activeTypes: s.activeTypesArray || Array.from(s.activeTypes || []),
      dateRange: s.dateRange,
      rarityMin: s.rarityMin,
      query: s.query,
    };
  }

  async function refreshAll() {
    await loadStats();
    await loadRoutesAndRender(currentFiltersFromStore());
  }

  document.addEventListener('DOMContentLoaded', () => {
    ensureMap();
    refreshAll();
    window.addEventListener('filters:changed', () => {
      loadRoutesAndRender(currentFiltersFromStore());
    });
  });
})();



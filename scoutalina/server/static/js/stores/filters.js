document.addEventListener('alpine:init', () => {
  function isoDate(d) {
    return new Date(d).toISOString();
  }

  function startOfToday() {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }

  function addDays(d, days) {
    const c = new Date(d);
    c.setDate(c.getDate() + days);
    return c;
  }

  Alpine.store('filtersStore', {
    activeTypes: new Set(['routes', 'properties']),
    dateRange: { preset: '7d' },
    rarityMin: 'common',
    query: '',

    get activeTypesArray() {
      return Array.from(this.activeTypes);
    },

    setPreset(preset) {
      const now = new Date();
      if (preset === 'today') {
        this.dateRange = { preset: 'today', start: isoDate(startOfToday()), end: isoDate(now) };
      } else if (preset === '7d') {
        this.dateRange = { preset: '7d', start: isoDate(addDays(startOfToday(), -6)), end: isoDate(now) };
      } else if (preset === '30d') {
        this.dateRange = { preset: '30d', start: isoDate(addDays(startOfToday(), -29)), end: isoDate(now) };
      } else {
        this.dateRange = { preset: 'custom' };
      }
      this.emit();
    },

    setCustomRange(startIso, endIso) {
      this.dateRange = { preset: 'custom', start: startIso || undefined, end: endIso || undefined };
      this.emit();
    },

    toggleType(type) {
      if (this.activeTypes.has(type)) {
        this.activeTypes.delete(type);
      } else {
        this.activeTypes.add(type);
      }
      this.emit();
    },

    setRarity(value) {
      this.rarityMin = value;
      this.emit();
    },

    setQuery(q) {
      this.query = q;
      this.emit();
    },

    emit() {
      const detail = {
        activeTypes: Array.from(this.activeTypes),
        dateRange: this.dateRange,
        rarityMin: this.rarityMin,
        query: this.query,
      };
      window.dispatchEvent(new CustomEvent('filters:changed', { detail }));
    },
  });
});



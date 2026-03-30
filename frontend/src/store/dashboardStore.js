import { create } from 'zustand'

export const useDashboardStore = create((set, get) => ({
  // ── Country & Geography ──────────────────────────────────────────────────
  allCountries: [],          // [{country_code, country_name, continent, region, economy_type}]
  selectedCodes: [],         // currently selected country codes
  continentFilter: 'All',
  regionFilter: 'All',
  economyTypeFilter: 'All',

  // ── Time & Scale ─────────────────────────────────────────────────────────
  yearStart: 1991,
  yearEnd: 2028,
  logScale: false,
  normalize1991: false,

  // ── Chart Visual ─────────────────────────────────────────────────────────
  showCI: true,
  showProjections: true,
  showLowess: false,
  showRecession: false,
  colorBy: 'country',
  plotlyTheme: 'plotly_dark',

  // ── Growth sub-panel ─────────────────────────────────────────────────────
  showGrowthPanel: false,
  cagrPeriod: '5yr',

  // ── Data ─────────────────────────────────────────────────────────────────
  historical: [],    // [{country_code, year, value}]
  predictions: [],   // [{country_code, year, value, ci_lower, ci_upper, is_baseline}]
  loading: false,
  error: null,

  // ── Agent panel ───────────────────────────────────────────────────────────
  agentOpen: false,

  // ── Actions ──────────────────────────────────────────────────────────────
  setFilter: (key, value) => set({ [key]: value }),

  toggleCountry: (code) => {
    const { selectedCodes } = get()
    const next = selectedCodes.includes(code)
      ? selectedCodes.filter(c => c !== code)
      : [...selectedCodes, code]
    set({ selectedCodes: next })
    get().loadData(next)
  },

  setSelectedCodes: (codes) => {
    set({ selectedCodes: codes })
    get().loadData(codes)
  },

  loadCountries: async () => {
    try {
      const res = await fetch('/api/countries')
      const data = await res.json()
      const initial = data.slice(0, 6).map(c => c.country_code)
      set({ allCountries: data, selectedCodes: initial })
      get().loadData(initial)
    } catch (e) {
      set({ error: 'Failed to load countries' })
    }
  },

  loadData: async (codes) => {
    if (!codes || codes.length === 0) {
      set({ historical: [], predictions: [] })
      return
    }
    set({ loading: true, error: null })
    try {
      const res = await fetch(`/api/predictions?countries=${codes.join(',')}`)
      const data = await res.json()
      set({ historical: data.historical, predictions: data.predictions, loading: false })
    } catch (e) {
      set({ loading: false, error: 'Failed to load data' })
    }
  },
}))

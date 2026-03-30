// Vite-safe Plotly component using the pre-built dist bundle
import Plotly from 'plotly.js-dist-min'
import _factory from 'react-plotly.js/factory'

const createPlotlyComponent = _factory.default ?? _factory
const Plot = createPlotlyComponent(Plotly)
export default Plot

import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import HomePage from './pages/HomePage'
import DashboardPage from './pages/DashboardPage'
import ModelPage from './pages/ModelPage'
import AboutPage from './pages/AboutPage'

function Navbar() {
  const linkClass = ({ isActive }) =>
    `px-4 py-2 text-sm font-medium rounded transition-colors duration-150 ${
      isActive
        ? 'text-[#00d4ff] bg-[#00d4ff]/10 border border-[#00d4ff]/30'
        : 'text-gray-400 hover:text-gray-100 hover:bg-white/5'
    }`

  return (
    <nav className="sticky top-0 z-50 border-b border-white/10 bg-[#0d1117]/90 backdrop-blur-sm">
      <div className="px-8 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[#00d4ff] font-bold tracking-wide text-sm font-mono">
            GDP<span className="text-white/40">·</span>FORECAST
          </span>
        </div>
        <div className="flex items-center gap-6">
          <NavLink to="/" end className={linkClass}>Home</NavLink>
          <NavLink to="/dashboard" className={linkClass}>Dashboard</NavLink>
          <NavLink to="/model" className={linkClass}>Model</NavLink>
          <NavLink to="/about" className={linkClass}>About</NavLink>
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen bg-[#0d1117]">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/model" element={<ModelPage />} />
            <Route path="/about" element={<AboutPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

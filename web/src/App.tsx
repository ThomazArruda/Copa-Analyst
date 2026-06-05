import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import JogosDodia from './pages/JogosDodia'
import AnaliseCompleta from './pages/AnaliseCompleta'
import Relatorio from './pages/Relatorio'
import Calibracao from './pages/Calibracao'
import AtualizarDados from './pages/AtualizarDados'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<JogosDodia />} />
        <Route path="/analise" element={<AnaliseCompleta />} />
        <Route path="/relatorio" element={<Relatorio />} />
        <Route path="/calibracao" element={<Calibracao />} />
        <Route path="/atualizar" element={<AtualizarDados />} />
      </Route>
    </Routes>
  )
}

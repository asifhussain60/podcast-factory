import { Route, Routes, Navigate } from 'react-router-dom'
import { BooksListPage } from './pages/BooksListPage'
import { EditorPage } from './pages/EditorPage'
import { CortexRobot } from './components/CortexRobot'

export function App() {
  return (
    <div className="h-full flex flex-col">
      <Routes>
        <Route path="/" element={<BooksListPage />} />
        <Route path="/books/:slug" element={<EditorPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <CortexRobot />
    </div>
  )
}

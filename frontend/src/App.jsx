import './index.css'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Landing     from './pages/Landing'
import Login       from './pages/Login'
import Chat        from './pages/Chat'
import Profile     from './pages/Profile'
import AuthCallback from './pages/AuthCallback'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"          element={<Landing />} />
        <Route path="/login"     element={<Login />} />
        <Route path="/chat"      element={<Chat />} />
        <Route path="/profile"   element={<Profile />} />
        <Route path="/callback"  element={<AuthCallback />} />
        <Route path="*"          element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

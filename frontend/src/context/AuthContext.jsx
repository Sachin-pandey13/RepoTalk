import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext(null)

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchMe = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/auth/me`, { credentials: 'include' })
      if (resp.ok) {
        const data = await resp.json()
        setUser(data)
      } else {
        setUser(null)
      }
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMe()
  }, [fetchMe])

  const logout = async () => {
    await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' })
    setUser(null)
  }

  const loginWithGithub = () => {
    window.location.href = `${API}/auth/github`
  }

  const loginWithGoogle = () => {
    window.location.href = `${API}/auth/google`
  }

  return (
    <AuthContext.Provider value={{ user, loading, logout, loginWithGithub, loginWithGoogle, refetch: fetchMe }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}

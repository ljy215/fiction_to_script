import { createContext, useContext, useEffect, useMemo, useState } from 'react'

import { fetchCurrentUser } from '../api/auth'

const TOKEN_STORAGE_KEY = 'fiction_to_script_token'
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(token))

  function setToken(nextToken) {
    setTokenState(nextToken)
    if (nextToken) {
      localStorage.setItem(TOKEN_STORAGE_KEY, nextToken)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      setUser(null)
    }
  }

  function logout() {
    setToken(null)
  }

  useEffect(() => {
    let ignore = false

    async function loadUser() {
      if (!token) {
        setLoading(false)
        return
      }

      setLoading(true)
      try {
        const currentUser = await fetchCurrentUser(token)
        if (!ignore) {
          setUser(currentUser)
        }
      } catch {
        if (!ignore) {
          setToken(null)
        }
      } finally {
        if (!ignore) {
          setLoading(false)
        }
      }
    }

    loadUser()

    return () => {
      ignore = true
    }
  }, [token])

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      isAuthenticated: Boolean(token),
      setToken,
      logout
    }),
    [token, user, loading]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

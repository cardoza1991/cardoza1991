import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { authAPI } from '../api/client'

/**
 * AuthContext: caller can be:
 *   - Loading (`session === null` while fetching /me on boot)
 *   - Anonymous (`session.anonymous === true`)  — allowed when require_auth=false
 *   - Authenticated (`session.user` is set)
 *   - Unauthenticated + require_auth=true → LoginPage shown by the route shell
 */
const AuthContext = createContext({
  session: null,
  loading: true,
  login: async () => {},
  logout: () => {},
})

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const { data } = await authAPI.me()
      setSession(data)
    } catch (err) {
      // 401 with no token in demo mode is fine — me() returns anonymous instead,
      // so reaching this branch generally means the backend is unreachable.
      setSession({ anonymous: true, require_auth: false, error: err?.message })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  // Listen for the soft 401 event from the axios interceptor.
  useEffect(() => {
    const handler = () => { authAPI.logout(); refresh() }
    window.addEventListener('aerorisk:auth-expired', handler)
    return () => window.removeEventListener('aerorisk:auth-expired', handler)
  }, [refresh])

  const login = useCallback(async (email, password) => {
    const { data } = await authAPI.login(email, password)
    authAPI.setToken(data.token)
    await refresh()
    return data
  }, [refresh])

  const logout = useCallback(() => {
    authAPI.logout()
    refresh()
  }, [refresh])

  return (
    <AuthContext.Provider value={{ session, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

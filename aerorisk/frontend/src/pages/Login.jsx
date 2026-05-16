import { useState } from 'react'
import { Shield, LogIn, AlertCircle } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState('admin@aerorisk.ai')
  const [password, setPassword] = useState('demo1234')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const onSubmit = async (e) => {
    e.preventDefault()
    setError(null); setBusy(true)
    try { await login(email, password) }
    catch (err) { setError(err?.response?.data?.detail || 'login failed') }
    finally { setBusy(false) }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center gap-2.5 mb-2">
            <div className="p-2 bg-sky-500/10 border border-sky-500/30 rounded-lg">
              <Shield size={20} className="text-sky-400" />
            </div>
            <div className="text-left">
              <div className="font-bold text-slate-100">AeroRisk AI</div>
              <div className="text-[10px] text-slate-500 -mt-0.5 uppercase tracking-widest">Supply Chain Intelligence</div>
            </div>
          </div>
        </div>
        <form onSubmit={onSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <h1 className="text-lg font-semibold text-slate-100">Sign in</h1>
          <div>
            <label className="text-xs text-slate-400 uppercase tracking-wider block mb-1">Email</label>
            <input
              type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
              autoFocus
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 uppercase tracking-wider block mb-1">Password</label>
            <input
              type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
            />
          </div>
          {error && (
            <div className="flex items-start gap-2 text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded p-2">
              <AlertCircle size={12} className="mt-0.5" />
              <span>{error}</span>
            </div>
          )}
          <button
            type="submit" disabled={busy}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/40 text-sky-200 rounded-lg text-sm font-semibold transition disabled:opacity-50"
          >
            <LogIn size={14} />
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <div className="text-center text-[10px] text-slate-500">
          Demo credentials prefilled. Rotate the password and JWT secret in any real deployment.
        </div>
      </div>
    </div>
  )
}

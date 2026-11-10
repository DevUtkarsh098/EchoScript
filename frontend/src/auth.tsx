import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { isMockAuthEnabled } from './auth-config'

const mockAuth = isMockAuthEnabled(import.meta.env.VITE_APP_ENV, import.meta.env.VITE_MOCK_AUTH)
const domain = import.meta.env.VITE_COGNITO_DOMAIN || ''
const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID || ''
const redirectUri = import.meta.env.VITE_COGNITO_REDIRECT_URI || `${window.location.origin}/auth/callback`
const scope = import.meta.env.VITE_COGNITO_SCOPE || 'openid email profile'
let accessToken = ''

function base64Url(bytes: Uint8Array) {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}
async function sha256(value: string) { return new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))) }

export async function beginLogin(signUp = false) {
  if (mockAuth) { window.location.assign('/dashboard'); return }
  if (!domain || !clientId) throw new Error('Cognito environment configuration is incomplete')
  const verifier = base64Url(crypto.getRandomValues(new Uint8Array(48)))
  const state = base64Url(crypto.getRandomValues(new Uint8Array(24)))
  sessionStorage.setItem('echoscript.pkce.verifier', verifier)
  sessionStorage.setItem('echoscript.oauth.state', state)
  const parameters = new URLSearchParams({ client_id: clientId, response_type: 'code', scope, redirect_uri: redirectUri, state, code_challenge_method: 'S256', code_challenge: base64Url(await sha256(verifier)) })
  window.location.assign(`${domain}/${signUp ? 'signup' : 'oauth2/authorize'}?${parameters}`)
}

async function completeLogin() {
  const parameters = new URLSearchParams(window.location.search)
  const code = parameters.get('code')
  const returnedState = parameters.get('state')
  const expectedState = sessionStorage.getItem('echoscript.oauth.state')
  const verifier = sessionStorage.getItem('echoscript.pkce.verifier')
  if (!code || !verifier || !expectedState || returnedState !== expectedState) throw new Error('The authentication response could not be validated')
  const body = new URLSearchParams({ grant_type: 'authorization_code', client_id: clientId, code, redirect_uri: redirectUri, code_verifier: verifier })
  const response = await fetch(`${domain}/oauth2/token`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body })
  if (!response.ok) throw new Error('Cognito token exchange failed')
  const tokens = await response.json() as { access_token: string }
  accessToken = tokens.access_token
  sessionStorage.removeItem('echoscript.oauth.state')
  sessionStorage.removeItem('echoscript.pkce.verifier')
}

export function bearerToken() { return accessToken }

export function AuthGate({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const [state, setState] = useState<'ready' | 'loading' | 'error'>(mockAuth ? 'ready' : 'loading')
  useEffect(() => {
    if (mockAuth) return
    if (location.pathname === '/auth/callback') {
      setState('loading')
      completeLogin().then(() => window.location.replace('/dashboard')).catch(() => setState('error'))
      return
    }
    if (location.pathname === '/') { setState('ready'); return }
    if (!accessToken) { setState('loading'); beginLogin().catch(() => setState('error')) }
    else setState('ready')
  }, [location.pathname])
  if (state === 'loading') return <div className="center-page"><h1>Securely signing you in…</h1><p>Completing the Cognito authorization flow.</p></div>
  if (state === 'error') return <div className="center-page"><h1>Session could not be started</h1><p>Return to the welcome page and try again.</p><a className="button primary" href="/">Return home</a></div>
  return children
}


import { describe, expect, it } from 'vitest'
import { isMockAuthEnabled } from './auth-config'

describe('mock authentication configuration', () => {
  it('fails closed when environment settings are missing', () => {
    expect(isMockAuthEnabled(undefined, undefined)).toBe(false)
  })

  it('does not allow mock auth outside local mode', () => {
    expect(isMockAuthEnabled('production', 'true')).toBe(false)
  })

  it('allows mock auth only when local mode is explicitly selected', () => {
    expect(isMockAuthEnabled('local', 'true')).toBe(true)
    expect(isMockAuthEnabled('local', 'false')).toBe(false)
  })
})

export function isMockAuthEnabled(appEnvironment: string | undefined, mockAuthSetting: string | undefined): boolean {
  return appEnvironment === 'local' && mockAuthSetting === 'true'
}

const sandboxCheckout = import.meta.env.VITE_ENABLE_SANDBOX_CHECKOUT === 'true'
const mockCheckout = import.meta.env.VITE_ENABLE_MOCK_CHECKOUT === 'true'

export const checkoutMode = sandboxCheckout && mockCheckout ? null
  : sandboxCheckout ? 'sandbox'
    : import.meta.env.DEV && mockCheckout ? 'mock' : null

const checkoutPackageId = Number(import.meta.env.VITE_SANDBOX_PACKAGE_ID)

export function packageSupportsCheckout(packageId) {
  return checkoutMode !== null && Number.isSafeInteger(packageId) &&
    packageId > 0 && packageId === checkoutPackageId
}

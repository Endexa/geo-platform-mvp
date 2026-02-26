/**
 * Composable for Stripe Checkout and Customer Portal redirects.
 *
 * Uses useApiFetch for authenticated API calls and redirects the browser
 * to Stripe-hosted pages (Checkout or Portal).
 */
export const useStripe = () => {
  /**
   * Create a Checkout Session and redirect to Stripe Checkout.
   *
   * @param priceId - Stripe price ID (price_xxx)
   */
  const redirectToCheckout = async (priceId: string) => {
    const data = await useApiFetch<{ checkout_url: string; session_id: string }>(
      '/payments/create-checkout',
      {
        method: 'POST',
        body: { price_id: priceId },
      }
    )
    if (data.checkout_url) {
      window.location.href = data.checkout_url
    }
  }

  /**
   * Create a Customer Portal session and redirect to Stripe Portal.
   */
  const redirectToPortal = async () => {
    const data = await useApiFetch<{ portal_url: string }>(
      '/payments/create-portal',
      {
        method: 'POST',
      }
    )
    if (data.portal_url) {
      window.location.href = data.portal_url
    }
  }

  return { redirectToCheckout, redirectToPortal }
}

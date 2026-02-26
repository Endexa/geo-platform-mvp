/**
 * Composable for tracking user subscription tier.
 *
 * Derives tier from audit response data (is_limited field) to avoid
 * needing a dedicated subscription status endpoint.
 */
export const useSubscription = () => {
  const tier = useState<string>('subscription_tier', () => 'free')
  const isProUser = computed(() => tier.value === 'pro')

  /**
   * Update tier based on audit detail response.
   * If is_limited is false, the user has a pro subscription.
   */
  const updateTierFromAudit = (auditResponse: { is_limited?: boolean }) => {
    if (auditResponse && auditResponse.is_limited === false) {
      tier.value = 'pro'
    } else {
      tier.value = 'free'
    }
  }

  /**
   * Explicitly set the tier (e.g. after successful checkout).
   */
  const setTier = (newTier: 'free' | 'pro') => {
    tier.value = newTier
  }

  return { tier, isProUser, updateTierFromAudit, setTier }
}

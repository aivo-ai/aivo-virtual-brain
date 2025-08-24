import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

// Types
export interface Plan {
  id: string
  name: string
  description: string
  price: number
  originalPrice?: number
  currency: string
  interval: 'month' | 'year'
  features: string[]
  popular?: boolean
  trialDays?: number
  stripePriceId: string
}

export interface Subscription {
  id: string
  planId: string
  planName?: string
  status:
    | 'active'
    | 'trialing'
    | 'past_due'
    | 'canceled'
    | 'unpaid'
    | 'incomplete'
  amount?: number
  currency?: string
  interval?: string
  currentPeriodStart: string
  currentPeriodEnd: string
  nextBillingDate?: string
  cancelAtPeriodEnd: boolean
  trialEnd?: string
  customerId: string
  paymentMethodId?: string
}

export interface PaymentMethod {
  id: string
  type: 'card'
  brand: string
  last4: string
  expiryMonth: number
  expiryYear: number
  // Legacy nested structure for backward compatibility
  card?: {
    brand: string
    last4: string
    expMonth: number
    expYear: number
  }
  isDefault?: boolean
}

export interface Invoice {
  id: string
  amount: number
  currency: string
  status: 'paid' | 'open' | 'void' | 'uncollectible' | 'failed'
  dueDate: string
  createdAt: string
  date?: string
  hostedInvoiceUrl?: string
  downloadUrl?: string
  invoicePdf?: string
}

export interface BillingInfo {
  subscription?: Subscription
  paymentMethod?: PaymentMethod
  paymentMethods: PaymentMethod[]
  upcomingInvoice?: Invoice
  recentInvoices: Invoice[]
  invoices?: Invoice[]
  studentCount?: number
  customer: {
    id: string
    email: string
    name?: string
    balance: number
  }
}

export interface CheckoutSession {
  id: string
  url: string
  status: 'open' | 'complete' | 'expired'
}

export interface DunningState {
  status:
    | 'payment_failed'
    | 'past_due'
    | 'subscription_canceled'
    | 'grace_period'
  lastFailedAt?: string
  gracePeriodEnds?: string
  attemptCount: number
  nextRetryAt?: string
  message?: string
  severity?: 'info' | 'warning' | 'error'
  // Legacy fields for backward compatibility
  isInGracePeriod?: boolean
  gracePeriodEnd?: string
  isDunning?: boolean
  nextAttemptDate?: string
  finalAttemptDate?: string
}

// Mock data for development
const mockPlans: Plan[] = [
  {
    id: 'basic',
    name: 'Basic',
    description: 'Perfect for individuals',
    price: 19,
    currency: 'USD',
    interval: 'month',
    features: [
      'Up to 3 students',
      'Basic analytics',
      'Standard support',
      'Core learning modules',
    ],
    trialDays: 14,
    stripePriceId: 'price_basic_monthly',
  },
  {
    id: 'pro',
    name: 'Professional',
    description: 'Best for small teams',
    price: 49,
    originalPrice: 59,
    currency: 'USD',
    interval: 'month',
    features: [
      'Up to 15 students',
      'Advanced analytics',
      'Priority support',
      'All learning modules',
      'Custom assessments',
      'Parent portal',
    ],
    popular: true,
    trialDays: 14,
    stripePriceId: 'price_pro_monthly',
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    description: 'For schools and districts',
    price: 149,
    currency: 'USD',
    interval: 'month',
    features: [
      'Unlimited students',
      'Real-time analytics',
      'Dedicated support',
      'All modules + custom content',
      'API access',
      'SSO integration',
      'Advanced reporting',
      'White-label options',
    ],
    trialDays: 30,
    stripePriceId: 'price_enterprise_monthly',
  },
]

const mockBillingInfo: BillingInfo = {
  subscription: {
    id: 'sub_123',
    planId: 'pro',
    planName: 'Pro',
    status: 'active',
    amount: 29.99,
    currency: 'USD',
    interval: 'month',
    currentPeriodStart: '2025-07-17T00:00:00Z',
    currentPeriodEnd: '2025-08-17T00:00:00Z',
    nextBillingDate: '2025-08-17T00:00:00Z',
    cancelAtPeriodEnd: false,
    customerId: 'cus_123',
    paymentMethodId: 'pm_123',
  },
  paymentMethod: {
    id: 'pm_123',
    type: 'card',
    brand: 'visa',
    last4: '4242',
    expiryMonth: 12,
    expiryYear: 2025,
    isDefault: true,
  },
  paymentMethods: [
    {
      id: 'pm_123',
      type: 'card',
      brand: 'visa',
      last4: '4242',
      expiryMonth: 12,
      expiryYear: 2025,
      isDefault: true,
    },
  ],
  upcomingInvoice: {
    id: 'in_upcoming',
    amount: 4900,
    currency: 'USD',
    status: 'open',
    dueDate: '2025-08-17T00:00:00Z',
    createdAt: '2025-07-17T00:00:00Z',
  },
  invoices: [
    {
      id: 'in_123',
      amount: 2999,
      currency: 'USD',
      status: 'paid',
      dueDate: '2025-07-17T00:00:00Z',
      createdAt: '2025-06-17T00:00:00Z',
      hostedInvoiceUrl: 'https://invoice.stripe.com/i/123',
      downloadUrl: 'https://invoice.stripe.com/i/123/pdf',
    },
  ],
  recentInvoices: [
    {
      id: 'in_123',
      amount: 4900,
      currency: 'USD',
      status: 'paid',
      dueDate: '2025-07-17T00:00:00Z',
      createdAt: '2025-06-17T00:00:00Z',
      hostedInvoiceUrl: 'https://invoice.stripe.com/i/123',
    },
  ],
  studentCount: 2,
  customer: {
    id: 'cus_123',
    email: 'user@example.com',
    name: 'John Doe',
    balance: 0,
  },
}

// Remove unused API_BASE to avoid linting warning
// const API_BASE = '/api/billing';

// Sibling discount calculation
export const calculateSiblingDiscount = (studentCount: number): number => {
  if (studentCount <= 1) return 0
  if (studentCount === 2) return 0.1 // 10% for 2 students
  if (studentCount === 3) return 0.15 // 15% for 3 students
  if (studentCount >= 4) return 0.2 // 20% for 4+ students
  return 0
}

// Format price with currency
export const formatPrice = (
  amount: number,
  currency: string = 'USD'
): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount)
}

// Get plans with sibling discounts applied
export const getPlansWithDiscounts = (
  plans: Plan[],
  studentCount: number = 1
): Plan[] => {
  const discount = calculateSiblingDiscount(studentCount)

  return plans.map(plan => ({
    ...plan,
    originalPrice: discount > 0 ? plan.price : undefined,
    price: Math.round(plan.price * (1 - discount)),
  }))
}

// React Query Hooks

// Get available plans
export const usePlans = (studentCount: number = 1) => {
  return useQuery<Plan[]>({
    queryKey: ['plans', studentCount],
    queryFn: async (): Promise<Plan[]> => {
      // In production, this would be a real API call
      // const response = await fetch(`${API_BASE}/plans?students=${studentCount}`);
      // return response.json();

      // Mock implementation
      return new Promise(resolve => {
        setTimeout(() => {
          resolve(getPlansWithDiscounts(mockPlans, studentCount))
        }, 500)
      })
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

// Get billing information
export const useBillingInfo = () => {
  return useQuery<BillingInfo>({
    queryKey: ['billing-info'],
    queryFn: async (): Promise<BillingInfo> => {
      // const response = await fetch(`${API_BASE}/info`);
      // return response.json();

      return new Promise(resolve => {
        setTimeout(() => {
          resolve(mockBillingInfo)
        }, 800)
      })
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  })
}

// Get dunning state
export const useDunningState = () => {
  return useQuery<DunningState>({
    queryKey: ['dunning-state'],
    queryFn: async (): Promise<DunningState> => {
      // const response = await fetch(`${API_BASE}/dunning`);
      // return response.json();

      // Mock dunning state (simulating different scenarios)
      const scenarios = [
        {
          status: 'grace_period' as const,
          isInGracePeriod: false,
          isDunning: false,
          attemptCount: 0,
          message: 'Your subscription is active.',
          severity: 'info' as const,
        },
        {
          status: 'payment_failed' as const,
          lastFailedAt: new Date(
            Date.now() - 24 * 60 * 60 * 1000
          ).toISOString(),
          gracePeriodEnds: '2025-08-24T00:00:00Z',
          isInGracePeriod: true,
          gracePeriodEnd: '2025-08-24T00:00:00Z',
          isDunning: true,
          attemptCount: 1,
          nextRetryAt: '2025-08-20T00:00:00Z',
          nextAttemptDate: '2025-08-20T00:00:00Z',
          message:
            "Payment failed. We'll retry in 3 days. Update your payment method to avoid service interruption.",
          severity: 'warning' as const,
        },
        {
          status: 'past_due' as const,
          lastFailedAt: new Date(
            Date.now() - 3 * 24 * 60 * 60 * 1000
          ).toISOString(),
          gracePeriodEnds: '2025-08-19T00:00:00Z',
          isInGracePeriod: true,
          gracePeriodEnd: '2025-08-19T00:00:00Z',
          isDunning: true,
          attemptCount: 3,
          nextRetryAt: '2025-08-19T00:00:00Z',
          finalAttemptDate: '2025-08-19T00:00:00Z',
          message:
            'Final payment attempt will be made on Aug 19. Please update your payment method immediately.',
          severity: 'error' as const,
        },
      ]

      return new Promise(resolve => {
        setTimeout(() => {
          // Randomly select a scenario for demo
          const scenario =
            scenarios[Math.floor(Math.random() * scenarios.length)]
          resolve(scenario)
        }, 300)
      })
    },
    staleTime: 1 * 60 * 1000, // 1 minute
    refetchInterval: 2 * 60 * 1000, // 2 minutes
  })
}

// Create checkout session
export const useCreateCheckout = () => {
  const queryClient = useQueryClient()

  return useMutation<
    CheckoutSession,
    Error,
    { planId: string; studentCount?: number }
  >({
    mutationFn: async ({
      planId,
      studentCount = 1,
    }): Promise<CheckoutSession> => {
      // Use parameters to avoid linting errors
      console.log(
        'Creating checkout for plan:',
        planId,
        'students:',
        studentCount
      )

      // const response = await fetch(`${API_BASE}/checkout`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ planId, studentCount })
      // });
      // return response.json();

      // Mock implementation
      return new Promise(resolve => {
        setTimeout(() => {
          resolve({
            id: `cs_${Date.now()}`,
            url: `https://checkout.stripe.com/c/pay/cs_test_${Date.now()}`,
            status: 'open',
          })
        }, 1000)
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing-info'] })
    },
  })
}

// Cancel subscription
export const useCancelSubscription = () => {
  const queryClient = useQueryClient()

  return useMutation<void, Error, { immediate?: boolean }>({
    mutationFn: async ({ immediate = false }): Promise<void> => {
      // Use parameter to avoid linting errors
      console.log('Canceling subscription with immediate:', immediate)

      // const response = await fetch(`${API_BASE}/subscription/cancel`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ immediate })
      // });
      // if (!response.ok) throw new Error('Failed to cancel subscription');

      // Mock implementation
      return new Promise(resolve => {
        setTimeout(() => {
          resolve()
        }, 800)
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing-info'] })
    },
  })
}

// Reactivate subscription
export const useReactivateSubscription = () => {
  const queryClient = useQueryClient()

  return useMutation<void, Error, void>({
    mutationFn: async (): Promise<void> => {
      // const response = await fetch(`${API_BASE}/subscription/reactivate`, {
      //   method: 'POST'
      // });
      // if (!response.ok) throw new Error('Failed to reactivate subscription');

      return new Promise(resolve => {
        setTimeout(() => {
          resolve()
        }, 800)
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing-info'] })
    },
  })
}

// Update payment method
export const useUpdatePaymentMethod = () => {
  const queryClient = useQueryClient()

  return useMutation<{ url: string }, Error, void>({
    mutationFn: async (): Promise<{ url: string }> => {
      // const response = await fetch(`${API_BASE}/payment-method/update`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' }
      // });
      // return response.json();

      // Mock implementation - return Stripe billing portal URL
      return new Promise(resolve => {
        setTimeout(() => {
          resolve({
            url: `https://billing.stripe.com/session/mock_${Date.now()}`,
          })
        }, 500)
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing-info'] })
      queryClient.invalidateQueries({ queryKey: ['dunning-state'] })
    },
  })
}

// Poll checkout status (for demo webhook simulation)
export const useCheckoutStatus = (sessionId: string | null) => {
  return useQuery<{
    status: string
    subscriptionId?: string
    planName?: string
    amount?: number
    nextBilling?: string
  }>({
    queryKey: ['checkout-status', sessionId],
    queryFn: async () => {
      if (!sessionId) throw new Error('No session ID')

      // const response = await fetch(`${API_BASE}/checkout/${sessionId}/status`);
      // return response.json();

      // Mock implementation - simulate successful payment after delay
      return new Promise(resolve => {
        setTimeout(() => {
          resolve({
            status: Math.random() > 0.3 ? 'complete' : 'processing',
            subscriptionId: 'sub_new_123',
            planName: 'Pro Plan',
            amount: 29.99,
            nextBilling: new Date(
              Date.now() + 30 * 24 * 60 * 60 * 1000
            ).toISOString(),
          })
        }, 2000)
      })
    },
    enabled: !!sessionId,
    refetchInterval: 3000, // Poll every 3 seconds until complete
    staleTime: 0,
  })
}

// Get invoice PDF
export const downloadInvoice = async (invoiceId: string): Promise<void> => {
  // const response = await fetch(`${API_BASE}/invoices/${invoiceId}/pdf`);
  // const blob = await response.blob();
  // const url = window.URL.createObjectURL(blob);
  // const a = document.createElement('a');
  // a.href = url;
  // a.download = `invoice-${invoiceId}.pdf`;
  // a.click();
  // window.URL.revokeObjectURL(url);

  // Mock implementation
  console.log(`Downloading invoice ${invoiceId}...`)
  alert('Invoice download would start here (mock implementation)')
}

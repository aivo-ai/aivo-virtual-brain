import { PlanSelection } from '../hooks/useOnboarding'

const API_BASE = process.env.VITE_API_BASE_URL || '/api'

export interface PaymentPlan {
  id: string
  name: string
  type: 'trial' | 'monthly' | 'quarterly' | 'half-year' | 'yearly'
  price: number
  currency: 'USD'
  billingCycle: number // days
  features: string[]
  isActive: boolean
}

export interface Subscription {
  id: string
  userId: string
  planId: string
  status: 'active' | 'trial' | 'cancelled' | 'expired' | 'pending'
  startDate: string
  endDate?: string
  trialEndDate?: string
  autoRenew: boolean
  learnerCount: number
  discountPercent?: number
  totalPrice: number
  nextBillingDate?: string
  createdAt: string
  updatedAt: string
}

export interface PaymentMethod {
  id: string
  userId: string
  type: 'card' | 'bank' | 'paypal'
  last4?: string
  brand?: string
  expiryMonth?: number
  expiryYear?: number
  isDefault: boolean
  createdAt: string
}

export interface CreateSubscriptionRequest {
  userId: string
  planType: PlanSelection['planType']
  learnerCount: number
  paymentMethodId?: string
  startTrial?: boolean
  tenantId?: string
}

export interface UpdateSubscriptionRequest {
  subscriptionId: string
  planType?: PlanSelection['planType']
  learnerCount?: number
  autoRenew?: boolean
}

export interface PaymentIntent {
  id: string
  clientSecret: string
  amount: number
  currency: string
  status:
    | 'requires_payment_method'
    | 'requires_confirmation'
    | 'succeeded'
    | 'canceled'
}

class PaymentClient {
  async getAvailablePlans(): Promise<PaymentPlan[]> {
    const response = await fetch(`${API_BASE}/payment-svc/plans`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to get plans: ${response.statusText}`)
    }

    return response.json()
  }

  async getPlan(planId: string): Promise<PaymentPlan> {
    const response = await fetch(`${API_BASE}/payment-svc/plans/${planId}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to get plan: ${response.statusText}`)
    }

    return response.json()
  }

  async createSubscription(
    subscriptionData: CreateSubscriptionRequest
  ): Promise<Subscription> {
    const response = await fetch(`${API_BASE}/payment-svc/subscriptions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(subscriptionData),
    })

    if (!response.ok) {
      throw new Error(`Failed to create subscription: ${response.statusText}`)
    }

    return response.json()
  }

  async updateSubscription(
    subscriptionData: UpdateSubscriptionRequest
  ): Promise<Subscription> {
    const response = await fetch(
      `${API_BASE}/payment-svc/subscriptions/${subscriptionData.subscriptionId}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(subscriptionData),
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to update subscription: ${response.statusText}`)
    }

    return response.json()
  }

  async getSubscription(subscriptionId: string): Promise<Subscription> {
    const response = await fetch(
      `${API_BASE}/payment-svc/subscriptions/${subscriptionId}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to get subscription: ${response.statusText}`)
    }

    return response.json()
  }

  async getUserSubscriptions(userId: string): Promise<Subscription[]> {
    const response = await fetch(
      `${API_BASE}/payment-svc/subscriptions?userId=${userId}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(
        `Failed to get user subscriptions: ${response.statusText}`
      )
    }

    return response.json()
  }

  async cancelSubscription(subscriptionId: string): Promise<Subscription> {
    const response = await fetch(
      `${API_BASE}/payment-svc/subscriptions/${subscriptionId}/cancel`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to cancel subscription: ${response.statusText}`)
    }

    return response.json()
  }

  async startTrial(
    userId: string,
    learnerCount: number
  ): Promise<Subscription> {
    return this.createSubscription({
      userId,
      planType: 'trial',
      learnerCount,
      startTrial: true,
    })
  }

  async createPaymentIntent(
    amount: number,
    currency: string = 'USD'
  ): Promise<PaymentIntent> {
    const response = await fetch(`${API_BASE}/payment-svc/payment-intents`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({ amount, currency }),
    })

    if (!response.ok) {
      throw new Error(`Failed to create payment intent: ${response.statusText}`)
    }

    return response.json()
  }

  async addPaymentMethod(
    userId: string,
    paymentMethodData: any
  ): Promise<PaymentMethod> {
    const response = await fetch(`${API_BASE}/payment-svc/payment-methods`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({ userId, ...paymentMethodData }),
    })

    if (!response.ok) {
      throw new Error(`Failed to add payment method: ${response.statusText}`)
    }

    return response.json()
  }

  async getPaymentMethods(userId: string): Promise<PaymentMethod[]> {
    const response = await fetch(
      `${API_BASE}/payment-svc/payment-methods?userId=${userId}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to get payment methods: ${response.statusText}`)
    }

    return response.json()
  }

  // Pricing calculation utilities
  calculatePlanPrice(
    planType: PlanSelection['planType'],
    learnerCount: number,
    siblingDiscount: boolean = true
  ): {
    originalPrice: number
    finalPrice: number
    discount: number
    discountPercent: number
  } {
    const basePrices = {
      trial: 0,
      monthly: 29.99,
      quarterly: 23.99, // 20% off monthly
      'half-year': 20.99, // 30% off monthly
      yearly: 14.99, // 50% off monthly
    }

    const originalPrice = basePrices[planType] * learnerCount
    let finalPrice = originalPrice
    let discountPercent = 0

    // Plan discounts are already built into the base prices
    if (planType === 'quarterly') discountPercent = 20
    if (planType === 'half-year') discountPercent = 30
    if (planType === 'yearly') discountPercent = 50

    // Sibling discount: 10% off for 2+ learners
    if (siblingDiscount && learnerCount >= 2) {
      finalPrice *= 0.9
      discountPercent = Math.max(discountPercent, 10)
    }

    return {
      originalPrice: basePrices.monthly * learnerCount, // Always show monthly as base
      finalPrice,
      discount: basePrices.monthly * learnerCount - finalPrice,
      discountPercent: Math.round(
        ((basePrices.monthly * learnerCount - finalPrice) /
          (basePrices.monthly * learnerCount)) *
          100
      ),
    }
  }

  getTrialDuration(): number {
    return 14 // 14-day trial
  }
}

export const paymentClient = new PaymentClient()

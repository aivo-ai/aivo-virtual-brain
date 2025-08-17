import React, { useState } from 'react';
import { 
  useBillingInfo, 
  useDunningState, 
  useCancelSubscription, 
  useReactivateSubscription,
  useUpdatePaymentMethod,
  formatPrice 
} from '../../api/paymentsClient';
import { DunningBanner } from '../../components/billing/DunningBanner';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { 
  CreditCard, 
  Calendar, 
  AlertTriangle, 
  CheckCircle, 
  Users,
  Settings,
  Download
} from '../../components/ui/Icons';

export const Manage: React.FC = () => {
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  // API hooks
  const { data: billingInfo, refetch: refetchBilling } = useBillingInfo();
  const { data: dunningState } = useDunningState();
  const cancelSubscription = useCancelSubscription();
  const reactivateSubscription = useReactivateSubscription();
  const updatePaymentMethod = useUpdatePaymentMethod();

  const subscription = billingInfo?.subscription;
  const paymentMethod = billingInfo?.paymentMethod;

  const handleCancelSubscription = async () => {
    if (!subscription?.id) return;
    
    try {
      await cancelSubscription.mutateAsync({ immediate: false });
      await refetchBilling();
      setShowCancelConfirm(false);
    } catch (error) {
      console.error('Failed to cancel subscription:', error);
    }
  };

  const handleReactivateSubscription = async () => {
    if (!subscription?.id) return;
    
    try {
      await reactivateSubscription.mutateAsync();
      await refetchBilling();
    } catch (error) {
      console.error('Failed to reactivate subscription:', error);
    }
  };

  const handleUpdatePaymentMethod = async () => {
    try {
      const updateData = await updatePaymentMethod.mutateAsync();
      // Redirect to payment update session
      window.location.href = updateData.url;
    } catch (error) {
      console.error('Failed to update payment method:', error);
    }
  };

  const handleContactSupport = () => {
    window.open('mailto:support@aivo.com', '_blank');
  };

  if (!billingInfo) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const isActive = subscription?.status === 'active';
  const isCanceled = subscription?.status === 'canceled';
  const isPastDue = subscription?.status === 'past_due';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <h1 className="text-2xl font-bold text-gray-900">Billing Management</h1>
          <p className="text-gray-600 mt-1">Manage your subscription and payment details</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Dunning Banner */}
        {dunningState && (
          <DunningBanner
            dunningState={dunningState}
            onUpdatePayment={handleUpdatePaymentMethod}
            onRetryPayment={handleUpdatePaymentMethod}
            onContactSupport={handleContactSupport}
          />
        )}

        {/* Subscription Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              Current Subscription
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Plan:</span>
                    <span className="font-medium">{subscription?.planName || 'No active plan'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Status:</span>
                    <Badge 
                      variant={isActive ? 'success' : isCanceled ? 'danger' : isPastDue ? 'warning' : 'default'}
                    >
                      {subscription?.status || 'None'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Amount:</span>
                    <span className="font-medium">
                      {subscription && subscription.amount && subscription.currency 
                        ? formatPrice(subscription.amount, subscription.currency) 
                        : 'N/A'}
                      {subscription?.interval && `/${subscription.interval}`}
                    </span>
                  </div>
                  {subscription?.nextBillingDate && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-600">
                        {isCanceled ? 'Ends on:' : 'Next billing:'}
                      </span>
                      <span className="font-medium">
                        {new Date(subscription.nextBillingDate).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="space-y-3">
                {isActive && (
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => window.location.href = '/billing/plans'}
                  >
                    <Settings className="w-4 h-4 mr-2" />
                    Change Plan
                  </Button>
                )}
                
                {isCanceled ? (
                  <Button
                    onClick={handleReactivateSubscription}
                    className="w-full"
                    disabled={reactivateSubscription.isPending}
                  >
                    {reactivateSubscription.isPending ? 'Reactivating...' : 'Reactivate Subscription'}
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    className="w-full text-red-600 border-red-200 hover:bg-red-50"
                    onClick={() => setShowCancelConfirm(true)}
                  >
                    <AlertTriangle className="w-4 h-4 mr-2" />
                    Cancel Subscription
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Payment Method */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="w-5 h-5" />
              Payment Method
            </CardTitle>
          </CardHeader>
          <CardContent>
            {paymentMethod ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-6 bg-gray-100 rounded flex items-center justify-center text-xs font-medium">
                    {paymentMethod.brand.toUpperCase()}
                  </div>
                  <div>
                    <div className="font-medium">•••• •••• •••• {paymentMethod.last4}</div>
                    <div className="text-sm text-gray-500">
                      Expires {paymentMethod.expiryMonth}/{paymentMethod.expiryYear}
                    </div>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleUpdatePaymentMethod}
                  disabled={updatePaymentMethod.isPending}
                >
                  {updatePaymentMethod.isPending ? 'Updating...' : 'Update'}
                </Button>
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-gray-500 mb-4">No payment method on file</p>
                <Button onClick={handleUpdatePaymentMethod}>
                  Add Payment Method
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Usage & Students */}
        {billingInfo.studentCount && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                Account Usage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Students:</span>
                    <span className="font-medium">{billingInfo.studentCount}</span>
                  </div>
                  {billingInfo.studentCount > 1 && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-600">Sibling discount:</span>
                      <Badge variant="success">15% OFF</Badge>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Billing History */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5" />
              Recent Invoices
            </CardTitle>
          </CardHeader>
          <CardContent>
            {billingInfo.invoices && billingInfo.invoices.length > 0 ? (
              <div className="space-y-3">
                {billingInfo.invoices.slice(0, 5).map((invoice) => (
                  <div key={invoice.id} className="flex items-center justify-between py-2 border-b last:border-b-0">
                    <div>
                      <div className="font-medium">
                        {formatPrice(invoice.amount, invoice.currency)}
                      </div>
                      <div className="text-sm text-gray-500">
                        {invoice.date ? new Date(invoice.date).toLocaleDateString() : new Date(invoice.createdAt).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge 
                        variant={invoice.status === 'paid' ? 'success' : invoice.status === 'failed' ? 'danger' : 'warning'}
                      >
                        {invoice.status}
                      </Badge>
                      {invoice.downloadUrl && (
                        <Button variant="ghost" size="sm">
                          <Download className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
                <div className="pt-4">
                  <Button variant="outline" className="w-full">
                    View All Invoices
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">No invoices yet</p>
            )}
          </CardContent>
        </Card>

        {/* Support */}
        <Card>
          <CardHeader>
            <CardTitle>Need Help?</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 mb-4">
              If you have questions about your billing or need assistance, our support team is here to help.
            </p>
            <Button variant="outline" onClick={handleContactSupport}>
              Contact Support
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Cancel Confirmation Modal */}
      {showCancelConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <Card className="max-w-md w-full">
            <CardHeader>
              <CardTitle className="text-red-600">Cancel Subscription</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-6">
                Are you sure you want to cancel your subscription? You'll lose access to all premium features at the end of your current billing period.
              </p>
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowCancelConfirm(false)}
                >
                  Keep Subscription
                </Button>
                <Button
                  variant="outline"
                  className="flex-1 text-red-600 border-red-200 hover:bg-red-50"
                  onClick={handleCancelSubscription}
                  disabled={cancelSubscription.isPending}
                >
                  {cancelSubscription.isPending ? 'Canceling...' : 'Cancel'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default Manage;

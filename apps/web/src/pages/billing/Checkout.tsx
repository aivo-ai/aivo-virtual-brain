import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useCheckoutStatus } from '../../api/paymentsClient';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { CheckCircle, XCircle, Clock, AlertTriangle } from '../../components/ui/Icons';

export const Checkout: React.FC = () => {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'processing'>('loading');

  const { data: checkoutStatus, isLoading, error } = useCheckoutStatus(sessionId);

  useEffect(() => {
    if (isLoading) {
      setStatus('loading');
    } else if (error) {
      setStatus('error');
    } else if (checkoutStatus) {
      setStatus(checkoutStatus.status === 'complete' ? 'success' : 'processing');
    }
  }, [checkoutStatus, isLoading, error]);

  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-16 h-16 text-green-500" />;
      case 'error':
        return <XCircle className="w-16 h-16 text-red-500" />;
      case 'processing':
        return <Clock className="w-16 h-16 text-yellow-500" />;
      default:
        return <AlertTriangle className="w-16 h-16 text-gray-400" />;
    }
  };

  const getStatusMessage = () => {
    switch (status) {
      case 'success':
        return {
          title: 'Payment Successful!',
          message: 'Welcome to your new plan. You can start using all features immediately.',
          action: 'Go to Dashboard'
        };
      case 'error':
        return {
          title: 'Payment Failed',
          message: 'There was an issue processing your payment. Please try again or contact support.',
          action: 'Try Again'
        };
      case 'processing':
        return {
          title: 'Processing Payment',
          message: 'Your payment is being processed. This may take a few moments.',
          action: 'Check Status'
        };
      default:
        return {
          title: 'Checking Payment Status',
          message: 'Please wait while we verify your payment...',
          action: null
        };
    }
  };

  const handleAction = () => {
    switch (status) {
      case 'success':
        window.location.href = '/dashboard';
        break;
      case 'error':
        window.location.href = '/billing/plans';
        break;
      case 'processing':
        window.location.reload();
        break;
    }
  };

  const statusInfo = getStatusMessage();

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="max-w-md w-full">
        <CardHeader>
          <div className="flex flex-col items-center text-center">
            {getStatusIcon()}
            <CardTitle className="mt-4 text-xl">
              {statusInfo.title}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="text-center">
          <p className="text-gray-600 mb-6">
            {statusInfo.message}
          </p>

          {/* Show checkout details for success */}
          {status === 'success' && checkoutStatus && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
              <div className="text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-600">Plan:</span>
                  <span className="font-medium">{checkoutStatus.planName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Amount:</span>
                  <span className="font-medium">${checkoutStatus.amount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Next billing:</span>
                  <span className="font-medium">
                    {checkoutStatus.nextBilling ? new Date(checkoutStatus.nextBilling).toLocaleDateString() : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Show error details */}
          {status === 'error' && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-red-700">
                Error: {error?.message || 'Payment processing failed'}
              </p>
            </div>
          )}

          {/* Loading indicator */}
          {status === 'loading' && (
            <div className="flex justify-center mb-6">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          )}

          {/* Action button */}
          {statusInfo.action && (
            <Button
              onClick={handleAction}
              className="w-full"
              variant={status === 'success' ? 'primary' : status === 'error' ? 'outline' : 'outline'}
            >
              {statusInfo.action}
            </Button>
          )}

          {/* Support link */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-500">
              Need help?{' '}
              <a 
                href="mailto:support@aivo.com"
                className="text-blue-600 hover:text-blue-700 underline"
              >
                Contact Support
              </a>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Checkout;

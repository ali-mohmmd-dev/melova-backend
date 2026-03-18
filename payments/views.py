from django.shortcuts import render
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest
import razorpay
from shop.models import Payment
from rest_framework.views import APIView
from rest_framework.decorators import api_view


# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))

@api_view(['GET'])
def homepage(request):
    amount = 20000  # Rs. 200 in paise
    currency = 'INR'

    # Create Razorpay order
    razorpay_order = razorpay_client.order.create(
        dict(amount=amount, currency=currency, payment_capture='0')
    )
    
    # Save order in database
    Payment.objects.create(
        razorpay_order_id=razorpay_order['id'],
        amount=amount,
        status='Created'
    )

    context = {
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_merchant_key': settings.RAZOR_KEY_ID,
        'razorpay_amount': amount,
        'currency': currency,
        'callback_url': '/paymenthandler/'
    }
    return render(request, 'index.html', context)


@csrf_exempt
def paymenthandler(request):
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id', '')
        razorpay_order_id = request.POST.get('razorpay_order_id', '')
        signature = request.POST.get('razorpay_signature', '')

        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }

        try:
            # Verify payment signature
            razorpay_client.utility.verify_payment_signature(params_dict)
            
            # Capture payment
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            razorpay_client.payment.capture(payment_id, payment.amount)

            # Update payment record
            payment.razorpay_payment_id = payment_id
            payment.razorpay_signature = signature
            payment.status = 'Success'
            payment.save()

            return render(request, 'paymentsuccess.html')
        except razorpay.errors.SignatureVerificationError:
            # Update payment as failed
            Payment.objects.filter(razorpay_order_id=razorpay_order_id).update(status='Failed')
            return render(request, 'paymentfail.html')
        except Exception as e:
            return HttpResponseBadRequest(str(e))
    else:
        return HttpResponseBadRequest("Invalid request method")
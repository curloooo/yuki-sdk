"""Custom payment methods of the administration.

Calls: GetCustomPaymentMethods.
"""

from yuki_sdk import PaymentMethodSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

methods = PaymentMethodSet(yuki_cred)
methods.get()
print(f"{methods.count} payment methods")
for method in methods:
    print(f"{method.id}  {method.description}")

"""
Stripe integration for worklone-employee SDK.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from worklone_employee.integrations.base import ApiKeyIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.stripe.cancel_payment_intent import StripeCancelPaymentIntentTool
from worklone_employee.integrations.stripe.cancel_subscription import StripeCancelSubscriptionTool
from worklone_employee.integrations.stripe.capture_charge import StripeCaptureChargeTool
from worklone_employee.integrations.stripe.capture_payment_intent import StripeCapturePaymentIntentTool
from worklone_employee.integrations.stripe.confirm_payment_intent import StripeConfirmPaymentIntentTool
from worklone_employee.integrations.stripe.create_charge import StripeCreateChargeTool
from worklone_employee.integrations.stripe.create_customer import StripeCreateCustomerTool
from worklone_employee.integrations.stripe.create_invoice import StripeCreateInvoiceTool
from worklone_employee.integrations.stripe.create_payment_intent import StripeCreatePaymentIntentTool
from worklone_employee.integrations.stripe.create_price import StripeCreatePriceTool
from worklone_employee.integrations.stripe.create_product import StripeCreateProductTool
from worklone_employee.integrations.stripe.create_subscription import StripeCreateSubscriptionTool
from worklone_employee.integrations.stripe.delete_customer import StripeDeleteCustomerTool
from worklone_employee.integrations.stripe.delete_invoice import StripeDeleteInvoiceTool
from worklone_employee.integrations.stripe.delete_product import StripeDeleteProductTool
from worklone_employee.integrations.stripe.finalize_invoice import StripeFinalizeInvoiceTool
from worklone_employee.integrations.stripe.list_charges import StripeListChargesTool
from worklone_employee.integrations.stripe.list_customers import StripeListCustomersTool
from worklone_employee.integrations.stripe.list_events import StripeListEventsTool
from worklone_employee.integrations.stripe.list_invoices import StripeListInvoicesTool
from worklone_employee.integrations.stripe.list_payment_intents import StripeListPaymentIntentsTool
from worklone_employee.integrations.stripe.list_prices import StripeListPricesTool
from worklone_employee.integrations.stripe.list_products import StripeListProductsTool
from worklone_employee.integrations.stripe.list_subscriptions import StripeListSubscriptionsTool
from worklone_employee.integrations.stripe.pay_invoice import StripePayInvoiceTool
from worklone_employee.integrations.stripe.resume_subscription import StripeResumeSubscriptionTool
from worklone_employee.integrations.stripe.retrieve_charge import StripeRetrieveChargeTool
from worklone_employee.integrations.stripe.retrieve_customer import StripeRetrieveCustomerTool
from worklone_employee.integrations.stripe.retrieve_event import StripeRetrieveEventTool
from worklone_employee.integrations.stripe.retrieve_invoice import StripeRetrieveInvoiceTool
from worklone_employee.integrations.stripe.retrieve_payment_intent import StripeRetrievePaymentIntentTool
from worklone_employee.integrations.stripe.retrieve_price import StripeRetrievePriceTool
from worklone_employee.integrations.stripe.retrieve_product import StripeRetrieveProductTool
from worklone_employee.integrations.stripe.retrieve_subscription import StripeRetrieveSubscriptionTool
from worklone_employee.integrations.stripe.search_charges import StripeSearchChargesTool
from worklone_employee.integrations.stripe.search_customers import StripeSearchCustomersTool
from worklone_employee.integrations.stripe.search_invoices import StripeSearchInvoicesTool
from worklone_employee.integrations.stripe.search_payment_intents import StripeSearchPaymentIntentsTool
from worklone_employee.integrations.stripe.search_prices import StripeSearchPricesTool
from worklone_employee.integrations.stripe.search_products import StripeSearchProductsTool
from worklone_employee.integrations.stripe.search_subscriptions import StripeSearchSubscriptionsTool
from worklone_employee.integrations.stripe.send_invoice import StripeSendInvoiceTool
from worklone_employee.integrations.stripe.update_charge import StripeUpdateChargeTool
from worklone_employee.integrations.stripe.update_customer import StripeUpdateCustomerTool
from worklone_employee.integrations.stripe.update_invoice import StripeUpdateInvoiceTool
from worklone_employee.integrations.stripe.update_payment_intent import StripeUpdatePaymentIntentTool
from worklone_employee.integrations.stripe.update_price import StripeUpdatePriceTool
from worklone_employee.integrations.stripe.update_product import StripeUpdateProductTool
from worklone_employee.integrations.stripe.update_subscription import StripeUpdateSubscriptionTool
from worklone_employee.integrations.stripe.void_invoice import StripeVoidInvoiceTool

_TOOL_CLASSES = [
    StripeCancelPaymentIntentTool, StripeCancelSubscriptionTool, StripeCaptureChargeTool, StripeCapturePaymentIntentTool, StripeConfirmPaymentIntentTool, StripeCreateChargeTool, StripeCreateCustomerTool, StripeCreateInvoiceTool, StripeCreatePaymentIntentTool, StripeCreatePriceTool, StripeCreateProductTool, StripeCreateSubscriptionTool, StripeDeleteCustomerTool, StripeDeleteInvoiceTool, StripeDeleteProductTool, StripeFinalizeInvoiceTool, StripeListChargesTool, StripeListCustomersTool, StripeListEventsTool, StripeListInvoicesTool, StripeListPaymentIntentsTool, StripeListPricesTool, StripeListProductsTool, StripeListSubscriptionsTool, StripePayInvoiceTool, StripeResumeSubscriptionTool, StripeRetrieveChargeTool, StripeRetrieveCustomerTool, StripeRetrieveEventTool, StripeRetrieveInvoiceTool, StripeRetrievePaymentIntentTool, StripeRetrievePriceTool, StripeRetrieveProductTool, StripeRetrieveSubscriptionTool, StripeSearchChargesTool, StripeSearchCustomersTool, StripeSearchInvoicesTool, StripeSearchPaymentIntentsTool, StripeSearchPricesTool, StripeSearchProductsTool, StripeSearchSubscriptionsTool, StripeSendInvoiceTool, StripeUpdateChargeTool, StripeUpdateCustomerTool, StripeUpdateInvoiceTool, StripeUpdatePaymentIntentTool, StripeUpdatePriceTool, StripeUpdateProductTool, StripeUpdateSubscriptionTool, StripeVoidInvoiceTool,
]

def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        return integration._get_token()
    tool._resolve_access_token = _resolve_access_token
    return tool


class Stripe(ApiKeyIntegration):
    """Pass your Stripe secret key (sk_live_... or sk_test_...)."""

    def __init__(self, api_key: str):
        super().__init__(api_key)


    def all(self) -> List[BaseTool]:
        return [_wire(cls(), self) for cls in _TOOL_CLASSES]

    @property
    def cancel_payment_intent(self): return _wire(StripeCancelPaymentIntentTool(), self)
    @property
    def cancel_subscription(self): return _wire(StripeCancelSubscriptionTool(), self)
    @property
    def capture_charge(self): return _wire(StripeCaptureChargeTool(), self)
    @property
    def capture_payment_intent(self): return _wire(StripeCapturePaymentIntentTool(), self)
    @property
    def confirm_payment_intent(self): return _wire(StripeConfirmPaymentIntentTool(), self)
    @property
    def create_charge(self): return _wire(StripeCreateChargeTool(), self)
    @property
    def create_customer(self): return _wire(StripeCreateCustomerTool(), self)
    @property
    def create_invoice(self): return _wire(StripeCreateInvoiceTool(), self)
    @property
    def create_payment_intent(self): return _wire(StripeCreatePaymentIntentTool(), self)
    @property
    def create_price(self): return _wire(StripeCreatePriceTool(), self)
    @property
    def create_product(self): return _wire(StripeCreateProductTool(), self)
    @property
    def create_subscription(self): return _wire(StripeCreateSubscriptionTool(), self)
    @property
    def delete_customer(self): return _wire(StripeDeleteCustomerTool(), self)
    @property
    def delete_invoice(self): return _wire(StripeDeleteInvoiceTool(), self)
    @property
    def delete_product(self): return _wire(StripeDeleteProductTool(), self)
    @property
    def finalize_invoice(self): return _wire(StripeFinalizeInvoiceTool(), self)
    @property
    def list_charges(self): return _wire(StripeListChargesTool(), self)
    @property
    def list_customers(self): return _wire(StripeListCustomersTool(), self)
    @property
    def list_events(self): return _wire(StripeListEventsTool(), self)
    @property
    def list_invoices(self): return _wire(StripeListInvoicesTool(), self)
    @property
    def list_payment_intents(self): return _wire(StripeListPaymentIntentsTool(), self)
    @property
    def list_prices(self): return _wire(StripeListPricesTool(), self)
    @property
    def list_products(self): return _wire(StripeListProductsTool(), self)
    @property
    def list_subscriptions(self): return _wire(StripeListSubscriptionsTool(), self)
    @property
    def pay_invoice(self): return _wire(StripePayInvoiceTool(), self)
    @property
    def resume_subscription(self): return _wire(StripeResumeSubscriptionTool(), self)
    @property
    def retrieve_charge(self): return _wire(StripeRetrieveChargeTool(), self)
    @property
    def retrieve_customer(self): return _wire(StripeRetrieveCustomerTool(), self)
    @property
    def retrieve_event(self): return _wire(StripeRetrieveEventTool(), self)
    @property
    def retrieve_invoice(self): return _wire(StripeRetrieveInvoiceTool(), self)
    @property
    def retrieve_payment_intent(self): return _wire(StripeRetrievePaymentIntentTool(), self)
    @property
    def retrieve_price(self): return _wire(StripeRetrievePriceTool(), self)
    @property
    def retrieve_product(self): return _wire(StripeRetrieveProductTool(), self)
    @property
    def retrieve_subscription(self): return _wire(StripeRetrieveSubscriptionTool(), self)
    @property
    def search_charges(self): return _wire(StripeSearchChargesTool(), self)
    @property
    def search_customers(self): return _wire(StripeSearchCustomersTool(), self)
    @property
    def search_invoices(self): return _wire(StripeSearchInvoicesTool(), self)
    @property
    def search_payment_intents(self): return _wire(StripeSearchPaymentIntentsTool(), self)
    @property
    def search_prices(self): return _wire(StripeSearchPricesTool(), self)
    @property
    def search_products(self): return _wire(StripeSearchProductsTool(), self)
    @property
    def search_subscriptions(self): return _wire(StripeSearchSubscriptionsTool(), self)
    @property
    def send_invoice(self): return _wire(StripeSendInvoiceTool(), self)
    @property
    def update_charge(self): return _wire(StripeUpdateChargeTool(), self)
    @property
    def update_customer(self): return _wire(StripeUpdateCustomerTool(), self)
    @property
    def update_invoice(self): return _wire(StripeUpdateInvoiceTool(), self)
    @property
    def update_payment_intent(self): return _wire(StripeUpdatePaymentIntentTool(), self)
    @property
    def update_price(self): return _wire(StripeUpdatePriceTool(), self)
    @property
    def update_product(self): return _wire(StripeUpdateProductTool(), self)
    @property
    def update_subscription(self): return _wire(StripeUpdateSubscriptionTool(), self)
    @property
    def void_invoice(self): return _wire(StripeVoidInvoiceTool(), self)

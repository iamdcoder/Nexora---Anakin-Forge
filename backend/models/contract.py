from datetime import datetime
from pydantic import BaseModel

class SLAContract(BaseModel):
    minimum_uptime: float
    penalty_percent: float

class B2BContract(BaseModel):
    contract_id: str
    buyer_name: str
    supplier_name: str
    product_name: str
    quantity: int
    unit_price: float
    currency: str
    delivery_days: int
    payment_days: int
    sla: SLAContract
    negotiation_id: str
    negotiation_rounds: int
    status: str
    created_at: datetime
    version: int = 1
    contract_hash: str | None = None

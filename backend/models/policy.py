from pydantic import BaseModel, Field, model_validator

class PricePolicy(BaseModel):
    target: float = Field(gt=0)
    minimum: float | None = Field(default=None, gt=0)
    maximum: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("Price minimum cannot exceed price maximum.")
        if self.minimum is not None and self.target < self.minimum:
            raise ValueError("Price target cannot be below price minimum.")
        if self.maximum is not None and self.target > self.maximum:
            raise ValueError("Price target cannot exceed price maximum.")
        return self

class DeliveryPolicy(BaseModel):
    target_days: int = Field(gt=0)
    maximum_days: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.target_days > self.maximum_days:
            raise ValueError("Delivery target cannot exceed maximum delivery days.")
        return self

class PaymentPolicy(BaseModel):
    preferred_days: int = Field(gt=0)
    minimum_days: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.preferred_days < self.minimum_days:
            raise ValueError("Preferred payment days cannot be below minimum payment days.")
        return self

class SLAPolicy(BaseModel):
    minimum_uptime: float = Field(ge=0, le=100)
    minimum_penalty: float = Field(ge=0)
    maximum_penalty: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.minimum_penalty > self.maximum_penalty:
            raise ValueError("Minimum SLA penalty cannot exceed maximum SLA penalty.")
        return self

class PartyPolicy(BaseModel):
    price: PricePolicy
    delivery: DeliveryPolicy
    payment: PaymentPolicy
    sla: SLAPolicy
    batna: str
    max_rounds: int = Field(default=10, gt=0, le=50)

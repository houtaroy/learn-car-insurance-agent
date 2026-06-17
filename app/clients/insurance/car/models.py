from decimal import Decimal

from pydantic import BaseModel, computed_field


class Quotation(BaseModel):
    id: str
    company_code: str
    company_name: str
    company_icon: str
    compulsory_premium: Decimal
    damage_premium: Decimal
    third_party_premium: Decimal
    vehicle_tax: Decimal

    @computed_field
    @property
    def commercial_premium(self) -> Decimal:
        return self.damage_premium + self.third_party_premium

    @computed_field
    @property
    def total_premium(self) -> Decimal:
        return self.compulsory_premium + self.commercial_premium

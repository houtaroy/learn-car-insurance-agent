from decimal import Decimal

from app.clients.insurance.car.models import Quotation
from app.clients.insurance.car.models import UnderwritingPolicy

PAYMENT_QR_CODE_URL = (
    "https://car-insurance-agent.oss-cn-beijing.aliyuncs.com/"
    "2026/06/17/03e35696dc47490bbe639c2578143e87.png"
)


def quote(license_plate: str) -> list[Quotation]:
    return [
        Quotation(
            id=f"{license_plate}-000017",
            company_code="000017",
            company_name="平安保险",
            company_icon="https://pc.car.xiaohe100.cn/img/logos/000017.png",
            compulsory_premium=Decimal("360"),
            damage_premium=Decimal("520"),
            third_party_premium=Decimal("480"),
            vehicle_tax=Decimal("300"),
        ),
        Quotation(
            id=f"{license_plate}-000242",
            company_code="000242",
            company_name="大家保险",
            company_icon="https://pc.car.xiaohe100.cn/img/logos/000242.png",
            compulsory_premium=Decimal("330"),
            damage_premium=Decimal("470"),
            third_party_premium=Decimal("430"),
            vehicle_tax=Decimal("300"),
        ),
        Quotation(
            id=f"{license_plate}-000068",
            company_code="000068",
            company_name="永诚财险",
            company_icon="https://pc.car.xiaohe100.cn/img/logos/000068.png",
            compulsory_premium=Decimal("300"),
            damage_premium=Decimal("420"),
            third_party_premium=Decimal("360"),
            vehicle_tax=Decimal("300"),
        ),
    ]


def underwrite(quotation_id: str) -> UnderwritingPolicy:
    return UnderwritingPolicy(
        id=f"{quotation_id}-underwriting",
        payment_qr_code_url=PAYMENT_QR_CODE_URL,
    )

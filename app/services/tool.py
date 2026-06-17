import json

from openai.types.responses import ResponseFunctionToolCall
from openai.types.responses.tool_param import ToolParam

from app.clients.insurance.car import Quotation
from app.clients.insurance.car import UnderwritingPolicy
from app.clients.insurance.car import quote as client_quote
from app.clients.insurance.car import (
    query_payment_result as client_query_payment_result,
)
from app.clients.insurance.car import underwrite as client_underwrite

TOOLS: list[ToolParam] = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "查询指定地点的当前天气。",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "城市和国家，例如：中国北京",
                },
            },
            "required": ["location"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "quote",
        "description": "根据车牌号为车辆进行报价, 结果为报价单列表",
        "parameters": {
            "type": "object",
            "properties": {
                "license_plate": {
                    "type": "string",
                    "description": "车牌号, 例如: 京A12345",
                },
            },
            "required": ["license_plate"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "underwrite",
        "description": "使用投保单id进行核保, 返回核保单",
        "parameters": {
            "type": "object",
            "properties": {
                "quotation_id": {
                    "type": "string",
                    "description": "来自报价结果中的投保单id",
                },
            },
            "required": ["quotation_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "query_payment_result",
        "description": "使用核保单id查询支付结果, 返回是否支付成功",
        "parameters": {
            "type": "object",
            "properties": {
                "underwriting_policy_id": {
                    "type": "string",
                    "description": "来自核保结果中的核保单id",
                },
            },
            "required": ["underwriting_policy_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def get_weather(location: str) -> str:
    """查询指定地点的天气。"""
    return f"{location}的天气晴朗。"


def quote(license_plate: str) -> list[Quotation]:
    """根据车牌号为车辆进行保险报价, 结果为报价单列表"""
    return client_quote(license_plate)


def underwrite(quotation_id: str) -> UnderwritingPolicy:
    """使用投保单id进行核保, 返回核保单"""
    return client_underwrite(quotation_id)


def query_payment_result(underwriting_policy_id: str) -> bool:
    """使用核保单id查询支付结果, 返回是否支付成功"""
    return client_query_payment_result(underwriting_policy_id)


def call_tool(tool_call: ResponseFunctionToolCall) -> str:
    arguments = json.loads(tool_call.arguments)

    if tool_call.name == "get_weather":
        return get_weather(arguments["location"])

    if tool_call.name == "quote":
        quotations = quote(arguments["license_plate"])
        return json.dumps(
            [quotation.model_dump(mode="json") for quotation in quotations],
            ensure_ascii=False,
        )

    if tool_call.name == "underwrite":
        underwriting_policy = underwrite(arguments["quotation_id"])
        return underwriting_policy.model_dump_json()

    if tool_call.name == "query_payment_result":
        is_paid = query_payment_result(arguments["underwriting_policy_id"])
        return json.dumps(is_paid, ensure_ascii=False)

    raise ValueError(f"未知工具：{tool_call.name}")

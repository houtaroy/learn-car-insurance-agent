import json
from collections.abc import Callable
from typing import TypedDict

from openai.types.responses import ResponseFunctionToolCall
from openai.types.responses.tool_param import ToolParam

from app.clients.insurance.car import quote as client_quote
from app.clients.insurance.car import (
    query_payment_result as client_query_payment_result,
)
from app.clients.insurance.car import query_policies as client_query_policies
from app.clients.insurance.car import underwrite as client_underwrite


class ToolDefinition(TypedDict):
    schema: ToolParam
    handler: Callable[..., str]


def handle_get_weather(location: str) -> str:
    return f"{location}的天气晴朗。"


def handle_quote(license_plate: str) -> str:
    quotations = client_quote(license_plate)
    return json.dumps(
        [quotation.model_dump(mode="json") for quotation in quotations],
        ensure_ascii=False,
    )


def handle_underwrite(quotation_id: str) -> str:
    underwriting_policy = client_underwrite(quotation_id)
    return underwriting_policy.model_dump_json()


def handle_query_payment_result(underwriting_policy_id: str) -> str:
    is_paid = client_query_payment_result(underwriting_policy_id)
    return json.dumps(is_paid, ensure_ascii=False)


def handle_query_policies(license_plate: str) -> str:
    policies = client_query_policies(license_plate)
    return json.dumps(
        [policy.model_dump(mode="json") for policy in policies],
        ensure_ascii=False,
    )


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "get_weather": {
        "schema": {
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
        "handler": handle_get_weather,
    },
    "quote": {
        "schema": {
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
        "handler": handle_quote,
    },
    "underwrite": {
        "schema": {
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
        "handler": handle_underwrite,
    },
    "query_payment_result": {
        "schema": {
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
        "handler": handle_query_payment_result,
    },
    "query_policies": {
        "schema": {
            "type": "function",
            "name": "query_policies",
            "description": "根据车牌号查询已出具的保单, 结果为保单对象列表",
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
        "handler": handle_query_policies,
    },
}

TOOLS: list[ToolParam] = [tool["schema"] for tool in TOOL_REGISTRY.values()]


def call_tool(tool_call: ResponseFunctionToolCall) -> str:
    arguments = json.loads(tool_call.arguments)
    tool = TOOL_REGISTRY.get(tool_call.name)
    if tool:
        return tool["handler"](**arguments)

    raise ValueError(f"未知工具：{tool_call.name}")

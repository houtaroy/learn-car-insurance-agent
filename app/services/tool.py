import json

from openai.types.responses import ResponseFunctionToolCall
from openai.types.responses.tool_param import ToolParam

from app.clients.insurance.car import Quotation
from app.clients.insurance.car import quote as quote_car

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
        "description": "根据车牌号为车辆进行保险报价, 结果为报价单列表",
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
]


def get_weather(location: str) -> str:
    """查询指定地点的天气。"""
    return f"{location}的天气晴朗。"


def quote(license_plate: str) -> list[Quotation]:
    """根据车牌号为车辆进行保险报价, 结果为报价单列表"""
    return quote_car(license_plate)


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

    raise ValueError(f"未知工具：{tool_call.name}")

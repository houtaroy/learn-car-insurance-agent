import json

from openai.types.responses import ResponseFunctionToolCall
from openai.types.responses.tool_param import ToolParam


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
    }
]


def get_weather(location: str) -> str:
    """查询指定地点的天气。"""
    return f"{location}的天气晴朗。"


def call_tool(tool_call: ResponseFunctionToolCall) -> str:
    arguments = json.loads(tool_call.arguments)

    if tool_call.name == "get_weather":
        return get_weather(arguments["location"])

    raise ValueError(f"未知工具：{tool_call.name}")

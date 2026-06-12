| Responses API Stream Event               | 参数                  | AG-UI Events                    | AG-UI Event Data                                             |
| ---------------------------------------- | --------------------- | ------------------------------- | ------------------------------------------------------------ |
| `response.created`                       | 无                    | `RUN_STARTED`                   | `{"type": "RUN_STARTED", "threadId": "thread_123", "runId": "run_123"}` |
| `response.output_item.added`             | `type: reasoning`     | `THINKING_START`                | `{"type": "THINKING_START", "title": "思考"}`                |
| `response.output_item.added`             | `type: reasoning`     | `THINKING_TEXT_MESSAGE_START`   | `{"type": "THINKING_TEXT_MESSAGE_START"}`                    |
| `response.reasoning_summary_text.delta`  | 无                    | `THINKING_TEXT_MESSAGE_CONTENT` | `{"type": "THINKING_TEXT_MESSAGE_CONTENT", "msgId": "msg_123", "delta": "我思考"}` |
| `response.reasoning_summary_text.done`   | 无                    | `THINKING_TEXT_MESSAGE_END`     | `{"type": "THINKING_TEXT_MESSAGE_END"}`                      |
| `response.output_item.done`              | `type: reasoning`     | `THINKING_END`                  | `{"type": "THINKING_END", "title": "思考"}`                  |
| `response.output_item.added`             | `type: message`       | `TEXT_MESSAGE_START`            | `{"type": "TEXT_MESSAGE_START", "messageId": "msg_123", "role": "assistant"}` |
| `response.output_text.delta`             | 无                    | `TEXT_MESSAGE_CONTENT`          | `{"type": "TEXT_MESSAGE_CONTENT", "messageId": "msg_123", "delta": "你好"}` |
| `response.output_item.done`              | `type: message`       | `TEXT_MESSAGE_END`              | `{"type": "TEXT_MESSAGE_END", "messageId": "msg_123"}`       |
| `response.output_item.added`             | `type: function_call` | `TOOL_CALL_START`               | `{"type": "TOOL_CALL_START", "toolCallId": "call_123", "toolCallName": "get_weather"}` |
| `response.function_call_arguments.delta` | 无                    | `TOOL_CALL_ARGS`                | `{"type": "TOOL_CALL_ARGS", "toolCallId": "call_123", "delta": "{\"location\": \"中国石家庄\"}"}` |
| 工具实际执行完成后                       | 无                    | `TOOL_CALL_END`                 | `{"type": "TOOL_CALL_END", "toolCallId": "call_123"}`        |
| 工具实际执行完成后                       | 无                    | `TOOL_CALL_RESULT`              | `{"type": "TOOL_CALL_RESULT", "toolCallId": "call_123", "toolCallName": "get_weather", "content": "石家庄天气晴朗"}` |
| `response.completed`                     | 无                    | `RUN_FINISHED`                  | `{"type": "RUN_FINISHED", "threadId": "thread_123", "runId": "run_123"}` |

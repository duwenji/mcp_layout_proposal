"""
MCPプロトコルメッセージのロギング機能を提供するモジュール
"""

import json
import logging
from typing import Any
from anyio import EndOfStream


def sanitize_log_output(result: Any) -> Any:
    """
    ログ出力用に機密情報をマスクする関数

    Args:
        result: ログ出力する結果データ

    Returns:
        機密情報がマスクされた結果データ
    """
    import logging

    logger = logging.getLogger(__name__)

    if logger.isEnabledFor(logging.DEBUG):
        input_repr = repr(result)[:200]
        logger.debug(
            f"SANITIZE_LOG_OUTPUT_START - input_type: {type(result)}, "
            f"input_repr: {input_repr}"
        )

    if isinstance(result, dict):
        sanitized = result.copy()
        # 機密情報を含む可能性のあるフィールドをマスク
        sensitive_fields = ["password", "secret", "token", "key", "auth"]
        masked_count = 0
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "***MASKED***"
                masked_count += 1

        if logger.isEnabledFor(logging.DEBUG):
            dict_keys = list(sanitized.keys())
            logger.debug(
                f"SANITIZE_LOG_OUTPUT_DICT - dict_keys: {dict_keys}, "
                f"masked_fields: {masked_count}"
            )

        # ネストされた辞書も再帰的に処理
        for key, value in sanitized.items():
            if isinstance(value, dict):
                sanitized[key] = sanitize_log_output(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    sanitize_log_output(item) if isinstance(item, dict) else item
                    for item in value
                ]

        if logger.isEnabledFor(logging.DEBUG):
            processed_keys = list(sanitized.keys())
            logger.debug(
                f"SANITIZE_LOG_OUTPUT_DICT_COMPLETE - "
                f"processed_dict_keys: {processed_keys}"
            )

        return sanitized
    elif isinstance(result, list):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"SANITIZE_LOG_OUTPUT_LIST - list_length: {len(result)}")

        sanitized_list = [
            sanitize_log_output(item) if isinstance(item, dict) else item
            for item in result
        ]

        if logger.isEnabledFor(logging.DEBUG):
            processed_length = len(sanitized_list)
            logger.debug(
                f"SANITIZE_LOG_OUTPUT_LIST_COMPLETE - "
                f"processed_list_length: {processed_length}"
            )

        return sanitized_list
    else:
        if logger.isEnabledFor(logging.DEBUG):
            value_preview = repr(result)[:100]
            logger.debug(
                f"SANITIZE_LOG_OUTPUT_OTHER - type: {type(result)}, "
                f"value: {value_preview}"
            )
        return result


def sanitize_protocol_message(message: str) -> str:
    """
    MCPプロトコルメッセージの機密情報をマスクする関数

    Args:
        message: JSON形式のプロトコルメッセージ

    Returns:
        機密情報がマスクされたメッセージ
    """
    import logging

    logger = logging.getLogger(__name__)

    if logger.isEnabledFor(logging.DEBUG):
        message_preview = message[:100]
        logger.debug(
            f"SANITIZE_PROTOCOL_MESSAGE_START - message_length: {len(message)}, "
            f"message_preview: {message_preview}"
        )

    try:
        data = json.loads(message)
        if logger.isEnabledFor(logging.DEBUG):
            is_dict = isinstance(data, dict)
            is_list = isinstance(data, list)
            logger.debug(
                f"SANITIZE_PROTOCOL_MESSAGE_JSON_PARSED - data_type: {type(data)}, "
                f"is_dict: {is_dict}, is_list: {is_list}"
            )

        sanitized_data = sanitize_log_output(data)

        result = json.dumps(sanitized_data, ensure_ascii=False)

        if logger.isEnabledFor(logging.DEBUG):
            result_preview = result[:100]
            logger.debug(
                f"SANITIZE_PROTOCOL_MESSAGE_COMPLETE - result_length: {len(result)}, "
                f"result_preview: {result_preview}"
            )

        return result
    except json.JSONDecodeError as e:
        if logger.isEnabledFor(logging.DEBUG):
            message_preview = message[:200]
            logger.debug(
                f"SANITIZE_PROTOCOL_MESSAGE_JSON_ERROR - JSONDecodeError: {e}, "
                f"message_preview: {message_preview}"
            )
        # JSONとして解析できない場合は元のメッセージを返す
        return message
    except TypeError as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"SANITIZE_PROTOCOL_MESSAGE_TYPE_ERROR - TypeError: {e}, "
                f"message_type: {type(message)}"
            )
        # JSONとして解析できない場合は元のメッセージを返す
        return message


class ProtocolLoggingReceiveStream:
    """
    MCPプロトコルメッセージをログに記録する受信ストリームラッパー
    """

    def __init__(
        self, original_stream: Any, logger_instance: logging.Logger | None = None
    ) -> None:
        self.original_stream = original_stream
        self.logger = logger_instance

        if self.logger:
            self.logger.debug(
                f"PROTOCOL_RECEIVE_STREAM_INIT - original_stream_type: {type(original_stream)}, "
                f"logger_provided: {logger_instance is not None}, "
                f"logger_level: {logger_instance.level if logger_instance else 'N/A'}, "
                f"logger_name: {logger_instance.name if logger_instance else 'N/A'}"
            )

    async def receive(self) -> Any:
        """受信操作をラップしてログに記録"""
        try:
            if self.logger:
                self.logger.debug("RECEIVE_START - Waiting for message")

            # 元のストリームのreceiveメソッドを呼び出し
            data = await self.original_stream.receive()

            if self.logger:
                self.logger.debug(
                    f"RECEIVE_COMPLETE - data_received: {data is not None}, data_type: {type(data)}"
                )

            if data is not None:
                try:
                    if self.logger:
                        # 詳細なデータ情報をログに記録
                        data_size = len(data) if hasattr(data, "__len__") else "N/A"
                        self.logger.debug(
                            f"RECEIVE_DATA_DETAILS - data_type: {type(data)}, "
                            f"data_size: {data_size}, "
                            f"data_repr: {repr(data)[:500]}"
                        )

                        # データがbytes型の場合はデコードしてログに記録
                        if isinstance(data, bytes):
                            message = data.decode("utf-8").strip()
                            if message:
                                sanitized_message = sanitize_protocol_message(message)
                                self.logger.info(
                                    f"REQUEST - original_length: {len(data)}, "
                                    f"decoded_length: {len(message)}, "
                                    f"sanitized_length: {len(sanitized_message)}, "
                                    f"content: {sanitized_message}"
                                )
                            else:
                                self.logger.debug(
                                    "REQUEST_EMPTY - Empty message received, bytes_length: 0"
                                )
                        elif hasattr(data, "message") and hasattr(data.message, "root"):
                            # MCP SessionMessageオブジェクトの場合
                            try:
                                import json
                                from mcp.shared.message import JSONRPCMessage

                                if isinstance(data.message, JSONRPCMessage):
                                    # JSON-RPCメッセージをJSON形式でログ出力
                                    message_dict = {
                                        "jsonrpc": data.message.root.jsonrpc,
                                        "id": getattr(data.message.root, "id", None),
                                        "method": getattr(
                                            data.message.root, "method", None
                                        ),
                                        "params": getattr(
                                            data.message.root, "params", None
                                        ),
                                    }
                                    sanitized_message = sanitize_log_output(
                                        message_dict
                                    )
                                    json_output = json.dumps(
                                        sanitized_message, ensure_ascii=False, indent=2
                                    )
                                    self.logger.info(
                                        f"REQUEST_JSONRPC - message_type: JSONRPCMessage, "
                                        f"json_length: {len(json_output)}, "
                                        f"content:\n{json_output}"
                                    )
                                else:
                                    # その他のメッセージタイプ
                                    message_str = str(data)
                                    sanitized_message = sanitize_protocol_message(
                                        message_str
                                    )
                                    self.logger.info(
                                        f"REQUEST_OTHER_MCP - message_type: {type(data.message)}, "
                                        f"content_length: {len(sanitized_message)}, "
                                        f"content: {sanitized_message}"
                                    )
                            except Exception as json_error:
                                self.logger.warning(
                                    f"JSON serialization error: {json_error}, falling back to string representation"
                                )
                                message_str = str(data)
                                sanitized_message = sanitize_protocol_message(
                                    message_str
                                )
                                self.logger.info(
                                    f"REQUEST_FALLBACK - error: {json_error}, "
                                    f"content_length: {len(sanitized_message)}, "
                                    f"content: {sanitized_message}"
                                )
                        else:
                            # その他の型の場合は文字列化してログに記録
                            message_str = str(data)
                            sanitized_message = sanitize_protocol_message(message_str)
                            self.logger.info(
                                f"REQUEST_STRING - original_type: {type(data)}, "
                                f"string_length: {len(message_str)}, "
                                f"sanitized_length: {len(sanitized_message)}, "
                                f"content: {sanitized_message}"
                            )

                except Exception as e:
                    # 詳細なエラー情報をログに記録
                    if self.logger:
                        import traceback

                        self.logger.error(
                            f"Error logging request: {e}, traceback: {traceback.format_exc()}"
                        )
            return data
        except EndOfStream as e:
            # ストリームの正常な終了 - デバッグログとして記録
            if self.logger:
                self.logger.debug(f"RECEIVE_END_OF_STREAM - Stream ended normally: {e}")
            raise
        except Exception as e:
            # 詳細なエラー情報をログに記録
            if self.logger:
                import traceback

                self.logger.error(
                    f"RECEIVE_ERROR - error: {e}, traceback: {traceback.format_exc()}"
                )
            raise e

    async def __aenter__(self) -> Any:
        """非同期コンテキストマネージャーのエントリーポイント"""
        # 常にselfを返す - これが非同期コンテキストマネージャーの正しい実装
        try:
            if hasattr(self.original_stream, "__aenter__"):
                await self.original_stream.__aenter__()
        except Exception as e:
            # 元のストリームのエントリーポイントでエラーが発生した場合
            if self.logger:
                self.logger.error(f"Error in original stream __aenter__: {e}")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        """非同期コンテキストマネージャーの終了ポイント"""
        try:
            if hasattr(self.original_stream, "__aexit__"):
                return await self.original_stream.__aexit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            # 元のストリームの終了ポイントでエラーが発生した場合
            if self.logger:
                self.logger.error(f"Error in original stream __aexit__: {e}")
        return False

    def __getattr__(self, name: str) -> Any:
        """他のメソッドは元のストリームに委譲"""
        try:
            return getattr(self.original_stream, name)
        except AttributeError:
            # 元のストリームにメソッドがない場合はAttributeErrorをそのまま送出
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

    def __aiter__(self) -> "ProtocolLoggingReceiveStream":
        """非同期イテレーターをサポート"""
        return self

    async def __anext__(self) -> Any:
        """非同期イテレーターの次の要素を返す"""
        try:
            data = await self.receive()
            if data is None:
                # ストリーム終了を適切に通知
                if self.logger:
                    self.logger.debug("STREAM_END - End of stream reached")
                raise StopAsyncIteration
            return data
        except StopAsyncIteration:
            # StopAsyncIterationはそのまま送出
            if self.logger:
                self.logger.debug("STREAM_END - StopAsyncIteration raised")
            raise
        except EndOfStream as e:
            # ストリームの正常な終了 - StopAsyncIterationに変換
            if self.logger:
                self.logger.debug(f"STREAM_END_OF_STREAM - Stream ended normally: {e}")
            raise StopAsyncIteration from e
        except Exception as e:
            # その他の例外はログに記録してからStopAsyncIterationを送出
            if self.logger:
                import traceback

                self.logger.error(f"STREAM_ERROR - Async iteration error: {e}")
                self.logger.debug(
                    f"STREAM_ERROR_TRACE - Traceback: {traceback.format_exc()}"
                )
            # 元の例外を保持したままStopAsyncIterationを送出
            raise StopAsyncIteration from e


class ProtocolLoggingSendStream:
    """
    MCPプロトコルメッセージをログに記録する送信ストリームラッパー
    """

    def __init__(
        self, original_stream: Any, logger_instance: logging.Logger | None = None
    ) -> None:
        self.original_stream = original_stream
        self.logger = logger_instance

        if self.logger:
            self.logger.debug(
                f"PROTOCOL_SEND_STREAM_INIT - original_stream_type: {type(original_stream)}, "
                f"logger_provided: {logger_instance is not None}, "
                f"logger_level: {logger_instance.level if logger_instance else 'N/A'}, "
                f"logger_name: {logger_instance.name if logger_instance else 'N/A'}"
            )

    async def send(self, item: Any) -> None:
        """送信操作をラップしてログに記録"""
        try:
            if self.logger:
                self.logger.debug(
                    f"SEND_START - item_type: {type(item)}, item_not_none: {item is not None}"
                )

            if item is not None:
                try:
                    if self.logger:
                        # 詳細なデータ情報をログに記録
                        item_size = len(item) if hasattr(item, "__len__") else "N/A"
                        self.logger.debug(
                            f"SEND_DATA_DETAILS - item_type: {type(item)}, "
                            f"item_size: {item_size}, "
                            f"item_repr: {repr(item)[:500]}"
                        )

                        # データがbytes型の場合はデコードしてログに記録
                        if isinstance(item, bytes):
                            message = item.decode("utf-8").strip()
                            if message:
                                sanitized_message = sanitize_protocol_message(message)
                                self.logger.info(
                                    f"RESPONSE - original_length: {len(item)}, "
                                    f"decoded_length: {len(message)}, "
                                    f"sanitized_length: {len(sanitized_message)}, "
                                    f"content: {sanitized_message}"
                                )
                            else:
                                self.logger.debug(
                                    "RESPONSE_EMPTY - Empty message to send, bytes_length: 0"
                                )
                        elif hasattr(item, "message") and hasattr(item.message, "root"):
                            # MCP SessionMessageオブジェクトの場合
                            try:
                                import json
                                from mcp.shared.message import JSONRPCMessage

                                if isinstance(item.message, JSONRPCMessage):
                                    # JSON-RPCメッセージをJSON形式でログ出力
                                    message_dict = {
                                        "jsonrpc": item.message.root.jsonrpc,
                                        "id": getattr(item.message.root, "id", None),
                                        "result": getattr(
                                            item.message.root, "result", None
                                        ),
                                        "error": getattr(
                                            item.message.root, "error", None
                                        ),
                                    }
                                    sanitized_message = sanitize_log_output(
                                        message_dict
                                    )
                                    json_output = json.dumps(
                                        sanitized_message, ensure_ascii=False, indent=2
                                    )
                                    self.logger.info(
                                        f"RESPONSE_JSONRPC - message_type: JSONRPCMessage, "
                                        f"json_length: {len(json_output)}, "
                                        f"content:\n{json_output}"
                                    )
                                else:
                                    # その他のメッセージタイプ
                                    message_str = str(item)
                                    sanitized_message = sanitize_protocol_message(
                                        message_str
                                    )
                                    self.logger.info(
                                        f"RESPONSE_OTHER_MCP - message_type: {type(item.message)}, "
                                        f"content_length: {len(sanitized_message)}, "
                                        f"content: {sanitized_message}"
                                    )
                            except Exception as json_error:
                                self.logger.warning(
                                    f"JSON serialization error: {json_error}, falling back to string representation"
                                )
                                message_str = str(item)
                                sanitized_message = sanitize_protocol_message(
                                    message_str
                                )
                                self.logger.info(
                                    f"RESPONSE_FALLBACK - error: {json_error}, "
                                    f"content_length: {len(sanitized_message)}, "
                                    f"content: {sanitized_message}"
                                )
                        else:
                            # その他の型の場合は文字列化してログに記録
                            message_str = str(item)
                            sanitized_message = sanitize_protocol_message(message_str)
                            self.logger.info(
                                f"RESPONSE_STRING - original_type: {type(item)}, "
                                f"string_length: {len(message_str)}, "
                                f"sanitized_length: {len(sanitized_message)}, "
                                f"content: {sanitized_message}"
                            )
                except Exception as e:
                    # 詳細なエラー情報をログに記録
                    if self.logger:
                        import traceback

                        self.logger.error(
                            f"Error logging response: {e}, traceback: {traceback.format_exc()}"
                        )

            # 元のストリームのsendメソッドを呼び出し
            await self.original_stream.send(item)

            if self.logger:
                self.logger.debug("SEND_COMPLETE - Message sent successfully")

        except Exception as e:
            # 詳細なエラー情報をログに記録
            if self.logger:
                import traceback

                self.logger.error(
                    f"SEND_ERROR - error: {e}, traceback: {traceback.format_exc()}"
                )
            raise e

    async def __aenter__(self) -> Any:
        """非同期コンテキストマネージャーのエントリーポイント"""
        # 常にselfを返す - これが非同期コンテキストマネージャーの正しい実装
        try:
            if hasattr(self.original_stream, "__aenter__"):
                await self.original_stream.__aenter__()
        except Exception as e:
            # 元のストリームのエントリーポイントでエラーが発生した場合
            if self.logger:
                self.logger.error(f"Error in original stream __aenter__: {e}")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        """非同期コンテキストマネージャーの終了ポイント"""
        try:
            if hasattr(self.original_stream, "__aexit__"):
                return await self.original_stream.__aexit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            # 元のストリームの終了ポイントでエラーが発生した場合
            if self.logger:
                self.logger.error(f"Error in original stream __aexit__: {e}")
        return False

    def __getattr__(self, name: str) -> Any:
        """他のメソッドは元のストリームに委譲"""
        try:
            return getattr(self.original_stream, name)
        except AttributeError:
            # 元のストリームにメソッドがない場合はAttributeErrorをそのまま送出
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )


async def protocol_logging_server(
    read_stream: Any,
    write_stream: Any,
    global_config: Any,
    protocol_logger: logging.Logger | None = None,
) -> tuple[Any, Any]:
    """
    MCPプロトコルメッセージをログに記録するラッパーサーバー

    Args:
        read_stream: 入力ストリーム
        write_stream: 出力ストリーム
        global_config: グローバル設定オブジェクト
        protocol_logger: プロトコルロガー

    Returns:
        ラップされたストリームのタプル
    """
    try:
        # プロトコルデバッグモードが有効な場合のみロギングを有効化
        if global_config and global_config.protocol_debug:
            if protocol_logger:
                protocol_logger.debug(
                    "PROTOCOL_LOGGING_SERVER - Starting stream wrapping"
                )

            # 入出力ストリームをラップ
            wrapped_read_stream = ProtocolLoggingReceiveStream(
                read_stream, protocol_logger
            )
            wrapped_write_stream = ProtocolLoggingSendStream(
                write_stream, protocol_logger
            )

            if protocol_logger:
                protocol_logger.debug(
                    "PROTOCOL_LOGGING_SERVER - Stream wrapping completed"
                )

            return wrapped_read_stream, wrapped_write_stream
        else:
            # プロトコルデバッグモードが無効な場合は元のストリームをそのまま返す
            if protocol_logger:
                protocol_logger.debug(
                    "PROTOCOL_LOGGING_SERVER - Protocol debug disabled, using original streams"
                )
            return read_stream, write_stream
    except Exception as e:
        # エラー情報をloggerに出力
        if protocol_logger:
            import traceback

            protocol_logger.error(
                f"PROTOCOL_LOGGING_SERVER_ERROR - Error in protocol logging server: {e}"
            )
            protocol_logger.debug(
                f"PROTOCOL_LOGGING_SERVER_TRACE - Traceback: {traceback.format_exc()}"
            )
        # エラーを再送出
        raise

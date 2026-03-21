"""
Prompt management system for PostgreSQL MCP Server
"""

from typing import Dict, List, Any, Optional
from mcp.types import Prompt, PromptMessage, TextContent, PromptArgument


class PromptManager:
    """Manages database-related prompts for AI assistants"""

    def __init__(self) -> None:
        self.prompts = self._initialize_prompts()

    def _initialize_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Initialize all available prompts"""
        return {
            "data_analysis_basic": {
                "name": "基本的なデータ分析",
                "description": "テーブルデータの基本的な統計分析を実行",
                "arguments": ["table_name"],
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="テーブル {table_name} のデータを分析して、行数、各カラムの基本統計、欠損値の有無を教えてください。",
                        ),
                    )
                ],
            },
            "data_analysis_advanced": {
                "name": "高度なデータ分析",
                "description": "複数のテーブルを結合した詳細な分析を実行",
                "arguments": ["table_names", "analysis_type"],
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="テーブル {table_names} のデータを結合して、{analysis_type} の観点から詳細な分析を実行してください。",
                        ),
                    )
                ],
            },
            "query_optimization": {
                "name": "クエリ最適化アドバイス",
                "description": "SQLクエリのパフォーマンス改善提案",
                "arguments": ["query"],
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="以下のSQLクエリを最適化するアドバイスをください:\n{query}",
                        ),
                    )
                ],
            },
            "schema_design": {
                "name": "スキーマ設計アドバイス",
                "description": "テーブル設計と正規化のベストプラクティス",
                "arguments": ["table_schema"],
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="以下のテーブルスキーマを確認して、正規化や設計の改善点を提案してください:\n{table_schema}",
                        ),
                    )
                ],
            },
            "data_quality_assessment": {
                "name": "データ品質評価",
                "description": "データの品質評価と改善提案",
                "arguments": ["table_name", "quality_dimensions"],
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="テーブル {table_name} のデータ品質を {quality_dimensions} の観点から評価し、改善提案をしてください。",
                        ),
                    )
                ],
            },
            "relationship_analysis": {
                "name": "テーブル関係性分析",
                "description": "テーブル間の関係性と依存関係の分析",
                "arguments": ["table_names"],
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="テーブル {table_names} 間の関係性を分析して、依存関係や結合の最適な方法を提案してください。",
                        ),
                    )
                ],
            },
            "index_optimization": {
                "name": "インデックス最適化",
                "description": "クエリパフォーマンス向上のためのインデックス設計",
                "arguments": ["query_patterns"],
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="以下のクエリパターンに対して、パフォーマンスを向上させるインデックス設計を提案してください:\n{query_patterns}",
                        ),
                    )
                ],
            },
            "migration_planning": {
                "name": "データ移行計画",
                "description": "スキーマ変更時のデータ移行計画作成",
                "arguments": ["current_schema", "target_schema"],
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="現在のスキーマから目標のスキーマに移行するための計画を作成してください:\n現在: {current_schema}\n目標: {target_schema}",
                        ),
                    )
                ],
            },
            "performance_troubleshooting": {
                "name": "パフォーマンストラブルシューティング",
                "description": "データベースパフォーマンス問題の診断と解決",
                "arguments": ["performance_issue"],
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="以下のパフォーマンス問題に対して、診断と解決策を提案してください:\n{performance_issue}",
                        ),
                    )
                ],
            },
            "backup_recovery_planning": {
                "name": "バックアップと復旧計画",
                "description": "データベースのバックアップと復旧戦略の策定",
                "arguments": ["database_size", "recovery_requirements"],
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=(
                                "データベースサイズ {database_size}、復旧要件 "
                                "{recovery_requirements} に基づいて、適切なバックアップと復旧計画を提案してください。"
                            ),
                        ),
                    )
                ],
            },
        }

    def _get_prompt_concerns(self, prompt_key: str) -> Dict[str, str]:
        """Get concerns for a specific prompt based on its type"""
        concerns_map = {
            "data_analysis_basic": {"development": "-", "using": "-"},
            "data_analysis_advanced": {"development": "-", "using": "-"},
            "query_optimization": {"tuning": "-", "development": "-"},
            "schema_design": {"development": "-"},
            "data_quality_assessment": {"maintenance": "-", "using": "-"},
            "relationship_analysis": {"development": "-", "maintenance": "-"},
            "index_optimization": {"tuning": "-", "development": "-"},
            "migration_planning": {"maintenance": "-", "development": "-"},
            "performance_troubleshooting": {"tuning": "-", "maintenance": "-"},
            "backup_recovery_planning": {"maintenance": "-"},
        }
        return concerns_map.get(prompt_key, {})

    def get_prompt(
        self, name: str, arguments: Optional[Dict[str, str]] = None
    ) -> Optional[Prompt]:
        """Get a specific prompt with argument substitution"""
        if name not in self.prompts:
            return None

        prompt_config = self.prompts[name]

        # Create PromptArgument objects for arguments
        prompt_arguments = (
            [
                PromptArgument(name=arg, description=f"Parameter: {arg}")
                for arg in prompt_config["arguments"]
            ]
            if prompt_config["arguments"]
            else []
        )

        prompt = Prompt(
            name=prompt_config["name"],
            description=prompt_config["description"],
            arguments=prompt_arguments,
        )
        # Add _meta with concerns
        prompt._meta = {"concerns": self._get_prompt_concerns(name)}  # type: ignore[attr-defined]
        return prompt

    def list_prompts(self) -> List[Prompt]:
        """List all available prompts"""
        prompts_list = []
        for key, config in self.prompts.items():
            prompt = Prompt(
                name=config["name"],
                description=config["description"],
                arguments=(
                    [
                        PromptArgument(name=arg, description=f"Parameter: {arg}")
                        for arg in config["arguments"]
                    ]
                    if config["arguments"]
                    else []
                ),
            )
            # Add _meta with concerns based on prompt type
            prompt._meta = {"concerns": self._get_prompt_concerns(key)}  # type: ignore[attr-defined]
            prompts_list.append(prompt)
        return prompts_list


# Global prompt manager instance
prompt_manager = PromptManager()


def get_prompt_manager() -> PromptManager:
    """Get the global prompt manager instance"""
    return prompt_manager

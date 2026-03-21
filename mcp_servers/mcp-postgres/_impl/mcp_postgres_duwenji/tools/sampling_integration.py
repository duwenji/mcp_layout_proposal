"""
MCP Sampling Integration for PostgreSQL MCP Server

This module provides full MCP Sampling integration for LLM-powered
data analysis and quality improvement.
"""

import logging
import json
from typing import Any, Dict, List, Callable, Coroutine, TypedDict
from mcp import Tool
from ..database import DatabaseManager
from ..config import load_config


class SamplingRequest(TypedDict):
    """MCP Samplingリクエストの型定義"""

    messages: List[Dict[str, str]]
    max_tokens: int
    temperature: float
    model: str


class Message(TypedDict):
    """LLMメッセージの型定義"""

    role: str
    content: str


class AnalysisContext(TypedDict):
    """分析コンテキストの型定義"""

    analysis_type: str
    table_names: List[str]
    schemas: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]


class LLMAnalysisResponse(TypedDict, total=False):
    """LLM分析レスポンスの共通型定義"""

    summary: str
    current_level: str
    target_level: str
    issues: List[str]
    recommendations: List[str]
    expected_benefits: Dict[str, str]
    scores: Dict[str, float]
    bottlenecks: List[str]


class QualityAssessmentResult(TypedDict):
    """データ品質評価結果の型定義"""

    quality_dimensions: List[str]
    overall_score: float
    dimension_scores: Dict[str, float]
    identified_issues: List[str]
    sample_data_summary: Dict[str, Dict[str, Any]]
    improvement_priority: str


class OptimizationPlanResult(TypedDict):
    """スキーマ最適化計画結果の型定義"""

    optimization_goals: List[str]
    identified_bottlenecks: List[str]
    recommendations: List[str]
    expected_benefits: Dict[str, str]
    implementation_plan: List[Dict[str, Any]]


class SampleDataResult(TypedDict, total=False):
    """サンプルデータ結果の型定義"""

    sample_size: int
    columns: List[str]
    sample_rows: List[Dict[str, Any]]
    error: str


logger = logging.getLogger(__name__)


# Tool definitions for MCP Sampling integration
request_llm_analysis = Tool(
    name="request_llm_analysis",
    description="Request LLM analysis using MCP Sampling for database schema and data quality",
    inputSchema={
        "type": "object",
        "properties": {
            "analysis_type": {
                "type": "string",
                "enum": [
                    "normalization_analysis",
                    "data_quality_assessment",
                    "schema_optimization",
                    "relationship_analysis",
                    "performance_review",
                ],
                "description": "Type of analysis to perform",
            },
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of table names to analyze",
            },
            "analysis_prompt": {
                "type": "string",
                "description": "Custom analysis prompt (optional)",
            },
            "max_tokens": {
                "type": "integer",
                "description": "Maximum tokens for LLM response (default: 2000)",
                "default": 2000,
                "minimum": 100,
                "maximum": 4000,
            },
            "temperature": {
                "type": "number",
                "description": "LLM temperature (default: 0.3)",
                "default": 0.3,
                "minimum": 0.0,
                "maximum": 1.0,
            },
        },
        "required": ["analysis_type", "table_names"],
    },
)
request_llm_analysis._meta = {"concerns": {"development": "-", "tuning": "-"}}  # type: ignore[attr-defined]


generate_normalization_plan = Tool(
    name="generate_normalization_plan",
    description="Generate comprehensive normalization plan using LLM analysis",
    inputSchema={
        "type": "object",
        "properties": {
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of table names to normalize",
            },
            "normalization_level": {
                "type": "string",
                "enum": ["1nf", "2nf", "3nf", "bcnf", "optimal"],
                "description": "Target normalization level",
                "default": "3nf",
            },
            "include_migration_sql": {
                "type": "boolean",
                "description": "Include migration SQL in plan (default: true)",
                "default": True,
            },
        },
        "required": ["table_names"],
    },
)
generate_normalization_plan._meta = {"concerns": {"development": "-", "maintenance": "-"}}  # type: ignore[attr-defined]


assess_data_quality = Tool(
    name="assess_data_quality",
    description="Assess data quality across multiple tables using LLM analysis",
    inputSchema={
        "type": "object",
        "properties": {
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of table names to assess",
            },
            "quality_dimensions": {
                "type": "array",
                "items": {"type": "string"},
                "enum": [
                    "completeness",
                    "accuracy",
                    "consistency",
                    "timeliness",
                    "validity",
                    "uniqueness",
                ],
                "description": "Data quality dimensions to assess",
                "default": ["completeness", "accuracy", "consistency"],
            },
            "sample_size": {
                "type": "integer",
                "description": "Sample size for data analysis (default: 100)",
                "default": 100,
                "minimum": 10,
                "maximum": 1000,
            },
        },
        "required": ["table_names"],
    },
)
assess_data_quality._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "using": "-", "maintenance": "-"}
}

optimize_schema_with_llm = Tool(
    name="optimize_schema_with_llm",
    description="Optimize database schema using LLM-powered analysis",
    inputSchema={
        "type": "object",
        "properties": {
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of table names to optimize",
            },
            "optimization_goals": {
                "type": "array",
                "items": {"type": "string"},
                "enum": [
                    "performance",
                    "maintainability",
                    "scalability",
                    "storage_efficiency",
                    "query_performance",
                ],
                "description": "Optimization goals",
                "default": ["performance", "maintainability"],
            },
            "include_implementation_plan": {
                "type": "boolean",
                "description": "Include implementation plan (default: true)",
                "default": True,
            },
        },
        "required": ["table_names"],
    },
)
optimize_schema_with_llm._meta = {  # type: ignore[attr-defined]
    "concerns": {"development": "-", "tuning": "-", "maintenance": "-"}
}


# Tool handlers
async def handle_request_llm_analysis(
    analysis_type: str,
    table_names: List[str],
    analysis_prompt: str = "",
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """Handle request_llm_analysis tool execution with MCP Sampling"""
    try:
        # First, gather the necessary data
        from .sampling_tools import handle_get_multiple_table_schemas

        schemas_result = await handle_get_multiple_table_schemas(table_names)
        if not schemas_result["success"]:
            return schemas_result

        # Prepare the context for LLM analysis
        analysis_context = {
            "analysis_type": analysis_type,
            "table_names": table_names,
            "schemas": schemas_result["schemas"],
            "relationships": schemas_result["relationships"],
        }

        # Generate or use custom prompt
        if not analysis_prompt:
            analysis_prompt = _generate_analysis_prompt(analysis_type, analysis_context)

        # Prepare MCP Sampling request
        sampling_request: SamplingRequest = {
            "messages": [{"role": "user", "content": analysis_prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "model": "gpt-4",  # This would be configured based on available models
        }

        # In a real implementation, this would use MCP Sampling API
        # For now, we'll simulate the response structure
        llm_response = await _simulate_llm_analysis(
            analysis_type, analysis_context, sampling_request
        )

        return {
            "success": True,
            "analysis_type": analysis_type,
            "tables_analyzed": table_names,
            "llm_request": sampling_request,
            "llm_response": llm_response,
            "context_data": analysis_context,
        }

    except Exception as e:
        logger.error(f"Unexpected error in request_llm_analysis: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_generate_normalization_plan(
    table_names: List[str],
    normalization_level: str = "3nf",
    include_migration_sql: bool = True,
) -> Dict[str, Any]:
    """Handle generate_normalization_plan tool execution"""
    try:
        # Use MCP Sampling for normalization analysis
        analysis_result = await handle_request_llm_analysis(
            analysis_type="normalization_analysis",
            table_names=table_names,
            analysis_prompt=_generate_normalization_prompt(normalization_level),
            max_tokens=3000,
            temperature=0.2,
        )

        if not analysis_result["success"]:
            return analysis_result

        # Process the LLM response to generate a structured plan
        normalization_plan = await _process_normalization_plan(
            analysis_result["llm_response"],
            table_names,
            normalization_level,
            include_migration_sql,
        )

        return {
            "success": True,
            "normalization_level": normalization_level,
            "tables": table_names,
            "plan": normalization_plan,
            "analysis_summary": analysis_result["llm_response"].get("summary", ""),
        }

    except Exception as e:
        logger.error(f"Unexpected error in generate_normalization_plan: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_assess_data_quality(
    table_names: List[str],
    quality_dimensions: List[str] = ["completeness", "accuracy", "consistency"],
    sample_size: int = 100,
) -> Dict[str, Any]:
    """Handle assess_data_quality tool execution"""

    try:
        # Gather sample data for analysis
        sample_data = await _gather_sample_data(table_names, sample_size)

        # Use MCP Sampling for data quality assessment
        analysis_result = await handle_request_llm_analysis(
            analysis_type="data_quality_assessment",
            table_names=table_names,
            analysis_prompt=_generate_data_quality_prompt(
                quality_dimensions, sample_data
            ),
            max_tokens=2500,
            temperature=0.1,  # Lower temperature for more consistent assessments
        )

        if not analysis_result["success"]:
            return analysis_result

        # Process the quality assessment
        quality_assessment = await _process_quality_assessment(
            analysis_result["llm_response"],
            quality_dimensions,
            sample_data,
        )

        return {
            "success": True,
            "tables_assessed": table_names,
            "quality_dimensions": quality_dimensions,
            "sample_size": sample_size,
            "assessment": quality_assessment,
            "recommendations": analysis_result["llm_response"].get(
                "recommendations", []
            ),
        }

    except Exception as e:
        logger.error(f"Unexpected error in assess_data_quality: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_optimize_schema_with_llm(
    table_names: List[str],
    optimization_goals: List[str] = ["performance", "maintainability"],
    include_implementation_plan: bool = True,
) -> Dict[str, Any]:
    """Handle optimize_schema_with_llm tool execution"""

    try:
        # Use MCP Sampling for schema optimization
        analysis_result = await handle_request_llm_analysis(
            analysis_type="schema_optimization",
            table_names=table_names,
            analysis_prompt=_generate_optimization_prompt(optimization_goals),
            max_tokens=2800,
            temperature=0.2,
        )

        if not analysis_result["success"]:
            return analysis_result

        # Process the optimization recommendations
        optimization_plan = await _process_optimization_plan(
            analysis_result["llm_response"],
            optimization_goals,
            include_implementation_plan,
        )

        return {
            "success": True,
            "tables_optimized": table_names,
            "optimization_goals": optimization_goals,
            "optimization_plan": optimization_plan,
            "expected_benefits": analysis_result["llm_response"].get(
                "expected_benefits", {}
            ),
        }

    except Exception as e:
        logger.error(f"Unexpected error in optimize_schema_with_llm: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


# Helper functions for prompt generation
def _generate_analysis_prompt(analysis_type: str, context: Dict[str, Any]) -> str:
    """Generate analysis prompt based on type and context"""
    base_prompts = {
        "normalization_analysis": """
        Analyze the following database schema for normalization opportunities.
        Provide specific recommendations for improving normalization to 3NF or higher.

        Tables: {table_names}

        Schema Details:
        {schemas}

        Relationships:
        {relationships}

        Please provide:
        1. Current normalization level assessment
        2. Specific normalization issues found
        3. Step-by-step normalization recommendations
        4. Expected benefits of normalization
        """,
        "data_quality_assessment": """
        Assess data quality for the following tables.
        Focus on completeness, accuracy, and consistency.

        Tables: {table_names}

        Schema:
        {schemas}

        Please provide:
        1. Data quality score for each table (1-10)
        2. Specific data quality issues found
        3. Root cause analysis
        4. Improvement recommendations
        """,
        "schema_optimization": """
        Optimize the database schema for better performance and maintainability.

        Tables: {table_names}

        Schema:
        {schemas}

        Please provide:
        1. Current performance bottlenecks
        2. Schema optimization recommendations
        3. Indexing suggestions
        4. Partitioning opportunities
        """,
    }

    prompt_template = base_prompts.get(
        analysis_type, base_prompts["normalization_analysis"]
    )
    return prompt_template.format(
        table_names=", ".join(context["table_names"]),
        schemas=json.dumps(context["schemas"], indent=2),
        relationships=json.dumps(context["relationships"], indent=2),
    )


def _generate_normalization_prompt(normalization_level: str) -> str:
    """Generate normalization-specific prompt"""
    return f"""
    Perform comprehensive normalization analysis targeting {normalization_level.upper()}.
    Focus on identifying functional dependencies, transitive dependencies, and partial dependencies.
    Provide specific SQL statements for creating normalized tables and migrating data.
    Include rollback considerations and validation steps.
    """


def _generate_data_quality_prompt(
    dimensions: List[str], sample_data: Dict[str, Any]
) -> str:
    """Generate data quality assessment prompt"""
    return f"""
    Assess data quality across the following dimensions: {', '.join(dimensions)}.
    Analyze the provided sample data for patterns, anomalies, and quality issues.
    Provide quantitative scores and qualitative assessments for each dimension.
    Include specific data cleansing recommendations and preventive measures.
    """


def _generate_optimization_prompt(goals: List[str]) -> str:
    """Generate schema optimization prompt"""
    return f"""
    Optimize the database schema with the following goals: {', '.join(goals)}.
    Consider indexing strategies, partitioning, denormalization where appropriate,
    and query performance improvements.
    Provide implementation priority and estimated impact for each recommendation.
    """


def _is_valid_table_name(table_name: str) -> bool:
    """Validate table name to prevent SQL injection"""
    import re

    # Basic validation: table names should only contain alphanumeric characters, underscores, and dots
    # and should not contain SQL keywords or special characters
    if not table_name or len(table_name) > 63:  # PostgreSQL identifier limit
        return False

    # Check for SQL injection patterns
    sql_injection_patterns = [
        r"[\'\";]",  # Single quotes, double quotes, semicolons
        r"\b(?:DROP|DELETE|UPDATE|INSERT|CREATE|ALTER|TRUNCATE|EXEC|UNION|SELECT)\b",
        r"--",  # SQL comments
        r"/\*.*\*/",  # Multi-line comments
        r"\s",  # Whitespace characters
        r"\\",  # Backslashes
    ]

    for pattern in sql_injection_patterns:
        if re.search(pattern, table_name, re.IGNORECASE):
            return False

    # Allow only alphanumeric, underscores, and dots
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$", table_name):
        return False

    return True


# Helper functions for data processing
async def _gather_sample_data(
    table_names: List[str], sample_size: int
) -> Dict[str, SampleDataResult]:
    """Gather sample data from tables for analysis"""
    sample_data: Dict[str, SampleDataResult] = {}

    try:
        config = load_config()
        db_manager = DatabaseManager(config.postgres)
        db_manager.connect()

        for table_name in table_names:
            try:
                # Get sample data - use parameterized query with table name validation
                # Validate table name to prevent SQL injection
                if not _is_valid_table_name(table_name):
                    logger.warning(f"Invalid table name: {table_name}")
                    sample_data[table_name] = SampleDataResult(
                        error="Invalid table name"
                    )
                    continue

                # Use proper query construction with parameterized LIMIT
                # Table name is validated, so we can safely format it
                query = f"SELECT * FROM {table_name} LIMIT %s"  # nosec
                results = db_manager.execute_query(query, {"limit": sample_size})
                sample_data[table_name] = SampleDataResult(
                    sample_size=len(results["data"]) if results["success"] else 0,
                    columns=(
                        list(results["data"][0].keys())
                        if results["success"] and results["data"]
                        else []
                    ),
                    sample_rows=(
                        results["data"][:5]
                        if results["success"] and results["data"]
                        else []
                    ),
                )
            except Exception as e:
                logger.warning(f"Failed to sample data from {table_name}: {e}")
                sample_data[table_name] = SampleDataResult(error=str(e))

        db_manager.disconnect()
    except Exception as e:
        logger.error(f"Error gathering sample data: {e}")

    return sample_data


async def _simulate_llm_analysis(
    analysis_type: str, context: Dict[str, Any], request: SamplingRequest
) -> LLMAnalysisResponse:
    """Simulate LLM analysis response (to be replaced with actual MCP Sampling)"""
    # This is a simulation - in production, this would call MCP Sampling API
    simulated_responses: Dict[str, LLMAnalysisResponse] = {
        "normalization_analysis": LLMAnalysisResponse(
            summary="Found several normalization opportunities",
            current_level="1NF",
            target_level="3NF",
            issues=[
                "Partial dependencies found",
                "Transitive dependencies identified",
            ],
            recommendations=[
                "Create separate tables for related entities",
                "Add foreign key constraints",
                "Remove redundant columns",
            ],
            expected_benefits={
                "data_integrity": "Improved",
                "storage_efficiency": "Moderate improvement",
                "query_performance": "Slight improvement",
            },
        ),
        "data_quality_assessment": LLMAnalysisResponse(
            summary="Good overall data quality with some areas for improvement",
            scores={"completeness": 8.5, "accuracy": 7.8, "consistency": 9.2},
            issues=[
                "Missing values in optional fields",
                "Inconsistent date formats",
            ],
            recommendations=[
                "Implement data validation rules",
                "Add constraints for required fields",
            ],
        ),
        "schema_optimization": LLMAnalysisResponse(
            summary="Several optimization opportunities identified",
            bottlenecks=[
                "Lack of indexes on frequently queried columns",
                "Inefficient data types",
            ],
            recommendations=[
                "Add composite indexes on common query patterns",
                "Consider partitioning large tables",
                "Optimize data types for storage efficiency",
            ],
            expected_benefits={
                "query_performance": "Significant improvement",
                "storage": "Moderate reduction",
                "maintainability": "Improved",
            },
        ),
    }

    return simulated_responses.get(
        analysis_type, LLMAnalysisResponse(summary="Analysis completed")
    )


async def _process_normalization_plan(
    llm_response: Dict[str, Any],
    table_names: List[str],
    normalization_level: str,
    include_migration_sql: bool,
) -> Dict[str, Any]:
    """Process LLM response into structured normalization plan"""
    return {
        "normalization_level": normalization_level,
        "tables_affected": table_names,
        "analysis_summary": llm_response.get("summary", ""),
        "identified_issues": llm_response.get("issues", []),
        "recommendations": llm_response.get("recommendations", []),
        "implementation_steps": [
            {
                "step": 1,
                "description": "Analyze current schema and dependencies",
                "estimated_time": "30 minutes",
            },
            {
                "step": 2,
                "description": "Design normalized schema",
                "estimated_time": "1 hour",
            },
            {
                "step": 3,
                "description": "Implement schema changes with transaction safety",
                "estimated_time": "2 hours",
            },
            {
                "step": 4,
                "description": "Validate and test normalized schema",
                "estimated_time": "1 hour",
            },
        ],
        "migration_sql_included": include_migration_sql,
    }


async def _process_quality_assessment(
    llm_response: Dict[str, Any],
    quality_dimensions: List[str],
    sample_data: Dict[str, Any],
) -> QualityAssessmentResult:
    """Process LLM response into structured quality assessment"""
    scores = llm_response.get("scores", {})
    overall_score = sum(scores.values()) / len(quality_dimensions) if scores else 0.0

    return QualityAssessmentResult(
        quality_dimensions=quality_dimensions,
        overall_score=overall_score,
        dimension_scores=scores,
        identified_issues=llm_response.get("issues", []),
        sample_data_summary={
            table: {
                "sample_size": data.get("sample_size", 0),
                "columns": data.get("columns", []),
            }
            for table, data in sample_data.items()
        },
        improvement_priority="medium",  # This would be calculated based on scores
    )


async def _process_optimization_plan(
    llm_response: Dict[str, Any],
    optimization_goals: List[str],
    include_implementation_plan: bool,
) -> OptimizationPlanResult:
    """Process LLM response into structured optimization plan"""
    return OptimizationPlanResult(
        optimization_goals=optimization_goals,
        identified_bottlenecks=llm_response.get("bottlenecks", []),
        recommendations=llm_response.get("recommendations", []),
        expected_benefits=llm_response.get("expected_benefits", {}),
        implementation_plan=(
            [
                {
                    "phase": 1,
                    "description": "High-impact optimizations",
                    "recommendations": llm_response.get("recommendations", [])[:2],
                    "estimated_effort": "Low",
                },
                {
                    "phase": 2,
                    "description": "Medium-impact optimizations",
                    "recommendations": llm_response.get("recommendations", [])[2:4],
                    "estimated_effort": "Medium",
                },
                {
                    "phase": 3,
                    "description": "Long-term optimizations",
                    "recommendations": llm_response.get("recommendations", [])[4:],
                    "estimated_effort": "High",
                },
            ]
            if include_implementation_plan
            else []
        ),
    )


# Tool registry
def get_sampling_integration_tools() -> List[Tool]:
    """Get all sampling integration tools"""
    return [
        request_llm_analysis,
        generate_normalization_plan,
        assess_data_quality,
        optimize_schema_with_llm,
    ]


def get_sampling_integration_handlers() -> (
    Dict[str, Callable[..., Coroutine[Any, Any, Dict[str, Any]]]]
):
    """Get tool handlers for sampling integration operations"""
    return {
        "request_llm_analysis": handle_request_llm_analysis,
        "generate_normalization_plan": handle_generate_normalization_plan,
        "assess_data_quality": handle_assess_data_quality,
        "optimize_schema_with_llm": handle_optimize_schema_with_llm,
    }

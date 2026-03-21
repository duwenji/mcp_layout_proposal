"""
Elicitation tools for PostgreSQL MCP Server

This module provides interactive elicitation tools for guided
data analysis and exploration through conversation.
"""

import logging
from typing import Any, Dict, List, Callable, Coroutine, Optional
from mcp import Tool

logger = logging.getLogger(__name__)


# Tool definitions for elicitation operations
interactive_data_exploration = Tool(
    name="interactive_data_exploration",
    description="Interactive data exploration with guided conversation",
    inputSchema={
        "type": "object",
        "properties": {
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of table names to explore",
            },
            "exploration_focus": {
                "type": "string",
                "enum": [
                    "schema_analysis",
                    "data_quality",
                    "relationships",
                    "performance",
                    "general",
                ],
                "description": "Focus area for exploration",
                "default": "general",
            },
            "conversation_context": {
                "type": "string",
                "description": "Previous conversation context for continuity",
            },
        },
        "required": ["table_names"],
    },
)
interactive_data_exploration._meta = {"concerns": {"development": "-", "using": "-"}}  # type: ignore[attr-defined]


guided_analysis_workflow = Tool(
    name="guided_analysis_workflow",
    description="Step-by-step guided analysis workflow with user interaction",
    inputSchema={
        "type": "object",
        "properties": {
            "analysis_type": {
                "type": "string",
                "enum": [
                    "normalization",
                    "data_quality",
                    "performance",
                    "schema_optimization",
                ],
                "description": "Type of analysis to perform",
            },
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of table names to analyze",
            },
            "current_step": {
                "type": "integer",
                "description": "Current step in the workflow (for continuation)",
                "default": 1,
            },
            "user_responses": {
                "type": "object",
                "description": "User responses to previous questions",
            },
        },
        "required": ["analysis_type", "table_names"],
    },
)
guided_analysis_workflow._meta = {"concerns": {"development": "-", "using": "-"}}  # type: ignore[attr-defined]


clarify_analysis_requirements = Tool(
    name="clarify_analysis_requirements",
    description="Clarify analysis requirements through interactive questioning",
    inputSchema={
        "type": "object",
        "properties": {
            "initial_request": {
                "type": "string",
                "description": "User's initial analysis request",
            },
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of table names involved",
            },
            "clarification_context": {
                "type": "object",
                "description": "Context from previous clarification rounds",
            },
        },
        "required": ["initial_request", "table_names"],
    },
)
clarify_analysis_requirements._meta = {"concerns": {"development": "-", "using": "-"}}  # type: ignore[attr-defined]


# Tool handlers
async def handle_interactive_data_exploration(
    table_names: List[str],
    exploration_focus: str = "general",
    conversation_context: str = "",
) -> Dict[str, Any]:
    """Handle interactive_data_exploration tool execution"""
    try:
        # Get schema information
        from .sampling_tools import handle_get_multiple_table_schemas

        schemas_result = await handle_get_multiple_table_schemas(table_names)
        if not schemas_result["success"]:
            return schemas_result

        # Generate conversation based on focus
        conversation = await _generate_exploration_conversation(
            table_names, exploration_focus, schemas_result, conversation_context
        )

        return {
            "success": True,
            "conversation": conversation,
            "tables_explored": table_names,
            "exploration_focus": exploration_focus,
            "next_questions": conversation.get("next_questions", []),
            "suggested_analyses": conversation.get("suggested_analyses", []),
        }

    except Exception as e:
        logger.error(f"Unexpected error in interactive_data_exploration: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_guided_analysis_workflow(
    analysis_type: str,
    table_names: List[str],
    current_step: int = 1,
    user_responses: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Handle guided_analysis_workflow tool execution"""
    try:
        user_responses = user_responses or {}

        # Get workflow definition
        workflow = _get_analysis_workflow(analysis_type, table_names)

        if current_step > len(workflow["steps"]):
            return {
                "success": True,
                "workflow_complete": True,
                "analysis_summary": workflow.get("summary", ""),
                "recommendations": workflow.get("recommendations", []),
            }

        current_step_info = workflow["steps"][current_step - 1]

        # Process current step
        step_result = await _process_workflow_step(
            current_step_info, table_names, user_responses, current_step
        )

        return {
            "success": True,
            "workflow": {
                "analysis_type": analysis_type,
                "current_step": current_step,
                "total_steps": len(workflow["steps"]),
                "step_info": current_step_info,
                "step_result": step_result,
                "next_step_available": current_step < len(workflow["steps"]),
            },
            "user_questions": step_result.get("questions", []),
            "data_collected": step_result.get("data_collected", {}),
        }

    except Exception as e:
        logger.error(f"Unexpected error in guided_analysis_workflow: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


async def handle_clarify_analysis_requirements(
    initial_request: str,
    table_names: List[str],
    clarification_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Handle clarify_analysis_requirements tool execution"""
    try:
        clarification_context = clarification_context or {}

        # Get schema context
        from .sampling_tools import handle_get_multiple_table_schemas

        schemas_result = await handle_get_multiple_table_schemas(table_names)

        # Generate clarification questions
        clarification = await _generate_clarification_questions(
            initial_request, table_names, schemas_result, clarification_context
        )

        return {
            "success": True,
            "clarification_round": clarification_context.get("round", 1) + 1,
            "questions": clarification["questions"],
            "context_summary": clarification["context_summary"],
            "suggested_approach": clarification["suggested_approach"],
            "remaining_ambiguities": clarification["remaining_ambiguities"],
        }

    except Exception as e:
        logger.error(f"Unexpected error in clarify_analysis_requirements: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


# Helper functions for elicitation
async def _generate_exploration_conversation(
    table_names: List[str],
    focus: str,
    schemas_result: Dict[str, Any],
    context: str = "",
) -> Dict[str, Any]:
    """Generate interactive exploration conversation"""

    focus_prompts = {
        "schema_analysis": {
            "initial_questions": [
                "What specific aspects of the schema are you most interested in?",
                "Are you looking to understand table relationships, column types, or constraints?",
                "Do you have any concerns about the current schema design?",
            ],
            "suggested_analyses": [
                "Table relationship analysis",
                "Data type optimization review",
                "Constraint validation check",
            ],
        },
        "data_quality": {
            "initial_questions": [
                "What data quality dimensions are most important to you?",
                "Do you have specific data quality issues you've observed?",
                "Are you concerned about completeness, accuracy, or consistency?",
            ],
            "suggested_analyses": [
                "Completeness assessment",
                "Data validation rule analysis",
                "Anomaly detection",
            ],
        },
        "relationships": {
            "initial_questions": [
                "Are you interested in foreign key relationships or logical dependencies?",
                "Do you need to understand how tables connect for reporting or analysis?",
                "Are there specific relationship patterns you're looking for?",
            ],
            "suggested_analyses": [
                "Foreign key relationship mapping",
                "Data dependency analysis",
                "Join pattern optimization",
            ],
        },
        "performance": {
            "initial_questions": [
                "What performance issues have you observed?",
                "Are you concerned about query speed, storage, or scalability?",
                "Do you have specific queries that are running slowly?",
            ],
            "suggested_analyses": [
                "Query performance analysis",
                "Index optimization review",
                "Storage efficiency assessment",
            ],
        },
        "general": {
            "initial_questions": [
                "What would you like to learn about your database?",
                "Are there specific business questions you're trying to answer?",
                "What's your primary goal for this analysis?",
            ],
            "suggested_analyses": [
                "Comprehensive schema overview",
                "Data exploration and profiling",
                "Business intelligence readiness assessment",
            ],
        },
    }

    focus_config = focus_prompts.get(focus, focus_prompts["general"])

    return {
        "welcome_message": f"Let's explore your database tables: {', '.join(table_names)}",
        "focus_area": focus,
        "initial_questions": focus_config["initial_questions"],
        "suggested_analyses": focus_config["suggested_analyses"],
        "schema_summary": f"Found {len(table_names)} tables with various relationships",
        "next_questions": [
            "Which of these areas would you like to explore first?",
            "Do you have any specific questions about the data?",
            "Would you like me to suggest an analysis based on your goals?",
        ],
    }


def _get_analysis_workflow(
    analysis_type: str, table_names: List[str]
) -> Dict[str, Any]:
    """Get workflow definition for analysis type"""

    workflows = {
        "normalization": {
            "name": "Database Normalization Analysis",
            "description": "Step-by-step normalization assessment and improvement",
            "steps": [
                {
                    "step": 1,
                    "name": "Current State Assessment",
                    "description": "Analyze current normalization level",
                    "questions": [
                        "What's the primary purpose of these tables?",
                        "Are you experiencing any data redundancy issues?",
                        "Do you have specific update anomaly concerns?",
                    ],
                },
                {
                    "step": 2,
                    "name": "Functional Dependency Analysis",
                    "description": "Identify functional dependencies",
                    "questions": [
                        "Which columns uniquely identify other columns?",
                        "Are there transitive dependencies between columns?",
                        "Do you have partial dependencies in composite keys?",
                    ],
                },
                {
                    "step": 3,
                    "name": "Normalization Plan",
                    "description": "Create normalization improvement plan",
                    "questions": [
                        "What normalization level are you targeting?",
                        "Do you need to maintain backward compatibility?",
                        "What's your timeline for implementation?",
                    ],
                },
            ],
            "summary": "Normalization analysis complete with improvement recommendations",
            "recommendations": [
                "Consider moving to 3NF",
                "Add foreign key constraints",
            ],
        },
        "data_quality": {
            "name": "Data Quality Assessment",
            "description": "Comprehensive data quality evaluation",
            "steps": [
                {
                    "step": 1,
                    "name": "Quality Dimensions",
                    "description": "Define quality assessment criteria",
                    "questions": [
                        "Which quality dimensions are most important?",
                        "Do you have specific data quality thresholds?",
                        "Are there regulatory compliance requirements?",
                    ],
                },
                {
                    "step": 2,
                    "name": "Data Sampling",
                    "description": "Collect and analyze sample data",
                    "questions": [
                        "What sample size would be appropriate?",
                        "Are there specific time periods to focus on?",
                        "Do you want to exclude any data subsets?",
                    ],
                },
                {
                    "step": 3,
                    "name": "Improvement Plan",
                    "description": "Create data quality improvement plan",
                    "questions": [
                        "What's your priority for quality improvements?",
                        "Do you need automated monitoring?",
                        "What resources are available for implementation?",
                    ],
                },
            ],
            "summary": "Data quality assessment complete with improvement roadmap",
            "recommendations": [
                "Implement data validation rules",
                "Add quality monitoring",
            ],
        },
    }

    return workflows.get(analysis_type, workflows["normalization"])


async def _process_workflow_step(
    step_info: Dict[str, Any],
    table_names: List[str],
    user_responses: Dict[str, Any],
    step_number: int,
) -> Dict[str, Any]:
    """Process a single workflow step"""

    # This would gather actual data based on the step
    # For now, return structured response
    return {
        "step_name": step_info["name"],
        "step_description": step_info["description"],
        "questions": step_info.get("questions", []),
        "data_collected": {
            "tables_analyzed": table_names,
            "step_progress": f"Step {step_number} completed",
            "user_input_required": len(step_info.get("questions", [])) > 0,
        },
        "next_actions": ["Proceed to next step", "Review previous responses"],
    }


async def _generate_clarification_questions(
    initial_request: str,
    table_names: List[str],
    schemas_result: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate clarification questions for analysis requirements"""

    # Analyze the request and schema to generate relevant questions
    questions = []

    # Common clarification areas
    if "normalization" in initial_request.lower():
        questions.extend(
            [
                "What specific normalization level are you targeting?",
                "Are you concerned about update anomalies or data redundancy?",
                "Do you need to maintain compatibility with existing applications?",
            ]
        )

    if "performance" in initial_request.lower():
        questions.extend(
            [
                "What specific performance metrics are important?",
                "Are you experiencing slow queries or general slowness?",
                "What's your current database size and growth rate?",
            ]
        )

    if "quality" in initial_request.lower():
        questions.extend(
            [
                "Which data quality dimensions are most critical?",
                "Do you have specific quality thresholds or standards?",
                "Are there regulatory compliance requirements?",
            ]
        )

    # Add schema-specific questions
    if schemas_result.get("schemas"):
        table_count = len(schemas_result["schemas"])
        questions.append(
            f"You have {table_count} tables. Are there specific tables you want to focus on?"
        )

    return {
        "questions": questions,
        "context_summary": f"Clarifying analysis request: {initial_request}",
        "suggested_approach": "Let's start by understanding your specific goals and constraints",
        "remaining_ambiguities": [
            "Analysis scope",
            "Success criteria",
            "Implementation constraints",
        ],
    }


# Tool registry
def get_elicitation_tools() -> List[Tool]:
    """Get all elicitation tools"""
    return [
        interactive_data_exploration,
        guided_analysis_workflow,
        clarify_analysis_requirements,
    ]


def get_elicitation_handlers() -> (
    Dict[str, Callable[..., Coroutine[Any, Any, Dict[str, Any]]]]
):
    """Get tool handlers for elicitation operations"""
    return {
        "interactive_data_exploration": handle_interactive_data_exploration,
        "guided_analysis_workflow": handle_guided_analysis_workflow,
        "clarify_analysis_requirements": handle_clarify_analysis_requirements,
    }

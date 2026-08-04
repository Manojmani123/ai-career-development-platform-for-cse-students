import json
import logging
from typing import Any

from django.conf import settings
from django.utils import timezone
from openai import OpenAI

from career_app.models import InterviewAnswer


logger = logging.getLogger(__name__)


class AIInterviewEvaluationError(Exception):
    """
    Raised when the AI evaluator cannot produce a valid evaluation.
    """


def _clamp_score(value: Any) -> float:
    """
    Convert a value to a score between 0 and 10.
    """

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return 0.0

    return round(
        max(0.0, min(10.0, numeric_value)),
        2,
    )


def _safe_text(
    value: Any,
    default: str = "",
) -> str:
    """
    Return a safe stripped string.
    """

    if value is None:
        return default

    return str(value).strip()


def _get_optional_name(
    value: Any,
    field_name: str,
    default: str = "Not specified",
) -> str:
    """
    Read a field from an optional related model.
    """

    if value is None:
        return default

    result = getattr(
        value,
        field_name,
        default,
    )

    return _safe_text(
        result,
        default,
    )


def _format_list(values: list[str]) -> str:
    """
    Convert a list into readable evidence text.
    """

    cleaned_values = [
        _safe_text(value)
        for value in values
        if _safe_text(value)
    ]

    if not cleaned_values:
        return "None listed"

    return ", ".join(cleaned_values)


def _build_evaluation_context(
    interview_answer: InterviewAnswer,
) -> dict[str, Any]:
    """
    Build the verified evidence supplied to the AI evaluator.

    Anything not present in this context must be treated as unknown.
    """

    question = interview_answer.question
    session = question.session
    project = session.project
    job_role = session.job_role

    project_skills = list(
        project.skills_used.order_by(
            "skill_name"
        ).values_list(
            "skill_name",
            flat=True,
        )
    )

    project_tools = list(
        project.tools_used.order_by(
            "tool_name"
        ).values_list(
            "tool_name",
            flat=True,
        )
    )

    expected_skill = _get_optional_name(
        question.expected_skill,
        "skill_name",
    )

    expected_tool = _get_optional_name(
        question.expected_tool,
        "tool_name",
    )

    competency_group = _get_optional_name(
        question.competency_group,
        "group_name",
    )

    return {
        "job_role": _safe_text(
            job_role.role_name
        ),
        "project_title": _safe_text(
            project.title
        ),
        "project_description": _safe_text(
            getattr(project, "description", "")
        ),
        "project_url": _safe_text(
            getattr(project, "project_url", "")
        ),
        "github_url": _safe_text(
            getattr(project, "github_url", "")
        ),
        "project_skills": project_skills,
        "project_tools": project_tools,
        "question_type": _safe_text(
            question.question_type
        ),
        "difficulty": _safe_text(
            question.difficulty
        ),
        "question_text": _safe_text(
            question.question_text
        ),
        "expected_skill": expected_skill,
        "expected_tool": expected_tool,
        "competency_group": competency_group,
        "candidate_answer": _safe_text(
            interview_answer.answer_text
        ),
    }


def _build_system_prompt() -> str:
    """
    System instructions for grounded interview evaluation.
    """

    return """
You are an evidence-based technical interview evaluator for
Computer Science students.

Your role is to evaluate interview answers fairly, consistently
and critically.

You are an evaluator. You must not invent better project details,
candidate responsibilities or unsupported achievements.

Evaluate whether the candidate:

1. Answers the interview question directly.
2. Demonstrates technically correct knowledge.
3. Provides evidence consistent with the selected project.
4. Demonstrates the expected skill, tool or competency.
5. Explains technical reasoning, decisions and trade-offs.
6. Communicates clearly and professionally.

GENERAL RULES:

- Do not reward an answer merely because it is long.
- Do not reward keyword stuffing.
- Base every judgement only on:
  1. the interview question,
  2. the supplied project evidence,
  3. the candidate answer.
- Treat information that is not supplied as unknown.
- Never rely on unsupported assumptions.

PROJECT QUESTIONS:

For PROJECT questions, evaluate:

- project context,
- personal contribution,
- technical implementation,
- challenges,
- solutions,
- testing,
- outcomes,
- lessons learned.

Do not award project-evidence marks for general theory alone.

BEHAVIOURAL QUESTIONS:

For BEHAVIOURAL questions, prioritise:

- situation and context,
- personal responsibility,
- action taken,
- decision-making,
- communication,
- reflection,
- outcome.

Technical depth is secondary.

Use STAR as a guide, but do not require the candidate to explicitly
use the words Situation, Task, Action and Result.

HYPOTHETICAL QUESTIONS:

System-design, technical, weakness-focused and architecture questions
may legitimately use wording such as:

"I would deploy"
"I would configure"
"I would use"
"I would design"

Do not penalise a hypothetical architecture answer merely because it
describes future implementation rather than completed past work.

However, hypothetical plans must not be treated as proof that the
candidate already completed that work.

STRICT EVIDENCE RULES:

Never invent or infer unsupported:

- technologies,
- programming languages,
- frameworks,
- cloud providers,
- cloud services,
- APIs,
- API endpoints,
- algorithms,
- datasets,
- databases,
- architecture decisions,
- project features,
- responsibilities,
- team activities,
- testing methods,
- deployment methods,
- metrics,
- achievements,
- measurable results,
- project outcomes.

A factual claim may only be used when it appears in:

1. the supplied project evidence, or
2. the candidate answer.

Project skills and tools are labels only.

A listed skill or tool proves only that it was associated with the
project. It does not prove:

- how the skill was used,
- which feature used it,
- what the candidate implemented,
- what technical decisions were made,
- how the work was tested,
- what results were achieved.

Do not infer project functionality from the project title.

When evidence is missing:

- reduce the evidence score,
- explicitly state what evidence is missing,
- never fabricate evidence.

SCORING RULES:

Every score must be between 0 and 10.

Meaningless, random or irrelevant text must receive scores close
to zero.

Extremely vague or unsupported answers must receive low scores.

Do not compensate for missing evidence by making assumptions.

Technically correct, relevant and well-supported answers should
receive appropriately high scores.

The overall score must be consistent with the four component scores.

OUTPUT RULES:

Return only valid JSON.

Do not return Markdown.

Do not return code fences.

Do not include explanations outside the JSON.

The JSON must strictly follow the requested schema.
""".strip()


def _build_user_prompt(
    context: dict[str, Any],
) -> str:
    """
    Build the candidate-specific evaluation prompt.
    """

    return f"""
Evaluate the following interview answer.

VERIFIED CONTEXT

TARGET JOB ROLE:
{context['job_role']}

SELECTED PROJECT TITLE:
{context['project_title']}

PROJECT DESCRIPTION:
{context['project_description'] or 'No description provided'}

PROJECT WEBSITE:
{context['project_url'] or 'Not provided'}

PROJECT GITHUB URL:
{context['github_url'] or 'Not provided'}

PROJECT SKILL LABELS:
{_format_list(context['project_skills'])}

PROJECT TOOL LABELS:
{_format_list(context['project_tools'])}

QUESTION TYPE:
{context['question_type']}

DIFFICULTY:
{context['difficulty']}

EXPECTED SKILL:
{context['expected_skill']}

EXPECTED TOOL:
{context['expected_tool']}

COMPETENCY GROUP:
{context['competency_group']}

QUESTION:
{context['question_text']}

CANDIDATE ANSWER:
{context['candidate_answer']}

Return exactly this JSON structure:

{{
    "technical_accuracy_score": 0,
    "evidence_consistency_score": 0,
    "competency_score": 0,
    "communication_score": 0,
    "overall_score": 0,
    "technical_feedback": "",
    "communication_feedback": "",
    "strengths": [],
    "weaknesses": [],
    "feedback": "",
    "recommendation": []
}}

STRICT OUTPUT REQUIREMENTS:

- Return valid JSON only.
- Do not include Markdown.
- Do not include code fences.
- Every score must be a number from 0 to 10.
- strengths must contain between 1 and 5 concise items.
- weaknesses must contain between 1 and 5 concise items.
- recommendation must contain between 1 and 5 actionable items.
- overall_score must reasonably reflect the component scores.

STRICT EVIDENCE REQUIREMENTS:

Base the evaluation only on:

1. the candidate answer,
2. the supplied project description,
3. the listed project skills and tools,
4. the question and expected competency.

Treat all other information as unknown.

Project skills and tools are labels only.

Do not expand a listed skill or tool into specific:

- responsibilities,
- implementation details,
- endpoints,
- architecture,
- testing,
- results.

Do not infer project functionality from the project title.

Never invent:

- technologies,
- frameworks,
- cloud services,
- algorithms,
- endpoints,
- databases,
- responsibilities,
- team activities,
- testing methods,
- deployment methods,
- metrics,
- achievements,
- project features,
- outcomes.

If evidence is missing:

- reduce the evidence score,
- state exactly what evidence is missing,
- do not fill the gap with assumptions.

SCORING REQUIREMENTS:

- Random or meaningless text must receive scores close to zero.
- Long answers must not automatically receive high scores.
- Keyword stuffing must not receive high scores.
- Hypothetical system-design answers may receive strong technical
  scores when their reasoning is correct and relevant.
- Hypothetical plans must not receive past-project evidence credit.
- Behavioural answers should prioritise ownership, action, reflection,
  structure and outcome.
- Technically strong but unsupported claims should receive a strong
  technical score but a lower evidence-consistency score.
""".strip()


def _extract_json_text(
    response_text: str,
) -> str:
    """
    Remove accidental code-fence wrapping before JSON parsing.
    """

    cleaned_text = _safe_text(
        response_text
    )

    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]

    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]

    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]

    return cleaned_text.strip()


def _parse_ai_response(
    response_text: str,
) -> dict[str, Any]:
    """
    Parse and validate the AI JSON response.
    """

    cleaned_text = _extract_json_text(
        response_text
    )

    try:
        data = json.loads(
            cleaned_text
        )
    except json.JSONDecodeError as error:
        raise AIInterviewEvaluationError(
            "The AI evaluator returned invalid JSON."
        ) from error

    if not isinstance(data, dict):
        raise AIInterviewEvaluationError(
            "The AI evaluator response must be a JSON object."
        )

    required_fields = {
        "technical_accuracy_score",
        "evidence_consistency_score",
        "competency_score",
        "communication_score",
        "overall_score",
        "technical_feedback",
        "communication_feedback",
        "strengths",
        "weaknesses",
        "feedback",
        "recommendation",
    }

    missing_fields = required_fields.difference(
        data.keys()
    )

    if missing_fields:
        raise AIInterviewEvaluationError(
            "The AI response is missing required fields: "
            + ", ".join(
                sorted(missing_fields)
            )
        )

    return data


def _normalise_list(
    value: Any,
) -> list[str]:
    """
    Convert the AI response into a cleaned list of strings.
    """

    if isinstance(value, list):
        values = value

    elif value is None:
        values = []

    else:
        values = [value]

    cleaned_values = []

    for item in values:
        cleaned_item = _safe_text(
            item
        )

        if cleaned_item:
            cleaned_values.append(
                cleaned_item
            )

    return cleaned_values[:5]


def _ensure_non_empty_list(
    values: list[str],
    fallback: str,
) -> list[str]:
    """
    Ensure list fields contain at least one value.
    """

    if values:
        return values

    return [fallback]


def _build_safe_improved_answer(
    context: dict[str, Any],
) -> str:
    """
    Produce a deterministic, grounded answer scaffold.

    The AI is not used to produce the saved improved answer because
    generative rewrites may introduce unsupported project claims.
    """

    candidate_answer = _safe_text(
        context["candidate_answer"]
    )

    word_count = len(
        candidate_answer.split()
    )

    question_type = context[
        "question_type"
    ].upper()

    if word_count < 8:
        return "\n".join([
            f"Project title: {context['project_title']}",
            "",
            "Project problem:",
            "[Describe the actual project problem]",
            "",
            "Intended users:",
            "[State the actual intended users]",
            "",
            "Personal contribution:",
            "[Describe your personal contribution]",
            "",
            "Technologies used:",
            "[State the technologies actually used]",
            "",
            "Implementation:",
            "[Describe the real implementation]",
            "",
            "Challenge:",
            "[Describe the actual challenge]",
            "",
            "Testing:",
            "[Explain how the solution was tested]",
            "",
            "Outcome:",
            "[State the actual outcome]",
        ])

    if question_type == "BEHAVIOURAL":
        guidance = [
            "Improve the answer using STAR:",
            "",
            "Situation:",
            "[Clarify the real context and feedback received]",
            "",
            "Task:",
            "[State your actual responsibility]",
            "",
            "Action:",
            "[Explain exactly what you personally did]",
            "",
            "Result:",
            "[State the real result and lesson learned]",
        ]

    elif question_type == "SYSTEM_DESIGN":
        guidance = [
            "Strengthen the answer with:",
            "",
            "Architecture scope:",
            "[Clarify the actual scale, users and constraints]",
            "",
            "Technical decisions:",
            "[Explain why each proposed component was selected]",
            "",
            "Security and reliability:",
            "[Add the relevant security, availability and recovery decisions]",
            "",
            "Validation:",
            "[Explain how the architecture would be tested or monitored]",
            "",
            "Trade-offs:",
            "[Explain the real cost, complexity or performance trade-offs]",
        ]

    elif question_type == "PROJECT":
        guidance = [
            "Strengthen the project evidence with:",
            "",
            "Project context:",
            "[Describe the actual problem and intended users]",
            "",
            "Personal responsibility:",
            "[Clarify what you personally implemented]",
            "",
            "Technical approach:",
            "[Explain the actual technologies and decisions used]",
            "",
            "Challenge and solution:",
            "[Describe a real challenge and how you solved it]",
            "",
            "Validation and outcome:",
            "[Explain how the solution was tested and the real result]",
        ]

    elif question_type == "TOOL":
        guidance = [
            "Strengthen the answer with:",
            "",
            "Tool purpose:",
            "[Explain the tool's role in this project]",
            "",
            "Integration:",
            "[Describe the real or proposed integration steps]",
            "",
            "Selection reasoning:",
            "[Explain why the tool was appropriate]",
            "",
            "Validation:",
            "[Explain how the integration would be verified]",
            "",
            "Limitations:",
            "[State a relevant limitation or trade-off]",
        ]

    else:
        guidance = [
            "Strengthen the answer with:",
            "",
            "Concept:",
            "[Define the expected skill or competency clearly]",
            "",
            "Project application:",
            "[Explain how it applies to the selected project]",
            "",
            "Implementation:",
            "[Describe the real or proposed implementation steps]",
            "",
            "Reasoning:",
            "[Explain the technical decisions and trade-offs]",
            "",
            "Validation and outcome:",
            "[Explain how it would be tested and what outcome is expected]",
        ]

    return "\n".join([
        "Current answer:",
        "",
        candidate_answer,
        "",
        *guidance,
    ])


def evaluate_answer_with_ai(
    interview_answer: InterviewAnswer,
) -> InterviewAnswer:
    """
    Evaluate one InterviewAnswer using OpenAI.

    AI is used for scoring, feedback, strengths, weaknesses and
    recommendations.

    The improved answer is generated deterministically to prevent
    unsupported claims.
    """

    if not isinstance(
        interview_answer,
        InterviewAnswer,
    ):
        raise TypeError(
            "interview_answer must be an InterviewAnswer instance."
        )

    answer_text = _safe_text(
        interview_answer.answer_text
    )

    if not answer_text:
        raise ValueError(
            "The interview answer cannot be empty."
        )

    api_key = _safe_text(
        getattr(
            settings,
            "OPENAI_API_KEY",
            "",
        )
    )

    if not api_key:
        raise AIInterviewEvaluationError(
            "OPENAI_API_KEY is not configured."
        )

    client = OpenAI(
        api_key=api_key
    )

    context = _build_evaluation_context(
        interview_answer
    )

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            instructions=_build_system_prompt(),
            input=_build_user_prompt(context),
        )

        response_text = _safe_text(
            response.output_text
        )

    except Exception as error:
        logger.exception(
            "OpenAI interview evaluation failed."
        )

        raise AIInterviewEvaluationError(
            "The AI evaluation request failed."
        ) from error

    if not response_text:
        raise AIInterviewEvaluationError(
            "The AI evaluator returned an empty response."
        )

    data = _parse_ai_response(
        response_text
    )

    strengths = _ensure_non_empty_list(
        _normalise_list(
            data["strengths"]
        ),
        "The candidate attempted to answer the question.",
    )

    weaknesses = _ensure_non_empty_list(
        _normalise_list(
            data["weaknesses"]
        ),
        "The answer needs more specific supporting evidence.",
    )

    recommendations = _ensure_non_empty_list(
        _normalise_list(
            data["recommendation"]
        ),
        "Add specific, truthful evidence from the project.",
    )

    improved_answer = _build_safe_improved_answer(
        context
    )

    interview_answer.technical_accuracy_score = (
        _clamp_score(
            data["technical_accuracy_score"]
        )
    )

    interview_answer.evidence_consistency_score = (
        _clamp_score(
            data["evidence_consistency_score"]
        )
    )

    interview_answer.competency_score = (
        _clamp_score(
            data["competency_score"]
        )
    )

    interview_answer.communication_score = (
        _clamp_score(
            data["communication_score"]
        )
    )

    interview_answer.overall_score = (
        _clamp_score(
            data["overall_score"]
        )
    )

    interview_answer.technical_feedback = _safe_text(
        data["technical_feedback"],
        "No technical feedback was returned.",
    )

    interview_answer.communication_feedback = _safe_text(
        data["communication_feedback"],
        "No communication feedback was returned.",
    )

    interview_answer.strengths = "\n".join(
        f"• {item}"
        for item in strengths
    )

    interview_answer.weaknesses = "\n".join(
        f"• {item}"
        for item in weaknesses
    )

    interview_answer.feedback = _safe_text(
        data["feedback"],
        "No overall feedback was returned.",
    )

    interview_answer.improved_answer = (
        improved_answer
    )

    interview_answer.recommendation = "\n".join(
        f"• {item}"
        for item in recommendations
    )

    interview_answer.evaluated_at = timezone.now()

    interview_answer.save(
        update_fields=[
            "technical_accuracy_score",
            "evidence_consistency_score",
            "competency_score",
            "communication_score",
            "overall_score",
            "technical_feedback",
            "communication_feedback",
            "strengths",
            "weaknesses",
            "feedback",
            "improved_answer",
            "recommendation",
            "evaluated_at",
        ]
    )

    return interview_answer
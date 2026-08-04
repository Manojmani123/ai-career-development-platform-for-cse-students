import re

from django.utils import timezone


def _clamp_score(value):
    """
    Keep a score between 0 and 10.
    """

    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0

    return round(
        max(0.0, min(10.0, value)),
        2
    )


def _normalise_text(value):
    """
    Convert text into a clean lowercase string.
    """

    return re.sub(
        r'\s+',
        ' ',
        value or ''
    ).strip().lower()


def _contains_any(text, phrases):
    """
    Return True when at least one phrase appears in the text.
    """

    return any(
        phrase in text
        for phrase in phrases
    )


def _calculate_evidence_score(interview_answer):
    """
    Evaluate how much concrete project evidence the answer contains.

    Maximum score: 10

    Criteria:
    - Project connection
    - Personal ownership
    - Specific implementation details
    - Technical reasoning
    - Challenge and solution
    - Testing or validation
    - Result or outcome
    """

    answer_text = _normalise_text(
        interview_answer.answer_text
    )

    if not answer_text:
        return (
            0.0,
            [],
            ['No project evidence was provided.']
        )

    question = interview_answer.question
    project = question.session.project
    question_type = question.question_type

    score = 0.0
    strengths = []
    weaknesses = []

    word_count = len(
        answer_text.split()
    )

    # -------------------------------------------------
    # 1. Project connection: maximum 1.5
    # -------------------------------------------------

    project_title = _normalise_text(
        project.title
    )

    project_description = _normalise_text(
        project.description
    )

    project_words = {
        word
        for word in project_title.split()
        if len(word) >= 4
    }

    description_words = {
        word
        for word in project_description.split()
        if len(word) >= 6
    }

    project_title_matches = sum(
        1
        for word in project_words
        if word in answer_text
    )

    description_matches = sum(
        1
        for word in description_words
        if word in answer_text
    )

    if (
        project_title
        and project_title in answer_text
    ):
        score += 1.5

        strengths.append(
            'The answer is directly connected to the selected project.'
        )

    elif project_title_matches >= 2:
        score += 1.0

        strengths.append(
            'The answer refers to the selected project context.'
        )

    elif description_matches >= 2:
        score += 0.75

        strengths.append(
            'The answer contains details related to the selected project.'
        )

    else:
        weaknesses.append(
            'The answer is not clearly connected to the selected project.'
        )

    # -------------------------------------------------
    # 2. Personal ownership: maximum 1.5
    # -------------------------------------------------

    if question_type in ["PROJECT", "BEHAVIOURAL"]:
        ownership_phrases = [
            "i designed",
            "i implemented",
            "i developed",
            "i created",
            "i configured",
            "i deployed",
            "i tested",
            "i analysed",
            "i analyzed",
            "i diagnosed",
            "i selected",
            "i decided",
            "i built",
            "my responsibility",
            "my contribution",
            "my role",
        ]

    else:
        ownership_phrases = [
        "i would use",
        "i would deploy",
        "i would configure",
        "i would create",
        "i would host",
        "i would implement",
        "i would integrate",
        "i would store",
        "i would secure",
        "i would scale",
        "i would containerise",
        "i would containerize",
        "i would run",
        "i would monitor",
        "i would automate",
        "i would design",
        "i would separate",
        "i would introduce",
    ]

    ownership_matches = sum(
        1
        for phrase in ownership_phrases
        if phrase in answer_text
    )

    if ownership_matches >= 2:
        score += 1.5

        strengths.append(
            'The answer clearly explains the candidate’s personal contribution.'
        )

    elif ownership_matches == 1:
        score += 0.75

    else:
        if question_type in ["PROJECT", "BEHAVIOURAL"]:
            weaknesses.append(
            "The answer does not clearly explain the candidate's personal contribution."
        )
        else:
            weaknesses.append(
            "The proposed implementation could include more concrete implementation steps."
        )

    # -------------------------------------------------
    # 3. Specific implementation: maximum 2
    # -------------------------------------------------

    implementation_phrases = [
        'rest api',
        'api gateway',
        'database',
        'postgresql',
        'mysql',
        'mongodb',
        'redis',
        'docker',
        'kubernetes',
        'aws',
        'azure',
        'google cloud',
        'serverless',
        'lambda',
        'cloudformation',
        'terraform',
        'load balancer',
        'auto scaling',
        'autoscaling',
        'message queue',
        'authentication',
        'authorisation',
        'authorization',
        'cache',
        'caching',
        'microservice',
        'container',
        'monitoring',
        'logging',
        'ci/cd',
        'github actions',
        'jenkins',
        'unit test',
        'integration test',
        'cloudwatch',
        'rds',
        's3',
        'cloudfront',
        'ecs',
        'eks',
        'iam',
        'vpc',
        'security group',
        'read replica',
        'multi-az',
        'object storage',
    ]

    implementation_matches = sum(
        1
        for phrase in implementation_phrases
        if phrase in answer_text
    )

    if implementation_matches >= 5:
        score += 2.0

        strengths.append(
            'The answer includes several concrete implementation details.'
        )

    elif implementation_matches >= 3:
        score += 1.5

    elif implementation_matches >= 1:
        score += 0.75

    else:
        weaknesses.append(
            'The answer contains no specific implementation details.'
        )

    # -------------------------------------------------
    # 4. Technical reasoning: maximum 1.5
    # -------------------------------------------------

    reasoning_phrases = [
        'because',
        'i chose',
        'i selected',
        'the reason',
        'this allowed',
        'this improved',
        'this reduced',
        'this ensured',
        'instead of',
        'the advantage',
        'the benefit',
        'trade-off',
        'tradeoff',
        'suitable because',
        'in order to',
    ]

    reasoning_matches = sum(
        1
        for phrase in reasoning_phrases
        if phrase in answer_text
    )

    if reasoning_matches >= 3:
        score += 1.5

        strengths.append(
            'The answer explains the reasoning behind technical decisions.'
        )

    elif reasoning_matches >= 1:
        score += 0.75

    else:
        weaknesses.append(
            'The answer lists concepts or technologies but does not explain why they were chosen.'
        )

    # -------------------------------------------------
    # 5. Challenge and solution: maximum 1.5
    # -------------------------------------------------

    challenge_phrases = [
        'challenge',
        'problem',
        'issue',
        'bottleneck',
        'failure',
        'error',
        'slow',
        'difficult',
        'limitation',
        'latency',
        'downtime',
    ]

    solution_phrases = [
        'solved',
        'fixed',
        'resolved',
        'improved',
        'optimised',
        'optimized',
        'redesigned',
        'changed',
        'introduced',
        'implemented',
        'separated',
        'cached',
        'scaled',
    ]

    has_challenge = _contains_any(
        answer_text,
        challenge_phrases
    )

    has_solution = _contains_any(
        answer_text,
        solution_phrases
    )

    if has_challenge and has_solution:
        score += 1.5

        strengths.append(
            'The answer explains both a technical challenge and its solution.'
        )

    elif has_challenge or has_solution:
        score += 0.5

    else:
        weaknesses.append(
            'The answer does not include a specific challenge and solution.'
        )

    # -------------------------------------------------
    # 6. Testing or validation: maximum 1
    # -------------------------------------------------
    require_testing = question_type in [
    "PROJECT",
    "SYSTEM_DESIGN",
]
    testing_phrases = [
        'tested',
        'unit test',
        'integration test',
        'load test',
        'performance test',
        'security test',
        'validated',
        'verified',
        'measured',
        'monitored',
        'confirmed',
        'benchmark',
        'health check',
        'alert',
    ]

    if not require_testing:
        score += 1.0
    elif _contains_any(
        answer_text,
        testing_phrases
    ):
        score += 1.0

        strengths.append(
            'The answer explains how the solution was tested, monitored or validated.'
        )

    else:
        weaknesses.append(
            'The answer does not explain how the solution was tested or validated.'
        )

    # -------------------------------------------------
    # 7. Result or outcome: maximum 1
    # -------------------------------------------------

    result_phrases = [
        'the result',
        'as a result',
        'reduced',
        'increased',
        'improved',
        'faster',
        'lower latency',
        'more reliable',
        'scalable',
        'available',
        'successful',
        'performance improved',
        'response time',
        'reduced cost',
        'reduced errors',
        'higher availability',
        'easier to maintain',
    ]

    if _contains_any(
        answer_text,
        result_phrases
    ):
        score += 1.0

        strengths.append(
            'The answer describes a result or practical outcome.'
        )

    else:
        weaknesses.append(
            'The answer does not state the final result or outcome.'
        )

    # Very short answers should not receive a meaningful score.
    if word_count < 10:
        score = min(
            score,
            1.0
        )

    elif word_count < 20:
        score = min(
            score,
            2.5
        )

    score = _clamp_score(
        score
    )

    return (
        score,
        strengths,
        weaknesses
    )


def _calculate_communication_score(answer_text):
    """
    Evaluate answer length and structure.
    """

    normalised_answer = _normalise_text(
        answer_text
    )

    word_count = len(
        normalised_answer.split()
    )

    if word_count == 0:
        return 0.0

    if word_count < 10:
        score = 1.5

    elif word_count < 20:
        score = 3.0

    elif word_count < 40:
        score = 5.0

    elif word_count < 80:
        score = 7.0

    elif word_count < 180:
        score = 8.5

    else:
        score = 8.0

    sentence_count = len([
        sentence
        for sentence in re.split(
            r'[.!?]+',
            answer_text
        )
        if sentence.strip()
    ])

    if sentence_count >= 3:
        score += 0.5

    structure_terms = [
        'first',
        'then',
        'because',
        'therefore',
        'finally',
        'as a result',
        'however',
        'for example',
        'initially',
        'to solve',
    ]

    structure_matches = sum(
        1
        for term in structure_terms
        if term in normalised_answer
    )

    score += min(
        structure_matches * 0.25,
        1.0
    )

    return _clamp_score(
        score
    )


def _calculate_technical_score(interview_answer):
    """
    Evaluate technical accuracy using five scoring dimensions:

    1. Correct technical concepts
    2. Architecture and design decisions
    3. Appropriate technology or service selection
    4. Production readiness
    5. Technical reasoning and depth

    Maximum score: 10
    """

    question = interview_answer.question
    answer_text = _normalise_text(
        interview_answer.answer_text
    )

    if not answer_text:
        return 0.0

    word_count = len(answer_text.split())

    if word_count < 5:
        return 0.0

    score = 0.0

    # -------------------------------------------------
    # 1. Correct technical concepts: maximum 2
    # -------------------------------------------------

    technical_concept_terms = [
        'architecture',
        'frontend',
        'backend',
        'api',
        'rest api',
        'database',
        'recommendation engine',
        'algorithm',
        'collaborative filtering',
        'content-based filtering',
        'machine learning',
        'authentication',
        'authorization',
        'encryption',
        'network',
        'container',
        'docker',
        'kubernetes',
        'serverless',
        'infrastructure as code',
        'terraform',
        'cloudformation',
        'load balancer',
        'cache',
        'redis',
        'message queue',
        'microservice',
        'monitoring',
        'logging',
        'ci/cd',
        'pipeline',
        'object storage',
        'cdn',
        'auto scaling',
        'autoscaling',
        'read replica',
        'backup',
        'disaster recovery',
    ]

    concept_matches = sum(
        1
        for term in technical_concept_terms
        if term in answer_text
    )

    if concept_matches >= 8:
        score += 2.0
    elif concept_matches >= 5:
        score += 1.6
    elif concept_matches >= 3:
        score += 1.2
    elif concept_matches >= 1:
        score += 0.6

    # -------------------------------------------------
    # 2. Architecture and design decisions: maximum 2
    # -------------------------------------------------

    architecture_terms = [
        'component',
        'service',
        'layered architecture',
        'separate service',
        'separate component',
        'data flow',
        'request',
        'response',
        'frontend sends',
        'backend handles',
        'stored in',
        'retrieves',
        'behind a load balancer',
        'private subnet',
        'public subnet',
        'multi-az',
        'availability zone',
        'event-driven',
        'asynchronous',
        'background worker',
        'decoupled',
        'loosely coupled',
        'scale independently',
        'modular architecture',
        'managed service',
    ]

    architecture_matches = sum(
        1
        for term in architecture_terms
        if term in answer_text
    )

    if architecture_matches >= 6:
        score += 2.0
    elif architecture_matches >= 4:
        score += 1.5
    elif architecture_matches >= 2:
        score += 1.0
    elif architecture_matches == 1:
        score += 0.5

    # -------------------------------------------------
    # 3. Technology and service selection: maximum 2
    # -------------------------------------------------

    technology_terms = [
        'aws',
        'azure',
        'google cloud',
        'amazon',
        'ecs',
        'eks',
        'lambda',
        's3',
        'cloudfront',
        'rds',
        'cloudwatch',
        'sqs',
        'ecr',
        'secrets manager',
        'postgresql',
        'mysql',
        'mongodb',
        'redis',
        'docker',
        'kubernetes',
        'terraform',
        'cloudformation',
        'github actions',
        'jenkins',
        'api gateway',
        'application load balancer',
        'object storage',
        'managed database',
        'message queue',
    ]

    technology_matches = sum(
        1
        for term in technology_terms
        if term in answer_text
    )

    if technology_matches >= 7:
        score += 2.0
    elif technology_matches >= 4:
        score += 1.5
    elif technology_matches >= 2:
        score += 1.0
    elif technology_matches == 1:
        score += 0.5

    if question.expected_skill:
        expected_skill_name = _normalise_text(
            question.expected_skill.skill_name
        )

        if (
            expected_skill_name
            and expected_skill_name in answer_text
        ):
            score += 0.5

    if question.expected_tool:
        expected_tool_name = _normalise_text(
            question.expected_tool.tool_name
        )

        if (
            expected_tool_name
            and expected_tool_name in answer_text
        ):
            score += 0.5

    # -------------------------------------------------
    # 4. Production readiness: maximum 2
    # -------------------------------------------------

    production_categories = {
        'security': [
            'security',
            'authentication',
            'authorization',
            'encryption',
            'https',
            'rate limiting',
            'secrets manager',
            'least privilege',
            'iam',
            'security group',
            'private subnet',
            'vulnerability',
            'audit logging',
        ],
        'scalability': [
            'scalability',
            'scalable',
            'auto scaling',
            'autoscaling',
            'horizontal scaling',
            'load balancer',
            'scale independently',
            'read replica',
            'distributed',
        ],
        'reliability': [
            'reliability',
            'reliable',
            'availability',
            'multi-az',
            'availability zone',
            'backup',
            'disaster recovery',
            'health check',
            'failover',
            'rolling deployment',
            'blue-green',
        ],
        'performance': [
            'performance',
            'cache',
            'caching',
            'redis',
            'index',
            'optimised query',
            'optimized query',
            'latency',
            'response time',
            'cdn',
            'background worker',
            'asynchronous',
        ],
        'operations': [
            'monitoring',
            'logging',
            'cloudwatch',
            'metrics',
            'alert',
            'ci/cd',
            'pipeline',
            'infrastructure as code',
            'automated deployment',
        ],
        'testing': [
            'unit test',
            'integration test',
            'performance test',
            'load test',
            'security test',
            'end-to-end test',
            'tested',
            'validated',
            'verified',
        ],
    }

    production_categories_matched = sum(
        1
        for category_terms in production_categories.values()
        if _contains_any(answer_text, category_terms)
    )

    if production_categories_matched >= 5:
        score += 2.0
    elif production_categories_matched >= 4:
        score += 1.6
    elif production_categories_matched >= 3:
        score += 1.2
    elif production_categories_matched >= 2:
        score += 0.8
    elif production_categories_matched == 1:
        score += 0.4

    # -------------------------------------------------
    # 5. Technical reasoning and depth: maximum 2
    # -------------------------------------------------

    reasoning_terms = [
        'because',
        'therefore',
        'the reason',
        'i chose',
        'i selected',
        'this allows',
        'this allowed',
        'this improves',
        'this improved',
        'this reduces',
        'this reduced',
        'this ensures',
        'this ensured',
        'the benefit',
        'the advantage',
        'instead of',
        'trade-off',
        'tradeoff',
        'however',
        'while',
        'suitable',
        'limitation',
        'would be simpler',
        'would be suitable',
        'to avoid',
        'in order to',
    ]

    reasoning_matches = sum(
        1
        for term in reasoning_terms
        if term in answer_text
    )

    if reasoning_matches >= 5:
        score += 2.0
    elif reasoning_matches >= 3:
        score += 1.5
    elif reasoning_matches >= 2:
        score += 1.0
    elif reasoning_matches == 1:
        score += 0.5

    # -------------------------------------------------
    # Depth adjustment
    # -------------------------------------------------

    if word_count >= 180:
        score += 0.5
    elif word_count >= 100:
        score += 0.3
    elif word_count < 15:
        score = min(score, 2.0)
    elif word_count < 30:
        score = min(score, 4.0)

    return _clamp_score(score)

def _calculate_competency_score(interview_answer):
    """
    Evaluate competency using five dimensions:

    1. Explains the concept
    2. Explains why it matters
    3. Applies it to the selected project
    4. Explains implementation
    5. Considers production requirements

    System-design questions also receive broader architecture
    competency scoring.

    Maximum score: 10
    """

    answer_text = _normalise_text(
        interview_answer.answer_text
    )

    if not answer_text:
        return 0.0

    question = interview_answer.question
    project = question.session.project

    word_count = len(answer_text.split())

    if word_count < 5:
        return 0.0

    score = 0.0

    # -------------------------------------------------
    # 1. Explains the concept: maximum 2
    # -------------------------------------------------

    concept_terms = [
        'is a',
        'is the',
        'refers to',
        'means',
        'defined as',
        'allows',
        'provides',
        'enables',
        'involves',
        'works by',
    ]

    if _contains_any(
        answer_text,
        concept_terms
    ):
        score += 2.0

    # -------------------------------------------------
    # 2. Explains importance or benefit: maximum 2
    # -------------------------------------------------

    importance_terms = [
        'because',
        'benefit',
        'advantage',
        'important',
        'helps',
        'improves',
        'reduces',
        'ensures',
        'allows',
        'supports',
        'makes it',
    ]

    importance_matches = sum(
        1
        for term in importance_terms
        if term in answer_text
    )

    if importance_matches >= 2:
        score += 2.0

    elif importance_matches == 1:
        score += 1.0

    # -------------------------------------------------
    # 3. Applies it to the selected project: maximum 2
    # -------------------------------------------------

    project_title = _normalise_text(
        project.title
    )

    if project_title and project_title in answer_text:
        score += 2.0

    else:
        project_words = [
            word
            for word in project_title.split()
            if len(word) >= 4
        ]

        project_matches = sum(
            1
            for word in project_words
            if word in answer_text
        )

        if project_matches >= 2:
            score += 1.0

    # -------------------------------------------------
    # 4. Explains implementation: maximum 2
    # -------------------------------------------------

    implementation_terms = [
        'implement',
        'implemented',
        'deploy',
        'deployed',
        'configure',
        'configured',
        'container',
        'docker',
        'kubernetes',
        'database',
        'api',
        'backend',
        'frontend',
        'load balancer',
        'terraform',
        'cloudformation',
        'pipeline',
        'ci/cd',
        'redis',
        'serverless',
        'lambda',
        'message queue',
        'monitoring',
        'storage',
    ]

    implementation_matches = sum(
        1
        for term in implementation_terms
        if term in answer_text
    )

    if implementation_matches >= 4:
        score += 2.0

    elif implementation_matches >= 2:
        score += 1.5

    elif implementation_matches == 1:
        score += 0.75

    # -------------------------------------------------
    # 5. Production thinking: maximum 2
    # -------------------------------------------------

    production_terms = [
        'production',
        'security',
        'performance',
        'availability',
        'reliability',
        'scalability',
        'scalable',
        'auto scaling',
        'monitoring',
        'logging',
        'backup',
        'disaster recovery',
        'high availability',
        'cost',
        'maintainability',
        'fault tolerance',
    ]

    production_matches = sum(
        1
        for term in production_terms
        if term in answer_text
    )

    if production_matches >= 3:
        score += 2.0

    elif production_matches >= 1:
        score += 1.0

    # -------------------------------------------------
    # Broad system-design competency adjustment
    # -------------------------------------------------

    if question.question_type == 'SYSTEM_DESIGN':

        architecture_categories = {
            'security': [
                'security',
                'authentication',
                'authorization',
                'encryption',
                'https',
                'rate limiting',
                'least privilege',
                'private subnet',
            ],
            'performance': [
                'performance',
                'cache',
                'caching',
                'redis',
                'index',
                'response time',
                'latency',
                'cdn',
            ],
            'scalability': [
                'scalability',
                'scalable',
                'auto scaling',
                'autoscaling',
                'load balancer',
                'scale independently',
                'read replica',
            ],
            'reliability': [
                'reliability',
                'availability',
                'multi-az',
                'availability zone',
                'backup',
                'health check',
                'failover',
                'disaster recovery',
            ],
            'testing': [
                'unit test',
                'integration test',
                'load test',
                'performance test',
                'security test',
                'end-to-end test',
            ],
            'operations': [
                'monitoring',
                'logging',
                'metrics',
                'alerts',
                'ci/cd',
                'pipeline',
                'infrastructure as code',
            ],
        }

        matched_categories = sum(
            1
            for category_terms
            in architecture_categories.values()
            if _contains_any(
                answer_text,
                category_terms
            )
        )

        if matched_categories >= 5:
            score = max(score, 9.0)

        elif matched_categories >= 4:
            score = max(score, 8.0)

        elif matched_categories >= 3:
            score = max(score, 7.0)

    return _clamp_score(score)

def _build_improved_answer(interview_answer):
    """
    Generate an answer structure based on question type.
    """

    question = interview_answer.question

    expected_skill = (
        question.expected_skill.skill_name
        if question.expected_skill
        else None
    )

    expected_tool = (
        question.expected_tool.tool_name
        if question.expected_tool
        else None
    )

    if question.question_type == 'PROJECT':
        parts = [
            'A stronger project answer should include:',
            '',
            '1. The project problem and intended users.',
            '2. Your specific responsibility.',
            '3. The technical approach you implemented.',
            '4. A challenge you encountered.',
            '5. How you solved the challenge.',
            '6. The final result and what you learned.',
        ]

    elif question.question_type == 'SYSTEM_DESIGN':
        parts = [
            'A stronger system-design answer should include:',
            '',
            '1. The major system components.',
            '2. How data moves between those components.',
            '3. The reason each technology or service was selected.',
            '4. Security, scalability and availability considerations.',
            '5. Monitoring, testing and deployment strategy.',
            '6. The trade-offs of the proposed architecture.',
        ]

    elif question.question_type == 'BEHAVIOURAL':
        parts = [
            'A stronger behavioural answer should use STAR:',
            '',
            '1. Situation: Explain the context.',
            '2. Task: Describe your responsibility.',
            '3. Action: Explain exactly what you did.',
            '4. Result: Describe the outcome and lesson learned.',
        ]

    elif question.question_type == 'TOOL':
        parts = [
            'A stronger tool-based answer should include:',
            '',
            '1. The purpose of the tool.',
            '2. Why it was selected.',
            '3. How it would be integrated.',
            '4. The practical benefit it provides.',
            '5. A limitation or implementation challenge.',
        ]

    elif question.question_type in {
        'TECHNICAL',
        'COMPETENCY',
        'WEAKNESS',
    }:
        parts = [
            'A stronger technical answer should include:',
            '',
            '1. A clear definition of the concept.',
            '2. Why the concept matters for the target role.',
            '3. How it applies to the selected project.',
            '4. A concrete implementation approach.',
            '5. Security, performance or scalability considerations.',
            '6. Testing and expected result.',
        ]

    else:
        parts = [
            'A stronger answer should include:',
            '',
            '1. Clear context.',
            '2. Your responsibility.',
            '3. The action or technical decision.',
            '4. The reason for the decision.',
            '5. The final result.',
        ]

    if expected_skill:
        parts.append(
            f'7. Explain specifically how {expected_skill} is applied.'
        )

    if expected_tool:
        parts.append(
            f'7. Explain specifically how {expected_tool} is integrated.'
        )

    return '\n'.join(
        parts
    )


def evaluate_answer(interview_answer):
    """
    Evaluate one InterviewAnswer and save the results.

    This is currently a rule-based evaluator.
    """

    answer_text = (
        interview_answer.answer_text or ''
    ).strip()

    if not answer_text:
        raise ValueError(
            'The interview answer cannot be empty.'
        )

    question = interview_answer.question

    technical_score = _calculate_technical_score(
        interview_answer
    )

    (
        evidence_score,
        evidence_strengths,
        evidence_weaknesses,
    ) = _calculate_evidence_score(
        interview_answer
    )

    competency_score = _calculate_competency_score(
        interview_answer
    )

    communication_score = _calculate_communication_score(
        answer_text
    )

    # -------------------------------------------------
# Question-type-aware overall score
# -------------------------------------------------

    if question.question_type == 'BEHAVIOURAL':
        overall_score = _clamp_score(
        technical_score * 0.15
        + evidence_score * 0.25
        + competency_score * 0.20
        + communication_score * 0.40
    )
    elif question.question_type == 'SYSTEM_DESIGN':
        overall_score = _clamp_score(
        technical_score * 0.40
        + evidence_score * 0.20
        + competency_score * 0.25
        + communication_score * 0.15
    )

    elif question.question_type == 'PROJECT':
        overall_score = _clamp_score(
        technical_score * 0.30
        + evidence_score * 0.35
        + competency_score * 0.20
        + communication_score * 0.15
    )

    else:
        overall_score = _clamp_score(
        technical_score * 0.35
        + evidence_score * 0.30
        + competency_score * 0.20
        + communication_score * 0.15
    )

    strengths = list(
        evidence_strengths
    )

    weaknesses = list(
        evidence_weaknesses
    )

    recommendations = []

        # -------------------------------------------------
    # Technical feedback
    # -------------------------------------------------

    if technical_score >= 8:
        technical_feedback = (
            'The answer demonstrates strong technical understanding '
            'and includes relevant implementation concepts.'
        )

        strengths.append(
            'The answer demonstrates strong technical knowledge.'
        )

    elif technical_score >= 6:
        if question.question_type == 'BEHAVIOURAL':
            technical_feedback = (
                'The answer includes suitable technical context for a '
                'behavioural question. The main strength is how the candidate '
                'explains the situation, action taken and final outcome.'
            )
        else:
            technical_feedback = (
                'The answer demonstrates acceptable technical understanding, '
                'but some technical decisions need more explanation.'
            )

            recommendations.append(
                'Explain the main technical decisions and trade-offs more clearly.'
            )

    elif technical_score >= 4:
        if question.question_type == 'BEHAVIOURAL':
            technical_feedback = (
                'The answer includes some relevant technical context. '
                'For this behavioural question, the main focus is the '
                'candidate’s response, decision-making and final outcome.'
            )
        else:
            technical_feedback = (
                'The answer includes some relevant technical concepts, '
                'but lacks depth and precision.'
            )

            weaknesses.append(
                'The technical explanation needs greater depth.'
            )

            recommendations.append(
                'Explain the architecture, implementation decisions and '
                'technical trade-offs in more detail.'
            )

    else:
        if question.question_type == 'BEHAVIOURAL':
            technical_feedback = (
                'The answer provides limited technical context, but the more '
                'important issue is that the behavioural example needs a clearer '
                'situation, action and outcome.'
            )

            recommendations.append(
                'Use the STAR structure and clearly explain what happened, '
                'what you did and what result you achieved.'
            )
        else:
            technical_feedback = (
                'The answer does not demonstrate sufficient technical '
                'understanding for this question.'
            )

            weaknesses.append(
                'The answer contains insufficient technical detail.'
            )

            recommendations.append(
                'Define the main concept and explain how it would be '
                'implemented in the selected project.'
            )
    # -------------------------------------------------
    # Communication feedback
    # -------------------------------------------------

    if communication_score >= 8:
        communication_feedback = (
            'The answer is clear, detailed and logically structured.'
        )

        strengths.append(
            'The answer is clearly communicated and well structured.'
        )

    elif communication_score >= 6:
        communication_feedback = (
            'The answer is understandable but could be organised more clearly.'
        )

    elif communication_score >= 4:
        communication_feedback = (
            'The answer communicates the main idea but lacks sufficient '
            'structure and detail.'
        )

        recommendations.append(
            'Organise the answer into context, action, reasoning and result.'
        )

    else:
        communication_feedback = (
            'The answer needs significantly better structure, detail '
            'and clarity.'
        )

        weaknesses.append(
            'The answer is too brief or unclear.'
        )

        recommendations.append(
            'Use complete sentences and explain the answer in a clear sequence.'
        )

    # -------------------------------------------------
    # Evidence recommendations
    # -------------------------------------------------

    if evidence_score < 5:
        recommendations.append(
            'Add concrete evidence from the selected project: your '
            'responsibility, implementation decision, challenge, solution, '
            'testing method and final result.'
        )

    elif evidence_score < 7:
        recommendations.append(
            'Strengthen the answer with more specific implementation '
            'details and a clear project outcome.'
        )

    # -------------------------------------------------
    # Competency recommendations
    # -------------------------------------------------

    if competency_score < 5:
        if question.expected_skill:
            recommendations.append(
                f'Explain the concept of '
                f'{question.expected_skill.skill_name} and how it applies '
                f'to the selected project.'
            )

        if question.expected_tool:
            recommendations.append(
                f'Explain why {question.expected_tool.tool_name} is used '
                f'and describe the integration steps.'
            )

    # Remove duplicate messages while preserving order.
    strengths = list(
        dict.fromkeys(strengths)
    )

    weaknesses = list(
        dict.fromkeys(weaknesses)
    )

    recommendations = list(
        dict.fromkeys(recommendations)
    )

    if not strengths:
        strengths.append(
            'The candidate attempted to address the interview question.'
        )

    if not weaknesses:
        weaknesses.append(
            'The answer could include more measurable outcomes and '
            'implementation detail.'
        )

    if not recommendations:
        recommendations.append(
            'Add a specific example, explain the technical decision and '
            'finish with a clear result.'
        )

    # -------------------------------------------------
    # Overall feedback
    # -------------------------------------------------

    if overall_score >= 8:
        general_feedback = (
        'This is a strong interview answer with good technical depth, '
        'project evidence and clear communication.'
    )

    elif overall_score >= 6:
        general_feedback = (
        'This is a reasonable answer, but it would be stronger with '
        'more project-specific evidence and technical reasoning.'
    )
    elif overall_score >= 4:
        general_feedback = (
        'The answer partially addresses the question but needs more '
        'technical detail, evidence and structure.'
    )

    else:
        general_feedback = (
        'The answer does not currently provide enough technical depth '
        'or evidence to perform well in an interview.'
    )
    improved_answer = _build_improved_answer(
        interview_answer
    )

    # -------------------------------------------------
    # Save evaluation
    # -------------------------------------------------

    interview_answer.technical_accuracy_score = (
        technical_score
    )

    interview_answer.evidence_consistency_score = (
        evidence_score
    )

    interview_answer.competency_score = (
        competency_score
    )

    interview_answer.communication_score = (
        communication_score
    )

    interview_answer.overall_score = (
        overall_score
    )

    interview_answer.technical_feedback = (
        technical_feedback
    )

    interview_answer.communication_feedback = (
        communication_feedback
    )

    interview_answer.strengths = '\n'.join(
        f'• {item}'
        for item in strengths
    )

    interview_answer.weaknesses = '\n'.join(
        f'• {item}'
        for item in weaknesses
    )

    interview_answer.feedback = (
        general_feedback
    )

    interview_answer.improved_answer = (
        improved_answer
    )

    interview_answer.recommendation = '\n'.join(
        f'• {item}'
        for item in recommendations
    )

    interview_answer.evaluated_at = (
        timezone.now()
    )

    interview_answer.save(
        update_fields=[
            'technical_accuracy_score',
            'evidence_consistency_score',
            'competency_score',
            'communication_score',
            'overall_score',
            'technical_feedback',
            'communication_feedback',
            'strengths',
            'weaknesses',
            'feedback',
            'improved_answer',
            'recommendation',
            'evaluated_at',
        ]
    )

    return interview_answer
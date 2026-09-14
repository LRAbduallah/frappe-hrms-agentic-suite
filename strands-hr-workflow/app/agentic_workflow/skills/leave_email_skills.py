from strands import AgentSkills, Skill


DRAFT_SKILL = Skill(
    name="leave-email-drafting",
    description="Draft personalized leave summary emails with low-balance and LOP awareness.",
    instructions=(
        "Draft one email per employee using the exact leave metrics provided. "
        "If leave is low, clearly warn about potential Loss of Pay (LOP) when leave exceeds remaining balance. "
        "Return JSON only with subject and body. "
        "Sign every email as John Doe, HR Manager."
    ),
)

RISK_SKILL = Skill(
    name="leave-risk-assessment",
    description="Assess low leave balance and potential loss of pay risk.",
    instructions=(
        "Classify leave risk with deterministic thresholds. "
        "Mark low balance when remaining leave is under configured thresholds. "
        "Mark LOP risk when remaining leave is near zero or negative."
    ),
)

WORKFLOW_SKILLS_PLUGIN = AgentSkills(skills=[DRAFT_SKILL, RISK_SKILL])

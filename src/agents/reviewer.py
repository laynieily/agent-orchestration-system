"""
Reviewer agent: validates a specialist's output before it's accepted.
"""
from __future__ import annotations

import os

from src.schemas.models import ReviewResult, SpecialistResult, SubTask

# prompt needs {description}, {expected_format}, and
# {output} placeholders, and should instruct the model to score quality
# 0-1 and give brief feedback on whether the output matches the expected
# format.
REVIEW_PROMPT_TEMPLATE = """
You are the Reviewer Agent. Your job is to evaluate whether a specialist's output satisfies the subtask requirements.

Evaluate the following:

Subtask Description:
{description}

Expected Output Format:
{expected_format}

Specialist Output:
{output}

Instructions:
1. Score the quality from 0.0 to 1.0
    - 1.0 = perfectly matches the expected format and fufills the description
    - 0.0 = completely unusable or irrelevant
2. Provide a brief, constructive feedback explaining:
    - whether the output matches the expected format,
    - whether it fufills the subtask description,
    - what should be improved if needed.
3. Set "approved" to true ONLY if the output meets the expected format AND the quality score is high.

You MUST return a JSON object matching the ReviewResult schema

"""


class ReviewerAgent:
    def __init__(self, llm):
        self.llm = llm
        self.quality_threshold = float(os.getenv("REVIEW_QUALITY_THRESHOLD", "0.6"))

    def review(self, subtask: SubTask, result: SpecialistResult) -> ReviewResult:
        if not result.success: 
            return ReviewResult(
                subtask_id=subtask.id,
                approved=False, 
                quality_score=0.0, 
                feedback=f"Specialist failed: {result.error}",
            )
        
        prompt = REVIEW_PROMPT_TEMPLATE.format(
            description = subtask.description,
            expected_format=subtask.expected_output_format,
            output=result.output,
        )

        structured_llm = self.llm.with_structured_output(ReviewResult)
        review = structured_llm.invoke(prompt)

        review = review.model_copy(update={"subtask_id": subtask.id})

        approved = review.approved and review.quality_score >= self.quality_threshold
        review = review.model_copy(update={"approved": approved})

        return review
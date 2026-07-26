from onesim.events import Event
from typing import List, Dict

class StartEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id)
        # No additional fields are specified for this event

class QuestionPosedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        question_content: str = "",
        difficulty: float = 0.5
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id)
        self.question_content = question_content
        self.difficulty = difficulty

class AttentionAllocatedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        allocated_attention: float = 0.0,
        student_ids: List[str] = None
    ) -> None:
        if student_ids is None:
            student_ids = []
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id)
        self.allocated_attention = allocated_attention
        self.student_ids = student_ids

class ResponseProvidedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        will_raise_hand: bool = False,
        gesture_description: str = "",
        response_content: str = "",
        response_type: str = 'non-verbal',
        student_id: str = "",
        # Optional structured signals (derived from CEPS-based profiles; used to stabilize treatment effects)
        expression_score: float | None = None,
        achievement_score: float | None = None,
        ses_score: float | None = None
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id)
        self.will_raise_hand = will_raise_hand
        self.gesture_description = gesture_description
        self.response_content = response_content
        self.response_type = response_type
        self.student_id = student_id
        self.expression_score = expression_score
        self.achievement_score = achievement_score
        self.ses_score = ses_score
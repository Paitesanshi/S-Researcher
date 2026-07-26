from onesim.events import Event
from typing import Any

class StartEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)

class AttentionReceivedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        worker_id: str = "",
        leadership_attention_level: int = 0,
        response_message: str = 'Acknowledged',
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.worker_id = worker_id
        self.leadership_attention_level = leadership_attention_level
        self.response_message = response_message

class ProductivityAdjustedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        worker_id: str = "",
        new_productivity_level: int = 0,
        adjustment_reason: str = 'Leadership Attention',
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.worker_id = worker_id
        self.new_productivity_level = new_productivity_level
        self.adjustment_reason = adjustment_reason

class FeedbackProvidedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        leader_id: str = "",
        worker_id: str = "",
        feedback_content: str = 'Keep up the good work!',
        task_assigned: str = 'None',
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.leader_id = leader_id
        self.worker_id = worker_id
        self.feedback_content = feedback_content
        self.task_assigned = task_assigned

class ResponseEvaluatedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        leader_id: str = "",
        worker_id: str = "",
        evaluation_outcome: str = 'Satisfactory',
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.leader_id = leader_id
        self.worker_id = worker_id
        self.evaluation_outcome = evaluation_outcome

class TeamSupportEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        team_id: str = "",
        worker_id: str = "",
        support_type: str = 'Emotional',
        interaction_details: str = 'Group discussion',
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.team_id = team_id
        self.worker_id = worker_id
        self.support_type = support_type
        self.interaction_details = interaction_details
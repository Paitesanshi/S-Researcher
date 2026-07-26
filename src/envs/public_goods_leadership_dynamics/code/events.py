from onesim.events import Event
from typing import Any

class FollowerContributionResultEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        actual_contribution: float = 0.0,
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.actual_contribution: float = actual_contribution

class LeaderContributionEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        contribution_level: float,
        decision_mechanism: str,
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.contribution_level: float = contribution_level
        self.decision_mechanism: str = decision_mechanism

class StartEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
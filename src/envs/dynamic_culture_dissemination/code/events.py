from onesim.events import Event
from typing import Dict
class StartEvent(Event):
    """Environment startup event."""
    def __init__(self, from_agent_id: str, to_agent_id: str):
        super().__init__(from_agent_id, to_agent_id)

# Carry the complete cultural feature set in the recommendation event.
class RecommendationEvent(Event):
    def __init__(self, from_agent_id: str, to_agent_id: str, cultural_traits: Dict[str, int], 
                    reason: str):
        super().__init__(from_agent_id, to_agent_id)
        self.reason = reason
        self.cultural_traits = cultural_traits

class AdoptionEvent(Event):
    def __init__(self, from_agent_id: str, to_agent_id: str, 
                 dimension: str, old_value: str, new_value: str, 
                  adopted: bool, round_number: int):
        super().__init__(from_agent_id, to_agent_id)
        self.adopted = adopted
        self.round_number = round_number
        self.dimension = dimension
        self.old_value = old_value
        self.new_value = new_value

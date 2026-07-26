from typing import Any, List, Optional
import json
import asyncio
from loguru import logger
from onesim.models import JsonBlockParser
from onesim.agent import GeneralAgent
from onesim.profile import AgentProfile
from onesim.memory import MemoryStrategy
from onesim.planning import PlanningBase
from onesim.events import Event
from .events import LeaderContributionEvent
from onesim.relationship import RelationshipManager





class LeaderAgent(GeneralAgent):
    def __init__(self,
                 sys_prompt: str | None = None,
                 model_config_name: str = None,
                 event_bus_queue: asyncio.Queue = None,
                 profile: AgentProfile = None,
                 memory: MemoryStrategy = None,
                 planning: PlanningBase = None,
                 relationship_manager: RelationshipManager = None) -> None:
        super().__init__(sys_prompt, model_config_name, event_bus_queue, profile, memory, planning, relationship_manager)
        self.register_event("StartEvent", "decide_contribution")

    async def decide_contribution(self, event: Event) -> List[Event]:
        # instruction = """Decide on the contribution level based on the current context of the followers.
        # Please return the decision in the following JSON format:
        
        # {
        # "contribution_level": <float>,
        # "selected_mechanism": "<'voluntary' or 'forced'>",
        # "target_ids": ["<The string ID(s) of the relevant agents>"]
        # }
        # """
    
        # observation = "Determine the contribution level based on the current scenario."
        # result = await self.generate_reaction(instruction, observation)
    
        # contribution_level = result.get("contribution_level", None)
        # selected_mechanism = result.get("selected_mechanism", None)
        # target_ids = result.get("target_ids", None)

        # if target_ids is None:
        #     logger.warning("No target_ids returned. Aborting event creation.")
        #     return []

        # if not isinstance(target_ids, list):
        #     target_ids = [target_ids]

        # self.profile.update_data("contribution_level", contribution_level)
        # self.profile.update_data("selected_mechanism", selected_mechanism)
        target_ids=[]
        for relationship in self.relationship_manager.get_all_relationships():
            target_ids.append(relationship.target_id)
        contribution_level = self.profile.get_data("contribution_level", 2)
        decision_mechanism = self.profile.get_data("decision_mechanism", "voluntary")
        events = []
        for target_id in target_ids:
            leader_contribution_event = LeaderContributionEvent(self.profile_id, target_id, contribution_level, decision_mechanism)
            events.append(leader_contribution_event)
        return events
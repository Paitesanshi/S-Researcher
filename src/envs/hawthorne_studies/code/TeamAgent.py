from typing import Any, List, Optional
import json
import asyncio
from loguru import logger
from onesim.models import JsonBlockParser
from onesim.agent import GeneralAgent
from onesim.profile import AgentProfile
from onesim.memory import MemoryStrategy
from onesim.planning import PlanningBase
from onesim.events import *
from onesim.relationship import RelationshipManager
from .events import *

class TeamAgent(GeneralAgent):
    def __init__(self,
                 sys_prompt: str | None = None,
                 model_config_name: str = None,
                 event_bus_queue: asyncio.Queue = None,
                 profile: AgentProfile=None,
                 memory: MemoryStrategy=None,
                 planning: PlanningBase=None,
                 relationship_manager: RelationshipManager=None) -> None:
        super().__init__(sys_prompt, model_config_name, event_bus_queue, profile, memory, planning, relationship_manager)
        self.register_event("StartEvent", "initiate_team_interaction")

    async def initiate_team_interaction(self, event: Event) -> List[Event]:
        # No condition to check, proceed directly with the handler logic

        # Safely access interaction details from the event
        interaction_details = getattr(event, 'interaction_details', 'Group discussion')

        # Generate reaction with LLM for decision making
        instruction = """Please determine the target WorkerAgent(s) for team interaction initiation. 
        The context involves enhancing team atmosphere through emotional support and cooperation. 
        Ensure to include the interaction_details in the response. 
        Return the information in the following JSON format:

        {
            "interaction_details": "<Details of interaction initiated by TeamAgent>",
            "target_ids": ["<The string ID(s) of the WorkerAgent(s)>"]
        }
        Note: The target_ids should only include the WorkerAgent(s). TeamAgent(s) and LeaderAgent(s) should not be included.
        """

        observation = f"Interaction Details: {interaction_details}"
        result = await self.generate_reaction(instruction, observation)

        interaction_details = result.get('interaction_details', interaction_details)
        target_ids = result.get('target_ids', None)
        if not isinstance(target_ids, list):
            target_ids = [target_ids]

        # Prepare and send TeamSupportEvent to each WorkerAgent
        events = []
        for target_id in target_ids:
            team_support_event = TeamSupportEvent(
                from_agent_id=self.profile_id,
                to_agent_id=target_id,
                team_id=self.profile_id,  # Assuming TeamAgent's ID is used as team_id
                worker_id=target_id,
                support_type="Emotional",
                interaction_details=interaction_details
            )
            events.append(team_support_event)

        # Update the team atmosphere in the environment
        new_team_atmosphere = "Improved through interaction"
        self.env.update_data("team_atmosphere", new_team_atmosphere)

        return events
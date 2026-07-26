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

class WorkerAgent(GeneralAgent):
    def __init__(self,
                 sys_prompt: str | None = None,
                 model_config_name: str = None,
                 event_bus_queue: asyncio.Queue = None,
                 profile: AgentProfile=None,
                 memory: MemoryStrategy=None,
                 planning: PlanningBase=None,
                 relationship_manager: RelationshipManager=None) -> None:
        super().__init__(sys_prompt, model_config_name, event_bus_queue, profile, memory, planning, relationship_manager)
        self.register_event("StartEvent", "receive_leadership_attention")
        self.register_event("FeedbackProvidedEvent", "receive_leadership_attention")
        self.register_event("TeamSupportEvent", "adjust_productivity")
        self.attention_received = False
        self.team_support_received = False

    async def receive_leadership_attention(self, event: Event) -> List[Event]:
        # Safely retrieve event-specific data
        leadership_attention_level = getattr(event, 'leadership_attention_level', 0)
        feedback_content = getattr(event, 'feedback_content', "No feedback provided")

        # Instruction for LLM to generate emotional response
        instruction = """
        Based on the received leadership attention level and feedback content, update the emotional state of the WorkerAgent.
        Please return the information in the following JSON format:
        {
            "emotional_state": "<Updated emotional state based on leadership attention>",
            "target_ids": ["<The string ID of the LeaderAgent to acknowledge>"]
        }
        Note: The target_ids should only be LeaderAgent IDs. Don't include the WorkerAgent ID in the target_ids.
        """

        # Observation context for LLM
        observation = f"Leadership attention level: {leadership_attention_level}, Feedback content: {feedback_content}"

        # Generate reaction using LLM
        result = await self.generate_reaction(instruction, observation)

        # Parse the LLM's JSON response
        emotional_state = result.get('emotional_state', None)
        target_ids = result.get('target_ids', None)
        if not isinstance(target_ids, list):
            target_ids = [target_ids]

        # Update the WorkerAgent's emotional state
        self.profile.update_data("emotional_state", emotional_state)
        self.profile.update_data("leadership_attention_level", leadership_attention_level)

        # Register that attention has been received
        self.attention_received = True

        # Create and send AttentionReceivedEvent to each target LeaderAgent
        events = []
        for target_id in target_ids:
            attention_received_event = AttentionReceivedEvent(
                from_agent_id=self.profile_id,
                to_agent_id=target_id,
                worker_id=self.profile_id,
                leadership_attention_level=leadership_attention_level,
                response_message="Acknowledged"
            )
            events.append(attention_received_event)

        return events

    async def adjust_productivity(self, event: Event) -> List[Event]:
        # Update profile based on the incoming event type
        if isinstance(event, AttentionReceivedEvent):
            self.attention_received = True
        elif isinstance(event, TeamSupportEvent):
            self.team_support_received = True

        # Proceed only if both events have been received
        if not (self.attention_received and self.team_support_received):
            return []

        # Retrieve required variables
        leadership_attention_level = self.profile.get_data("leadership_attention_level", 0)
        support_type = getattr(event, 'support_type', "Unknown")

        # Generate decision using LLM
        observation = f"Leadership attention level: {leadership_attention_level}, Support type: {support_type}"
        instruction = """
        Based on the received leadership attention and team support, determine the new productivity level for the WorkerAgent. 
        Please return the information in the following JSON format:

        {
        "new_productivity_level": <The adjusted level of productivity as an integer>,
        "adjustment_reason": "<Reason for productivity adjustment>",
        "target_ids": ["ENV"]
        }
        """
    
        result = await self.generate_reaction(instruction, observation)
    
        new_productivity_level = result.get('new_productivity_level', 0)
        adjustment_reason = result.get('adjustment_reason', "Leadership Attention")
        target_ids = result.get('target_ids', None)
        if not isinstance(target_ids, list):
            target_ids = [target_ids]

        # Update the agent's productivity level
        self.profile.update_data("productivity_level", new_productivity_level)

        # Reset flags after processing
        self.attention_received = False
        self.team_support_received = False

        # Prepare and send the ProductivityAdjustedEvent
        events = []
        for target_id in target_ids:
            productivity_event = ProductivityAdjustedEvent(
                from_agent_id=self.profile_id,
                to_agent_id=target_id,
                worker_id=self.profile_id,
                new_productivity_level=new_productivity_level,
                adjustment_reason=adjustment_reason
            )
            events.append(productivity_event)
    
        return events
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
        self.register_event("StartEvent", "provide_feedback_and_tasks")
        self.register_event("AttentionReceivedEvent", "evaluate_employee_response")

    async def provide_feedback_and_tasks(self, event: Event) -> List[Event]:
        # Since the action condition is null, proceed directly with the handler logic

        # Retrieve required variables from the event, handle cases where they might be absent
        worker_id = getattr(event, 'worker_id', '')
        task_assigned = getattr(event, 'task_assigned', 'None')

        # Prepare instruction for LLM to generate feedback content and target_ids
        instruction = """
        Please generate feedback content and determine target_ids for providing feedback and tasks.
        The feedback should be motivating and relevant to the task assigned.
        Return the information in the following JSON format:

        {
        "feedback_content": "<Motivational feedback>",
        "task_assigned": "<Task assigned to the worker>",
        "target_ids": ["<WorkerAgent ID or list of WorkerAgent IDs>"]
        }
        """

        observation = f"Worker ID: {worker_id}, Task Assigned: {task_assigned}"

        # Generate reaction using LLM
        result = await self.generate_reaction(instruction, observation)

        feedback_content = result.get('feedback_content', "Keep up the good work!")
        task_assigned = result.get('task_assigned', "None")
        target_ids = result.get('target_ids', None)

        if not isinstance(target_ids, list):
            target_ids = [target_ids]

        # Update agent's feedback log
        feedback_log = f"Feedback provided to {worker_id}: {feedback_content} with task {task_assigned}"
        self.profile.update_data("feedback_log", feedback_log)

        # Prepare and send FeedbackProvidedEvent to each target_id
        events = []
        for target_id in target_ids:
            feedback_event = FeedbackProvidedEvent(
                from_agent_id=self.profile_id,
                to_agent_id=target_id,
                leader_id=self.profile_id,
                worker_id=target_id,
                feedback_content=feedback_content,
                task_assigned=task_assigned
            )
            events.append(feedback_event)

        return events

    async def evaluate_employee_response(self, event: Event) -> List[Event]:
        # Condition Check: No condition specified, proceed with the handler logic

        # Retrieve required variables from event, handle cases where they might be absent
        response_message = getattr(event, 'response_message', 'Acknowledged')

        # Generate reaction using LLM
        observation = f"Received response message: {response_message}"
        instruction = """Evaluate the response message from WorkerAgent based on leadership attention.
        Determine if the response is 'Satisfactory' or requires further attention.
        Provide the evaluation outcome and decide on the target_ids for sending the event.
        Please return the information in the following JSON format:

        {
        "evaluation_outcome": "<Outcome of the evaluation>",
        "target_ids": ["ENV"]
        }
        """

        result = await self.generate_reaction(instruction, observation)

        # Extract evaluation outcome and target_ids
        evaluation_outcome = result.get('evaluation_outcome', "Satisfactory")
        target_ids = result.get('target_ids', "ENV")
        if not isinstance(target_ids, list):
            target_ids = [target_ids]

        # Update agent data with evaluation outcome
        self.profile.update_data("evaluation_outcome", evaluation_outcome)

        # Prepare and send ResponseEvaluatedEvent to EnvAgent
        events = []
        for target_id in target_ids:
            response_evaluated_event = ResponseEvaluatedEvent(
                from_agent_id=self.profile_id,
                to_agent_id=target_id,
                leader_id=self.profile_id,
                worker_id=getattr(event, 'worker_id', ''),
                evaluation_outcome=evaluation_outcome
            )
            events.append(response_evaluated_event)

        return events
from typing import Any, List
import json
import asyncio
from onesim.models import JsonBlockParser
from onesim.agent import GeneralAgent
from onesim.profile import AgentProfile
from onesim.memory import MemoryStrategy
from onesim.planning import PlanningBase
from onesim.events import Event
from onesim.relationship import RelationshipManager
from .events import ResponseProvidedEvent, QuestionPosedEvent
from loguru import logger
import re

class StudentAgent(GeneralAgent):
    def __init__(self,
                 sys_prompt: str | None = None,
                 model_config_name: str = None,
                 event_bus_queue: asyncio.Queue = None,
                 profile: AgentProfile = None,
                 memory: MemoryStrategy = None,
                 planning: PlanningBase = None,
                 relationship_manager: RelationshipManager = None) -> None:
        super().__init__(sys_prompt, model_config_name, event_bus_queue, profile, memory, planning, relationship_manager)
        self.register_event("QuestionPosedEvent", "respond_to_question")

    async def respond_to_question(self, event: QuestionPosedEvent) -> List[Event]:
        """
        Decide whether to raise hand based on:
        1. Ability judgment (can I answer this question?)
        2. Willingness judgment (do I dare to raise my hand?)
        Then generate gesture description.

        Flow:
        1. Extract student's characteristics from profile (prompt_summary)
        2. Use generate_reaction to make raise-hand decision
        3. Generate gesture description (if raised) or non-verbal state (if not)
        4. Record decision history
        5. Send ResponseProvidedEvent back to teacher
        """
        # Step 1: Extract student's characteristics from profile
        prompt_summary = await self.get_data("prompt_summary", "")
        student_name = await self.get_data("name", "Unknown")

        # Get question details from event
        question_content = event.question_content
        difficulty = event.difficulty

        # Step 2: Use generate_reaction to make raise-hand decision
        observation = f"""
        Teacher asked: {question_content}
        Question difficulty: {difficulty} (0=easy, 1=hard)

        My background: {prompt_summary}
        """

        instruction = """
        You are a middle school student who just heard a question from the teacher.

        Based on your background (academic level and communication skills), you need to decide:
        1. CAN you answer this question? (ability judgment based on academic level and question difficulty)
        2. Do you DARE to raise your hand? (willingness judgment based on shyness, communication skills)

        Decision process:
        - First judge if you have the ability to answer based on your academic level and the question difficulty
        - Then judge if you have the courage/willingness to raise your hand based on your communication skills

        If you decide to RAISE YOUR HAND:
        - Generate a gesture description showing your hand-raising behavior
        - Confident examples: "Leans forward, raises a hand high, and makes eye contact" or "Raises a hand quickly with a smile"
        - Hesitant examples: "Raises a hand halfway while looking down" or "Slowly raises a hand and avoids eye contact"
        - Provide a brief answer to the question in response_content

        If you decide NOT to raise your hand:
        - Generate a non-verbal state description
        - Examples: "Looks down at the book and avoids eye contact" or "Thinks quietly without raising a hand"
        - Leave response_content empty

        Return in JSON format:
        {
            "will_raise_hand": true or false,
            "gesture_description": "Your gesture description (if raised) or non-verbal state (if not)",
            "response_type": "verbal" or "non-verbal",
            "target_ids": []
        }

        Note:
        - will_raise_hand should be based on both ability AND willingness
        - gesture_description should reflect your personality and communication style
        - response_type is "verbal" if you raised hand, "non-verbal" if not
        - target_ids should be empty list (will be filled automatically)
        """

        # Always produce a valid response, including when the model fails.
        try:
            result = await self.generate_reaction(instruction, observation)
            if not result:
                logger.error(f"Student {self.profile_id} ({student_name}) - LLM returned None, using fallback")
                result = {
                    "will_raise_hand": False,
                    "gesture_description": "Remains silent",
                    "response_content": "",
                    "response_type": "non-verbal"
                }
        except Exception as e:
            logger.error(f"Student {self.profile_id} ({student_name}) - LLM exception: {e}, using fallback")
            result = {
                "will_raise_hand": False,
                "gesture_description": "Remains silent because of a model error",
                "response_content": "",
                "response_type": "non-verbal"
            }

        will_raise_hand = result.get('will_raise_hand', False)
        gesture_description = result.get('gesture_description', 'Remains silent')
        response_content = result.get('response_content', '')
        response_type = result.get('response_type', 'non-verbal')

        # --- Structured signals (for teacher modeling + stable correlations) ---
        # We derive coarse numeric scores from the CEPS-generated prompt_summary text.
        # These are NOT shown to the LLM unless teacher chooses to use them; they help align mechanisms to CEPS variables.
        def _extract_between(text: str, left: str, right: str) -> str | None:
            m = re.search(re.escape(left) + r"(.+?)" + re.escape(right), text)
            return m.group(1).strip() if m else None

        # Communication tier: low/medium/high -> 2/3/4.
        comm_map = {"low": 2.0, "medium": 3.0, "high": 4.0}
        comm_txt = _extract_between(prompt_summary, "communication is ", ";")
        expression_score = None
        if comm_txt:
            for k, v in comm_map.items():
                if k in comm_txt:
                    expression_score = v
                    break

        # Achievement tier: low/medium/high -> 2/3/4.
        ach_map = {"low": 2.0, "medium": 3.0, "high": 4.0}
        ach_txt = _extract_between(prompt_summary, "Academic performance is ", ";")
        achievement_score = None
        if ach_txt:
            for k, v in ach_map.items():
                if k in ach_txt:
                    achievement_score = v
                    break

        # Socioeconomic tier: low/medium/high -> 2/3/4.
        ses_map = {"low": 2.0, "medium": 3.0, "high": 4.0}
        ses_txt = _extract_between(
            prompt_summary, "socioeconomic background is ", ";"
        )
        ses_score = None
        if ses_txt:
            for k, v in ses_map.items():
                if k in ses_txt:
                    ses_score = v
                    break

        logger.info(f"Student {self.profile_id} ({student_name}): will_raise={will_raise_hand}, gesture={gesture_description}")

        # Step 3: Record decision history
        raise_hand_history = await self.get_data("raise_hand_history", [])
        raise_hand_history.append({
            "question": question_content,
            "difficulty": difficulty,
            "raised": will_raise_hand,
            "gesture": gesture_description,
            "response": response_content if will_raise_hand else ""
        })
        await self.update_data("raise_hand_history", raise_hand_history)

        # Step 4: Send response back to teacher
        return [ResponseProvidedEvent(
            from_agent_id=self.profile_id,
            to_agent_id=event.from_agent_id,
            will_raise_hand=will_raise_hand,
            gesture_description=gesture_description,
            response_content=response_content,
            response_type=response_type,
            student_id=self.profile_id,
            expression_score=expression_score,
            achievement_score=achievement_score,
            ses_score=ses_score
        )]

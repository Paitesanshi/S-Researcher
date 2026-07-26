from typing import Any, List
import asyncio
import random
from loguru import logger
from onesim.models import JsonBlockParser
from onesim.agent import GeneralAgent
from onesim.profile import AgentProfile
from onesim.memory import MemoryStrategy
from onesim.planning import PlanningBase
from onesim.events import Event
from onesim.relationship import RelationshipManager
from .events import FollowerContributionResultEvent, LeaderContributionEvent

class FollowerAgent(GeneralAgent):
    def __init__(self,
                 sys_prompt: str | None = None,
                 model_config_name: str = None,
                 event_bus_queue: asyncio.Queue = None,
                 profile: AgentProfile=None,
                 memory: MemoryStrategy=None,
                 planning: PlanningBase=None,
                 relationship_manager: RelationshipManager=None) -> None:
        super().__init__(sys_prompt, model_config_name, event_bus_queue, profile, memory, planning, relationship_manager)
        self.register_event("LeaderContributionEvent", "adjust_contribution")

    async def adjust_contribution(self, event: Event) -> List[Event]:
        # Get leader's contribution and decision mechanism from event
        leader_contribution = event.contribution_level
        decision_mechanism = event.decision_mechanism
        agent_trait = self.profile.get_data('trait', 'unknown')
        
        # Add individual difference factors to increase realism
        # Each agent gets subtle variations in their context
        uncertainty_phrases = [
            "You're not entirely sure what others will do.",
            "You have some doubts about whether everyone will cooperate.",
            "You're trying to make the best decision with limited information.",
            "You feel some uncertainty about the right choice here.",
            "You're weighing different considerations that pull you in different directions."
        ]
        
        risk_attitudes = [
            "You tend to be somewhat cautious in uncertain situations.",
            "You're willing to take some calculated risks.",
            "You prefer to play it safe when you're unsure.",
            "You're comfortable with a moderate level of risk.",
            "You try to find a balance between safety and opportunity."
        ]
        
        social_concerns = [
            "You care about what others might think of your choice.",
            "You're somewhat concerned about appearing fair to others.",
            "You wonder if others will judge your decision.",
            "You think about how your choice reflects on you.",
            "You're considering both your own interests and social expectations."
        ]
        
        # Randomly select one phrase from each category to add individual variation
        selected_uncertainty = random.choice(uncertainty_phrases)
        selected_risk = random.choice(risk_attitudes)
        selected_social = random.choice(social_concerns)
        
        # Construct base scenario with natural language
        base_scenario = """You are participating in a public goods game experiment with 3 other people.

HERE'S HOW IT WORKS:
- Everyone starts with 10 tokens
- You decide how many tokens (0-10) to put into a shared group pot
- Whatever goes into the pot gets multiplied by 1.6, then split equally among all 4 people

EXAMPLES:
- If everyone keeps everything (contributes 0): You end up with 10 tokens
- If everyone contributes half (5 tokens): Pot = 20 × 1.6 = 32, everyone gets 8 from pot + 5 kept = 13 tokens total
- If everyone contributes everything (10 tokens): Pot = 40 × 1.6 = 64, everyone gets 16 tokens

SO: The more people contribute, the more everyone benefits. But you personally earn more by contributing less than others (if they contribute and you don't, you keep your tokens AND get a share of the pot).

In this experiment, one person (the "leader") decided first. Now you and the other 2 people see what the leader did before making your own choice.
"""
        
        # Simple, natural descriptions of leader's decision
        if decision_mechanism == "voluntary" or decision_mechanism == "choice":
            leader_decision = f"""
WHAT THE LEADER DID:
The leader could choose any amount from 0 to 10 tokens.

The leader decided to contribute {leader_contribution} tokens.
"""
        else:  # forced or required
            leader_decision = f"""
WHAT THE LEADER DID:
The experimenter told the leader they had to contribute exactly {leader_contribution} tokens. The leader didn't get to choose - this amount was required.

The leader contributed {leader_contribution} tokens (as required).
"""
        
        observation = base_scenario + leader_decision + "\n\nNow it's your turn. How many tokens will you contribute?"
        
        # More realistic, human-like instruction with individual variation
        trait_descriptions = {
            "Prosocial": "generally care about group welfare and fairness, though you also think about yourself",
            "Proself": "generally focus on your own outcomes, though you're not completely unconcerned about others"
        }
        
        trait_desc = trait_descriptions.get(agent_trait, "consider both personal and collective interests")
        
        instruction = f"""You need to decide how many tokens to contribute (0-10).

ABOUT YOU:
You {trait_desc}. But remember - people with similar tendencies still make quite different choices depending on the situation. {selected_risk} {selected_social}

THINK ABOUT THIS NATURALLY:
Put yourself in this situation. What's going through your mind?

The leader contributed {leader_contribution} tokens. What's your reaction?
- Does this seem like a lot, a little, or about right?
- Can you tell anything about what the leader was thinking?
- Does it matter to you how the leader made this decision?

What about the other 2 people who are also deciding right now?
- What do you think they'll probably do?
- Should you try to match them, lead them, or just do your own thing?
- {selected_uncertainty}

What feels right to YOU?
- What would you feel comfortable contributing?
- Are you willing to take a chance on cooperation, or play it safer?
- What choice would you feel okay about afterward?

Think about the trade-offs:
- Contributing more helps everyone (including you) but costs you directly
- Contributing less helps you keep more but you get less if others also hold back
- You're trying to balance different goals that might conflict

Make your decision based on what feels right in THIS specific situation. Don't overthink it - there's no perfect answer.

Respond in this format:
{{
    "reasoning": "Explain your thinking naturally and honestly, like you're telling a friend. Just a few sentences about what went through your mind and why you made this choice. Don't write a formal analysis - be genuine.",
    "actual_contribution": <a number from 0 to 10>,
    "target_ids": ["ENV"]
}}

Important: 
- actual_contribution must be a whole number between 0 and 10
- Be honest about your real reasoning - not what you think you "should" say
- It's okay to have mixed feelings or be unsure
"""
        
        result = await self.generate_reaction(instruction, observation)
        
        # Enhanced validation and error handling
        if not isinstance(result, dict):
            logger.error(f"Agent {self.profile_id} returned non-dict result: {type(result)}")
            result = {"actual_contribution": 5, "reasoning": "Error: invalid response format", "target_ids": ["ENV"]}
        
        # Extract and validate reasoning
        reasoning = result.get("reasoning", "")
        if not reasoning or not reasoning.strip():
            logger.warning(f"Agent {self.profile_id} provided empty reasoning")
            reasoning = "No reasoning provided"
        
        # Extract and validate contribution
        actual_contribution = result.get("actual_contribution", 5)
        if not isinstance(actual_contribution, (int, float)):
            logger.error(f"Agent {self.profile_id} invalid contribution type: {type(actual_contribution)}, using default 5")
            actual_contribution = 5
        
        # Ensure contribution is within valid range
        if not (0 <= actual_contribution <= 10):
            logger.warning(f"Agent {self.profile_id} invalid contribution {actual_contribution}, clamping to [0, 10]")
            actual_contribution = max(0, min(10, actual_contribution))
        
        # Convert to integer
        actual_contribution = int(round(actual_contribution))
        
        # Extract and validate target_ids
        target_ids = result.get("target_ids", ["ENV"])
        if not isinstance(target_ids, list):
            target_ids = [target_ids] if target_ids else ["ENV"]
        
        # Update profile with comprehensive context for analysis
        self.profile.update_data("actual_contribution", actual_contribution)
        self.profile.update_data("last_reasoning", reasoning)
        # Create and send FollowerContributionResultEvent to all target agents
        events = []
        for target_id in target_ids:
            contribution_result_event = FollowerContributionResultEvent(
                from_agent_id=self.profile_id,
                to_agent_id=target_id,
                actual_contribution=actual_contribution,
            )
            events.append(contribution_result_event)
        
        return events
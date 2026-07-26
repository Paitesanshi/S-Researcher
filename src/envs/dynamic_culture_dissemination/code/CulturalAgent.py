from typing import Any, List, Optional, Dict, Tuple
import asyncio
import random
from loguru import logger
from onesim.agent import GeneralAgent
from onesim.profile import AgentProfile
from onesim.memory import MemoryStrategy
from onesim.planning import PlanningBase
from onesim.events import Event
from onesim.relationship import RelationshipManager
from .events import RecommendationEvent, AdoptionEvent

class CulturalAgent(GeneralAgent):
    
    CULTURAL_DIMENSIONS = [
        "music_preference",
        "culinary_preference", 
        "fashion_style", 
        "political_orientation", 
        "leisure_activity"
    ]
    
    def __init__(self,
                 sys_prompt: str | None = None,
                 model_config_name: str = None,
                 event_bus_queue: asyncio.Queue = None,
                 profile: AgentProfile = None,
                 memory: MemoryStrategy = None,
                 planning: PlanningBase = None,
                 relationship_manager: RelationshipManager = None) -> None:
        
        if sys_prompt is None:
            sys_prompt = self.create_cultural_agent_sys_prompt()
            
        super().__init__(sys_prompt, model_config_name, event_bus_queue, profile, memory, planning, relationship_manager)
        self.register_event("StartEvent", "send_recommendation")
        self.register_event("RecommendationEvent", "receive_recommendation")
        
        if not self.profile.get_data("trait_explanations"):
            self.initialize_trait_explanations()

    def create_cultural_agent_sys_prompt(self):
        return """You are a CulturalAgent in a cultural dissemination simulation.

You have cultural traits across five dimensions (music, food, fashion, politics, leisure).

When making decisions about cultural interactions, consider your own preferences, your cultural similarity with others, and the cultural dynamics of the simulation.
"""

    def get_cultural_traits(self) -> Dict[str, str]:
        traits = {}
        for dimension in self.CULTURAL_DIMENSIONS:
            traits[dimension] = self.profile.get_data(dimension, "")
        return traits

    def initialize_trait_explanations(self):
        traits = self.get_cultural_traits()
        explanations = {}
        for dimension, trait_value in traits.items():
            if trait_value:  # Explain only dimensions that have a value.
                explanations[dimension] = f"I value {trait_value} because it aligns with my personal preferences."
        
        self.profile.update_data("trait_explanations", explanations)

    def calculate_similarity(self, other_traits: Dict[str, str]) -> float:
        my_traits = self.get_cultural_traits()
        if not my_traits or not other_traits:
            return 0.0
        
        all_dimensions = set(my_traits.keys()).union(other_traits.keys())
        
        shared_count = 0
        for dim in all_dimensions:
            if dim in my_traits and dim in other_traits and my_traits[dim] == other_traits[dim]:
                shared_count += 1
        
        return shared_count / len(all_dimensions) if all_dimensions else 0.0

    def find_different_dimensions(self, other_traits: Dict[str, str]) -> List[Dict[str, str]]:
        my_traits = self.get_cultural_traits()
        different_dims = []
        
        for dim in self.CULTURAL_DIMENSIONS:
            if dim in my_traits and dim in other_traits and my_traits[dim] != other_traits[dim]:
                different_dims.append({
                    "dimension": dim,
                    "current_value": my_traits[dim],
                    "other_value": other_traits[dim]
                })
                
        return different_dims

    async def send_recommendation(self, event: Event) -> List[Event]:
        
        traits = self.get_cultural_traits()
        if not traits:
            logger.warning(f"Agent {self.profile_id} doesn't have cultural traits")
            return []

        relationships = self.relationship_manager.get_all_relationships()
        potential_targets = []
        
        for relation in relationships:
            if relation.target_id == "ENV":
                continue
                
            target_info = relation.get_target_info()
            
            target_traits = {}
            for dimension in self.CULTURAL_DIMENSIONS:
                if dimension in target_info:
                    target_traits[dimension] = target_info.get(dimension, "")
            
            similarity = self.calculate_similarity(target_traits)

            target_name = target_info.get("name", relation.target_id)

            potential_targets.append({
                "id": relation.target_id,
                "name": target_name,
                "similarity": similarity,
                "traits": target_traits
            })
        
        if not potential_targets:
            logger.warning(f"Agent {self.profile_id} has no potential targets")
            return []
            
        instruction = """
        Choose ONE agent from your social network to share your cultural traits with.

        Select a target and explain why you chose them.

        Return your decision in this JSON format:
        {
            "target_id": "<ID of the chosen agent>",
            "reason": "<Brief explanation for your choice (1-2 sentences)>"
        }
        """
        
        my_profile = ", ".join([f"{dim.replace('_', ' ')}: {val}" for dim, val in traits.items() if val])
        
        targets_info = ""
        for target in potential_targets:
            target_profile = ", ".join([f"{dim.replace('_', ' ')}: {val}" for dim, val in target["traits"].items() if val])
            targets_info += f"- ID: {target['id']}, Similarity: {target['similarity']:.2f}\n  Cultural traits: {target_profile}\n\n"
        
        observation = f"""
        YOUR CULTURAL PROFILE:
        {my_profile}
        
        POTENTIAL INTERACTION TARGETS:
        {targets_info}
        """
        
        result = await self.generate_reaction(instruction, observation)
        
        target_id = result.get('target_id')
        reason = result.get('reason', "This agent seems most receptible to cultural influence.")
        
        if not target_id or not any(t["id"] == target_id for t in potential_targets):
            logger.warning(f"Agent {self.profile_id} selected invalid target: {target_id}")
            if potential_targets:
                target = random.choice(potential_targets)
                target_id = target["id"]
                logger.info(f"Falling back to random target: {target_id}")
            else:
                return []
        
        target_traits = {}
        similarity = 0.0
        for t in potential_targets:
            if t["id"] == target_id:
                target_traits = t["traits"]
                similarity = t["similarity"]
                break
        
        recommendation_history = self.profile.get_data("recommendation_history", [])
        recommendation_history.append({
            "round": await self.env.get_data("round_number", 0),
            "target_id": target_id,
            "similarity": similarity,
            "reason": reason
        })
        if len(recommendation_history)>10:
            recommendation_history=recommendation_history[-10:]
        self.profile.update_data("recommendation_history", recommendation_history)
        
        recommendation_event = RecommendationEvent(
            from_agent_id=self.profile_id,
            to_agent_id=target_id,
            cultural_traits=traits,
            reason=reason
        )
        
        # logger.info(f"Agent {self.profile_id} sends cultural traits to Agent {target_id} (similarity: {similarity:.2f})")
        return [recommendation_event]

    async def receive_recommendation(self, event: Event) -> List[Event]:
        """
        """

        recommender_id = event.from_agent_id
        recommender_traits = event.cultural_traits
        reason = event.reason
        
        my_traits = self.get_cultural_traits()
        
        similarity = self.calculate_similarity(recommender_traits)
        
        if similarity == 0.0 or similarity == 1.0:
            logger.info(f"Agent {self.profile_id} and {recommender_id} have similarity {similarity}, no transmission")
            
            adoption_history = self.profile.get_data("adoption_history", [])
            adoption_history.append({
                "round": await self.env.get_data("round_number", 0),
                "recommender": recommender_id,
                "similarity": similarity,
                "adopted": False,
                "reasoning": f"Similarity is {similarity}, no cultural transmission occurs"
            })
            self.profile.update_data("adoption_history", adoption_history)
            
            adoption_event = AdoptionEvent(
                from_agent_id=self.profile_id,
                to_agent_id="ENV",
                dimension="",
                old_value="",
                new_value="",
                adopted=False,
                round_number=await self.env.get_data("round_number", 0)
            )
            
            return [adoption_event]
        
        different_dimensions = self.find_different_dimensions(recommender_traits)
        
        if not different_dimensions:
            logger.warning(f"Agent {self.profile_id} and {recommender_id} have no different dimensions despite similarity {similarity}")
            
            adoption_event = AdoptionEvent(
                from_agent_id=self.profile_id,
                to_agent_id="ENV",
                dimension="",
                old_value="",
                new_value="",
                adopted=False,
                round_number=await self.env.get_data("round_number", 0)
            )
            
            return [adoption_event]
        
        instruction = """
        You've received cultural recommendations from another agent.

        From the differences between your cultures, choose ONE dimension to adopt from them.

        Return your decision in this JSON format:
        {
            "adopt_dimension": "<dimension_name>",
            "reasoning": "<Brief explanation for your choice (1-2 sentences)>"
        }
        """
        
        my_profile = ", ".join([f"{dim.replace('_', ' ')}: {val}" for dim, val in my_traits.items() if val])
        recommender_profile = ", ".join([f"{dim.replace('_', ' ')}: {val}" for dim, val in recommender_traits.items() if val])
        
        personality = self.profile.get_data("personality_trait", "neutral")
        
        differences_info = ""
        for diff in different_dimensions:
            differences_info += f"- {diff['dimension'].replace('_', ' ')}:\n"
            differences_info += f"  Your current: {diff['current_value']}\n"
            differences_info += f"  Their value: {diff['other_value']}\n\n"
        
        observation = f"""
        CULTURAL EXCHANGE INFORMATION:
        Recommender: Agent {recommender_id}
        Similarity: {similarity:.2f}
        Your personality: {personality}
        Recommender's explanation: "{reason}"
        
        RECOMMENDER'S CULTURAL PROFILE:
        {recommender_profile}
        
        CULTURAL DIFFERENCES (potential to adopt):
        {differences_info}
        """
        
        result = await self.generate_reaction(instruction, observation)
        
        adopt_dimension = result.get('adopt_dimension', '').lower().replace(' ', '_')
        reasoning = result.get('reasoning', "This cultural trait seems valuable to adopt.")
        
        valid_dimension = False
        dimension_info = None
        for diff in different_dimensions:
            if diff['dimension'] == adopt_dimension:
                valid_dimension = True
                dimension_info = diff
                break
        
        if not valid_dimension:
            logger.warning(f"Agent {self.profile_id} selected invalid dimension: {adopt_dimension}")
            dimension_info = random.choice(different_dimensions)
            adopt_dimension = dimension_info['dimension']
            logger.info(f"Falling back to random dimension: {adopt_dimension}")
        
        old_value = dimension_info['current_value']
        new_value = dimension_info['other_value']
        
        self.profile.update_data(adopt_dimension, new_value)
        
        trait_explanations = self.profile.get_data("trait_explanations", {})
        trait_explanations[adopt_dimension] = reasoning
        self.profile.update_data("trait_explanations", trait_explanations)
        
        adoption_history = self.profile.get_data("adoption_history", [])
        adoption_history.append({
            "round": await self.env.get_data("round_number", 0),
            "dimension": adopt_dimension,
            "old_value": old_value,
            "new_value": new_value,
            "recommender": recommender_id,
            "similarity": similarity,
            "adopted": True,
            "reasoning": reasoning
        })
        if len(adoption_history)>10:
            adoption_history=adoption_history[-10:]
        self.profile.update_data("adoption_history", adoption_history)
        
        #logger.info(f"Agent {self.profile_id} adopted {adopt_dimension}: {new_value} from {recommender_id}")
        
        adoption_event = AdoptionEvent(
            from_agent_id=self.profile_id,
            to_agent_id="ENV",
            dimension=adopt_dimension,
            old_value=old_value,
            new_value=new_value,
            adopted=True,
            round_number=await self.env.get_data("round_number", 0)
        )
        
        return [adoption_event]

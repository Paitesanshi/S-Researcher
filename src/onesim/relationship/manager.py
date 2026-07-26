# relationship_manager.py

from typing import Dict, List, Optional
from loguru import logger

class Relationship:
    def __init__(self, source_id:str,target_id: str, description: str,target_info: Optional[Dict]=None):
        self.source_id = source_id
        self.target_id = target_id
        self.description = description
        self.target_info = target_info
    def __str__(self):
        target_info_str = f"Target Info: {self.target_info}" if self.target_info else ""
        return f"Relationship(Target ID: {self.target_id}, {target_info_str}, Relationship Description: {self.description})"

    def __repr__(self):
        return self.__str__()
    
    def get_target_info(self):
        return self.target_info

class RelationshipManager:
    def __init__(self, profile_id: str):
        self.profile_id = profile_id
        self.relationships: Dict[str, Relationship] = {}

    def add_relationship(self, target_id: str, description: str,target_info: Optional[Dict]=None):
        self.relationships[target_id] = Relationship(self.profile_id,target_id, description,target_info)
        #logger.debug(f"Relationship added: {self.profile_id} -> {target_id} : {description}")

    def remove_relationship(self, target: str):
        if target in self.relationships:
            del self.relationships[target]
            logger.debug(f"Relationship removed: {self.profile_id} -> {target}")
        else:
            logger.debug(f"No relationship found from {self.profile_id} to {target}")

    def update_relationship(self, target: str, description: str):
        if target in self.relationships:
            self.relationships[target].description = description
            logger.debug(f"Relationship updated: {self.profile_id} -> {target} : {description}")
        else:
            logger.debug(f"No relationship found from {self.profile_id} to {target}")

    def get_relationship(self, target: str) -> Optional[Relationship]:
        return self.relationships.get(target)

    def get_all_relationships(self) -> List[Relationship]:
        return list(self.relationships.values())
    
    def get_all_relationships_str(self) -> List[str]:
        return [str(rel) for rel in self.relationships.values()]

    def get_relationships_by_agent_types(self, agent_types: List[str]) -> List[Relationship]:
        """
        Filter relationships whose target agent_type is in agent_types.

        Note:
            Relationship stores target type inside rel.target_info["agent_type"] (if provided).
        """
        res: List[Relationship] = []
        for rel in self.relationships.values():
            target_type = None
            if getattr(rel, "target_info", None) and isinstance(rel.target_info, dict):
                target_type = rel.target_info.get("agent_type")
            if target_type in agent_types:
                res.append(rel)
        return res
import uuid
import time


class MemoryItem:
    def __init__(self, agent_id, content, attributes=None, embedding=None):
        self.agent_id = agent_id
        self.id = uuid.uuid4()
        self.content = content
        self.timestamp = time.time()
        self.attributes = dict(attributes) if attributes is not None else {}
        self.embedding = embedding

    def __repr__(self):
        return f"MemoryItem(id={self.id}, content='{self.content}', attributes={self.attributes})"

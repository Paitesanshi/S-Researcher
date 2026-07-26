from onesim.simulator import BasicSimEnv
from onesim.events import Event
from .events import StartEvent
from datetime import datetime

class SimEnv(BasicSimEnv):
    async def _create_start_event(self, target_id: str) -> Event:
        # Extract relevant information from self.data using key parameters
        source_id = self.data.get('environment_id', 'ENVSYS')
        mechanism = self.data.get('decision_mechanism', 'voluntary')
        initial_contribution = self.data.get('initial_contribution', 0)
        
        # Create StartEvent with extracted information
        return StartEvent(
            from_agent_id=source_id,
            to_agent_id=target_id,
            mechanism=mechanism,
            initial_contribution=initial_contribution,
            timestamp=datetime.now()
        )
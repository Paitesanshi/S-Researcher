from typing import List, Optional
import asyncio
import random
import math
from loguru import logger
from onesim.agent import GeneralAgent
from onesim.profile import AgentProfile
from onesim.memory import MemoryStrategy
from onesim.planning import PlanningBase
from onesim.relationship import RelationshipManager
from .events import *

class TeacherAgent(GeneralAgent):
    def __init__(self,
                 sys_prompt: Optional[str] = None,
                 model_config_name: Optional[str] = None,
                 event_bus_queue: asyncio.Queue = None,
                 profile: Optional[AgentProfile] = None,
                 memory: Optional[MemoryStrategy] = None,
                 planning: Optional[PlanningBase] = None,
                 relationship_manager: Optional[RelationshipManager] = None) -> None:
        super().__init__(sys_prompt, model_config_name, event_bus_queue, profile, memory, planning, relationship_manager)
        self.register_event("StartEvent", "pose_question")
        self.register_event("ResponseProvidedEvent", "evaluate_responses")

    async def pose_question(self, _event: Event) -> List[Event]:
        """
        Generate a question with difficulty level and broadcast it to ALL students.

        Flow:
        1. Use generate_reaction to create question content and difficulty
        2. Get ALL student IDs from relationships
        3. Broadcast QuestionPosedEvent to all students
        4. Initialize response buffer
        """
        # Step 1: Use generate_reaction to create question content and difficulty
        observation = "Starting a new classroom question round"
        instruction = """
        You are a middle school math teacher preparing to ask a question in class.
        Generate a math question appropriate for students and assign a difficulty level.

        Return in JSON format:
        {
            "question_content": "Your question here (e.g., about triangles, equations, geometry, etc.)",
            "difficulty": 0.5,
            "target_ids": []
        }

        Note:
        - difficulty is a float between 0 (easy) and 1 (hard)
        - target_ids should be empty list (we will broadcast to all students automatically)
        """

        result = await self.generate_reaction(instruction, observation)
        if not result:
            logger.error("Failed to generate question")
            return []

        question_content = result.get('question_content', '')
        difficulty = result.get('difficulty', 0.5)

        # Step 2: Get ALL student IDs from relationships
        # logger.info(f"Relationships: {self.relationships}")
        student_ids = [
            rel.target_id
            for rel in self.relationships
            if rel.target_info and rel.target_info.get('agent_type') == 'StudentAgent'
        ]

        if not student_ids:
            logger.error("No student relationships found")
            return []

        # Step 3: Broadcast to ALL students
        events = []
        for student_id in student_ids:
            events.append(QuestionPosedEvent(
                from_agent_id=self.profile_id,
                to_agent_id=student_id,
                question_content=question_content,
                difficulty=difficulty
            ))

        # Step 4: Record question and initialize response buffer
        question_log = await self.get_data("question_log", [])
        question_log.append({"content": question_content, "difficulty": difficulty})
        await self.update_data("question_log", question_log)
        await self.update_data("current_question", {"content": question_content, "difficulty": difficulty})
        await self.update_data("responses_buffer", [])  # Initialize buffer
        await self.update_data("expected_responses", len(student_ids))  # Track how many responses to expect
        await self.update_data("wait_counter", 0)  # Reset wait counter for new question

        return events

    async def evaluate_responses(self, event: ResponseProvidedEvent) -> List[Event]:
        """
        Collect all student responses (raised and not raised), then select ONE student.

        This is an AND-type action that gets triggered by each ResponseProvidedEvent.
        We maintain a responses_buffer and only make selection when all responses are received.

        Flow:
        1. Add this response to buffer
        2. Check if we've received all responses
        3. If not all received: return [] and wait
        4. If all received: use generate_reaction to select ONE student
        5. Record attention distribution
        6. Send AttentionAllocatedEvent to ENV
        """
        # Step 1: Add this response to buffer
        responses_buffer = await self.get_data("responses_buffer", [])
        responses_buffer.append({
            "student_id": event.student_id,
            "will_raise_hand": event.will_raise_hand,
            "gesture_description": event.gesture_description,
            "response_content": event.response_content,
            "response_type": event.response_type,
            # structured signals (may be None)
            "expression_score": getattr(event, "expression_score", None),
            "achievement_score": getattr(event, "achievement_score", None),
            "ses_score": getattr(event, "ses_score", None),
        })
        await self.update_data("responses_buffer", responses_buffer)

        # Step 2: Check if we've received all responses (with timeout protection)
        expected_responses = await self.get_data("expected_responses", 0)
        # wait_counter = await self.get_data("wait_counter", 0)

        if len(responses_buffer) < expected_responses:
            # Wait until all expected responses have arrived.
            # await self.update_data("wait_counter", wait_counter + 1)
            # logger.warning(f"Received {len(responses_buffer)}/{expected_responses} responses, wait cycle {wait_counter + 1}/{MAX_WAIT_CYCLES}")
            return []  # Wait for more responses

        # Reset the wait counter when timeout handling is enabled.
        #await self.update_data("wait_counter", 0)

        # if force_proceed:
        #     logger.error(f"TIMEOUT: Only received {len(responses_buffer)}/{expected_responses} responses after {MAX_WAIT_CYCLES} cycles, proceeding with available data")
        # else:
        logger.info(f"All {expected_responses} responses received, making selection...")

        # --------- Teacher memory / state for realism (LLM-visible) ----------
        # Provide the LLM with lightweight, structured signals (frequency + recency)
        # so it can form human-like but bounded patterns (avoids purely random or purely uniform outcomes).
        attention_distribution_hist = await self.get_data("attention_distribution", [])
        selection_counts_hist: dict[str, int] = {}
        last_selected_round: dict[str, int] = {}
        for ridx, round_selections in enumerate(attention_distribution_hist, start=1):
            for selection in round_selections:
                sid = selection.get("selected_student_id")
                if not sid:
                    continue
                selection_counts_hist[sid] = selection_counts_hist.get(sid, 0) + 1
                last_selected_round[sid] = ridx
        current_round_for_context = len(attention_distribution_hist) + 1

        # Treatment differences come ONLY from teacher profile `decision_logic` (in projects/*/groups/* profiles).
        decision_logic = await self.get_data("decision_logic", "")

        # Step 4: Prepare observation with ALL student information
        # IMPORTANT: generate_reaction automatically includes relationships,
        # so the LLM can see all students' background info (prompt_summary)
        current_question = await self.get_data("current_question", {})
        observation = f"""
        Question asked: {current_question.get('content', '')}
        Difficulty: {current_question.get('difficulty', 0.5)}

        All student reactions ({len(responses_buffer)} students):
        """

        # Format responses for clarity
        raised_students = []
        not_raised_students = []
        for resp in responses_buffer:
            if resp['will_raise_hand']:
                raised_students.append(resp)
            else:
                not_raised_students.append(resp)

        # Enhanced history formatting: emphasize frequency patterns for faster convergence
        observation += f"\n\nStudents who RAISED HANDS ({len(raised_students)}):\n"
        for resp in raised_students:
            sid = resp.get("student_id", "")
            cnt = selection_counts_hist.get(sid, 0)
            last_r = last_selected_round.get(sid)
            gap = (current_round_for_context - last_r) if last_r is not None else None
            gap_txt = f"{gap}r ago" if gap is not None else "never"
            observation += (
                f"- {sid}: {resp['gesture_description']} | "
                f"expr={resp.get('expression_score')}, ach={resp.get('achievement_score')}, ses={resp.get('ses_score')} | "
                f"called={cnt}, last={gap_txt}\n"
            )

        observation += f"\n\nStudents who DID NOT raise hands ({len(not_raised_students)}):\n"
        for resp in not_raised_students:
            sid = resp.get("student_id", "")
            cnt = selection_counts_hist.get(sid, 0)
            last_r = last_selected_round.get(sid)
            gap = (current_round_for_context - last_r) if last_r is not None else None
            gap_txt = f"{gap}r ago" if gap is not None else "never"
            observation += (
                f"- {sid}: {resp['gesture_description']} | "
                f"expr={resp.get('expression_score')}, ach={resp.get('achievement_score')}, ses={resp.get('ses_score')} | "
                f"called={cnt}, last={gap_txt}\n"
            )

        # Step 5: Use generate_reaction to select MULTIPLE students

        # Build instruction with emphasis on consistency for faster pattern formation
        instruction = f"""
        You are a middle school teacher who just asked a question to the class (Round {current_round_for_context}).
        You received reactions from ALL students (some raised hands, some didn't).

        **Your Task:**
        Select multiple students to call on for answering the question or participating in discussion.

        **Available Information:**
        Your relationships data includes all students' background information in prompt_summary:
        - Academic performance and achievement levels
        - Family background and socioeconomic status
        - Communication skills and classroom behavior patterns
        - How many times each student has been called before (called=N) and when they were last called

        Each student's current reaction includes:
        - Whether they raised their hand (eager to participate)
        - Gesture description (body language, confidence level, engagement signals)
        - Three numeric scores: expression ability (expr), academic achievement (ach), socioeconomic status (ses)
        """

        # Add teaching philosophy if it exists (this is where treatment differences come from)
        if decision_logic:
            instruction += f"""
        **Your Teaching Philosophy:**
        {decision_logic}

        Let this philosophy naturally guide your choices, as it would for any real teacher.
        """
        else:
            instruction += """
        **Your Teaching Philosophy:**
        You are a well-rounded teacher who considers multiple factors when deciding which students to call on,
        including participation eagerness, academic needs, and fairness.
        """

        # Common instructions for all teachers
        instruction += """
        **Selection Strategy:**
        - Identify a candidate pool of students to call on (about 10-15 students, ~1/3–1/2 of the class), ordered by how well they fit your teaching philosophy.
        - The system will call on 4-8 students this round from your ordered candidate pool.
        - Make your choices as a real teacher would — balancing your philosophy with practical classroom considerations.

        Return in JSON format:
        {{
            "selected_student_ids": ["student_id_1", "student_id_2", "... (10-15 ids, best to worst) ..."],
            "target_ids": ["ENV"]
        }}

        Note:
        - selected_student_ids should be an ordered candidate list (10-15 IDs). Put your best choices first.
        - Do not include explanations; only output JSON.
        """

        # Always select a valid set of students when the model fails.
        try:
            result = await self.generate_reaction(instruction, observation)
            if not result:
                logger.error("Teacher LLM returned None, using fallback selection")
                # Select three to five students from the received responses.
                available_students = [r['student_id'] for r in responses_buffer if r.get('student_id')]
                if available_students:
                    num_to_select = min(random.randint(3, 5), len(available_students))
                    selected_student_ids = random.sample(available_students, num_to_select)
                    selection_reasons = {
                        sid: "Random fallback selection"
                        for sid in selected_student_ids
                    }
                    allocated_attention = 1.0
                else:
                    # No selection is possible without any student response.
                    logger.critical("No student responses available, cannot proceed")
                    return []
            else:
                selected_student_ids = result.get('selected_student_ids', [])
                if not isinstance(selected_student_ids, list):
                    selected_student_ids = [selected_student_ids] if selected_student_ids else []

                allocated_attention = result.get('allocated_attention', 1.0)

        except Exception as e:
            logger.error(f"Teacher LLM exception: {e}, using fallback selection")
            # Select three to five students from the received responses.
            available_students = [r['student_id'] for r in responses_buffer if r.get('student_id')]
            if available_students:
                num_to_select = min(random.randint(3, 5), len(available_students))
                selected_student_ids = random.sample(available_students, num_to_select)
                allocated_attention = 1.0
            else:
                logger.critical("No student responses available, cannot proceed")
                return []

        # ========== Order-preserving post-processing ==========
        # We do NOT add new decision variables or fairness constraints here.
        # We only introduce controlled stochasticity over the LLM-proposed ordered list,
        # preserving treatment effects (ranking) while avoiding brittle/extreme outcomes.
        # - We sample WITHOUT replacement from the LLM list using rank-based softmax.
        # - Optionally mix a small uniform component over the same list (still order-preserving in expectation).

        # De-duplicate while preserving order
        ordered = []
        seen = set()
        for sid in selected_student_ids:
            if sid and sid not in seen:
                ordered.append(sid)
                seen.add(sid)

        # Determine how many to call this round (keep within 4-8, default 6)
        target_k = 6
        target_k = max(4, min(8, target_k))
        # keep target_k even if ordered list is short; we'll fill from roster as safety
        target_k = target_k if target_k > 0 else 0

        if target_k > 0 and len(ordered) > target_k:
            # Dynamic parameters based on round number for faster convergence
            # Early rounds: sharper sampling to quickly establish patterns
            # Later rounds: maintain stable patterns with slight exploration
            current_round = len(attention_distribution_hist) + 1
            
            # # Temperature decay: starts lower (more focused), gradually increases
            # tau = 0.75 + 0.35 * min(1.0, current_round / 3.0)  # 0.75→1.10 over first 3 rounds
            
            # # Uniform mixing: starts lower (more deterministic), slightly increases
            # lam = 0.03 + 0.05 * min(1.0, current_round / 5.0)  # 0.03→0.08 over first 5 rounds
            tau=1.2
            lam=0.1
            
            # rank logits: higher rank -> higher weight
            logits = [-(i / tau) for i in range(len(ordered))]
            m = max(logits)
            exps = [math.exp(x - m) for x in logits]
            s = sum(exps) if exps else 1.0
            probs = [(1 - lam) * (e / s) + lam * (1.0 / len(ordered)) for e in exps]

            # sample WITHOUT replacement from ordered list
            pool_ids = list(ordered)
            pool_p = list(probs)
            sampled = []
            for _ in range(target_k):
                # normalize
                sp = sum(pool_p)
                if sp <= 0:
                    pool_p = [1.0 / len(pool_p)] * len(pool_p)
                else:
                    pool_p = [p / sp for p in pool_p]
                r = random.random()
                cum = 0.0
                idx = None
                for i, p in enumerate(pool_p):
                    cum += p
                    if r <= cum:
                        idx = i
                        break
                if idx is None:
                    idx = len(pool_ids) - 1
                sampled_id = pool_ids.pop(idx)
                pool_p.pop(idx)
                sampled.append(sampled_id)

            selected_student_ids = sampled
        else:
            selected_student_ids = ordered[:target_k] if target_k > 0 else ordered

        # Safety: if LLM list is too short, fill remaining from full roster (avoid many never-called students)
        if target_k > 0 and len(selected_student_ids) < target_k:
            roster_ids = [r.get("student_id") for r in responses_buffer if isinstance(r, dict) and r.get("student_id")]
            remaining_pool = [sid for sid in roster_ids if sid and sid not in set(selected_student_ids)]
            if remaining_pool:
                need = min(target_k - len(selected_student_ids), len(remaining_pool))
                selected_student_ids.extend(random.sample(remaining_pool, need))

        logger.info(f"Final selection (order-preserving): {len(selected_student_ids)} students")
        # ========== End post-processing ==========

        # Step 6: Record attention distribution for each selected student
        attention_distribution = await self.get_data("attention_distribution", [])
        current_attention_distribution=[]
        # IMPORTANT for Nature narrative:
        # We evaluate attention as "being called on" frequency. Each call contributes 1 unit.
        # This keeps the mechanism simple and avoids inventing a continuous attention-score output.
        for student_id in selected_student_ids:
            current_attention_distribution.append({
                # "round": len(attention_distribution) + 1,
                "selected_student_id": student_id,
                # "reason": selection_reasons.get(student_id, "Selected for participation"),
                # "question": current_question.get('content', ''),
                # "difficulty": current_question.get('difficulty', 0.5),
                "attention_value": 1.0,
                # "total_selected": len(selected_student_ids)
            })
        attention_distribution.append(current_attention_distribution)
        await self.update_data("attention_distribution", attention_distribution)

        # Step 7: Clear buffer for next round
        await self.update_data("responses_buffer", [])

        # Step 8: Send AttentionAllocatedEvent to ENV (simulation end)
        logger.info(f"Selected {len(selected_student_ids)} students: {selected_student_ids}")

        return [AttentionAllocatedEvent(
            from_agent_id=self.profile_id,
            to_agent_id="ENV",
            allocated_attention=allocated_attention,
            student_ids=selected_student_ids
        )]

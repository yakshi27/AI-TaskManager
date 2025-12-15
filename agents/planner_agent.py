"""
Planner Agent: Creates detailed day-by-day study schedules.
Distributes topics logically across the study period.
"""

import json
import re
from typing import Dict, Any, List
import google.generativeai as genai
from utils.prompts import PLANNER_PROMPT


class PlannerAgent:
    """Agent responsible for creating study schedules."""
    
    def __init__(self, model: genai.GenerativeModel):
        """
        Initialize the Planner Agent.
        
        Args:
            model: Configured Gemini model instance
        """
        self.model = model
    
    def create_schedule(self, parsed_goal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create a detailed study schedule based on parsed goal.
        
        Args:
            parsed_goal: Dictionary with total_days, hours_per_day, topics, goal_summary
            
        Returns:
            List of dictionaries representing the schedule for each day
        """
        print(f"\n📅 Planner Agent: Creating study schedule...")
        
        total_days = parsed_goal.get("total_days", 30)
        hours_per_day = parsed_goal.get("hours_per_day", 2.0)
        topics = parsed_goal.get("topics", [])
        
        try:
            # Generate prompt
            prompt = PLANNER_PROMPT.format(
                parsed_goal=json.dumps(parsed_goal, indent=2),
                total_days=total_days,
                hours_per_day=hours_per_day,
                topics=", ".join(topics)
            )
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            schedule = self._extract_json(response_text)
            
            # Validate and fix the schedule
            validated_schedule = self._validate_and_fix_schedule(
                schedule, total_days, hours_per_day, topics
            )
            
            print(f"✅ Schedule created successfully")
            print(f"   📅 Total days: {len(validated_schedule)}")
            print(f"   📚 Topics distributed across days")
            
            return validated_schedule
            
        except Exception as e:
            print(f"⚠️ Error creating schedule with AI: {e}")
            print("🔄 Falling back to template schedule...")
            return self._create_fallback_schedule(total_days, hours_per_day, topics)
    
    def _extract_json(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract JSON array from LLM response text.
        
        Args:
            text: Response text that may contain JSON
            
        Returns:
            Parsed JSON array
        """
        # Try to find JSON in code blocks
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        
        # Try to find JSON array
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        
        # Parse JSON
        return json.loads(text)
    
    def _validate_and_fix_schedule(
        self,
        schedule: List[Dict[str, Any]],
        total_days: int,
        hours_per_day: float,
        topics: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Validate and fix schedule data.
        
        Args:
            schedule: Schedule from AI
            total_days: Expected number of days
            hours_per_day: Expected daily hours
            topics: Topics to cover
            
        Returns:
            Validated and fixed schedule
        """
        if not isinstance(schedule, list):
            return self._create_fallback_schedule(total_days, hours_per_day, topics)
        
        validated = []
        
        # Ensure we have exactly total_days entries
        for i in range(1, total_days + 1):
            if i - 1 < len(schedule):
                day_data = schedule[i - 1]
            else:
                # Create missing day
                day_data = {
                    "day": i,
                    "topic": topics[(i - 1) % len(topics)] if topics else f"Day {i}",
                    "duration_hours": hours_per_day,
                    "status": "pending",
                    "notes": "Study session"
                }
            
            # Validate day number
            day_data["day"] = i
            
            # Validate topic
            if not day_data.get("topic"):
                day_data["topic"] = topics[(i - 1) % len(topics)] if topics else f"Study Day {i}"
            
            # Validate duration
            duration = day_data.get("duration_hours", hours_per_day)
            if not isinstance(duration, (int, float)) or duration <= 0:
                duration = hours_per_day
            day_data["duration_hours"] = float(min(max(duration, 0.5), 12.0))
            
            # Validate status
            if day_data.get("status") not in ["pending", "done"]:
                day_data["status"] = "pending"
            
            # Validate notes
            if not day_data.get("notes"):
                day_data["notes"] = "Focus on understanding core concepts"
            else:
                day_data["notes"] = str(day_data["notes"])[:200]
            
            validated.append(day_data)
        
        return validated
    
    def _create_fallback_schedule(
        self,
        total_days: int,
        hours_per_day: float,
        topics: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Create a fallback schedule when AI generation fails.
        
        Args:
            total_days: Number of days in schedule
            hours_per_day: Hours per day
            topics: List of topics to cover
            
        Returns:
            Fallback schedule
        """
        if not topics:
            topics = ["Study Session"] * total_days
        
        # Expand topics to cover all days
        expanded_topics = []
        days_per_topic = max(1, total_days // len(topics))
        
        for topic in topics:
            expanded_topics.extend([topic] * days_per_topic)
        
        # Adjust to exact day count
        expanded_topics = expanded_topics[:total_days]
        while len(expanded_topics) < total_days:
            expanded_topics.append(topics[-1] if topics else "Study Session")
        
        # Create schedule
        schedule = []
        for day in range(1, total_days + 1):
            topic_idx = min(day - 1, len(expanded_topics) - 1)
            topic = expanded_topics[topic_idx]
            
            schedule.append({
                "day": day,
                "topic": topic,
                "duration_hours": hours_per_day,
                "status": "pending",
                "notes": f"Study {topic}" if topic else f"Study Day {day}"
            })
        
        return schedule

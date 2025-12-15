"""
Goal Parsing Agent: Intelligently extracts structured information from user goals.
Handles vague, incomplete, detailed, or ambiguous inputs with robust fallback logic.
"""

import json
import re
from typing import Dict, Any, List
import google.generativeai as genai
from utils.prompts import GOAL_PARSING_PROMPT


class GoalAgent:
    """Agent responsible for parsing and structuring user study goals."""
    
    def __init__(self, model: genai.GenerativeModel):
        """
        Initialize the Goal Agent.
        
        Args:
            model: Configured Gemini model instance
        """
        self.model = model
    
    def parse_goal(self, user_goal: str) -> Dict[str, Any]:
        """
        Parse a user's free-text goal into structured data.
        
        Args:
            user_goal: Free-text study goal from user
            
        Returns:
            Dictionary with keys: total_days, hours_per_day, topics, goal_summary
        """
        print(f"\n🤖 Goal Agent: Parsing goal...")
        
        # Validate input
        if not user_goal or not user_goal.strip():
            print("⚠️ Empty goal provided, using default")
            return self._create_default_goal()
        
        try:
            # Generate prompt
            prompt = GOAL_PARSING_PROMPT.format(user_goal=user_goal.strip())
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            parsed_data = self._extract_json(response_text)
            
            # Validate and fix the parsed data
            validated_data = self._validate_and_fix_goal(parsed_data, user_goal)
            
            print(f"✅ Goal parsed successfully")
            print(f"   📅 Duration: {validated_data['total_days']} days")
            print(f"   ⏰ Daily hours: {validated_data['hours_per_day']}")
            print(f"   📚 Topics: {len(validated_data['topics'])}")
            
            return validated_data
            
        except Exception as e:
            print(f"⚠️ Error parsing goal with AI: {e}")
            print("🔄 Falling back to intelligent defaults...")
            return self._create_fallback_goal(user_goal)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response text.
        
        Args:
            text: Response text that may contain JSON
            
        Returns:
            Parsed JSON dictionary
        """
        # Try to find JSON in code blocks
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        
        # Try to find JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        
        # Parse JSON
        return json.loads(text)
    
    def _validate_and_fix_goal(self, data: Dict[str, Any], original_goal: str) -> Dict[str, Any]:
        """
        Validate parsed goal data and fix any issues.
        
        Args:
            data: Parsed goal data
            original_goal: Original user goal text
            
        Returns:
            Validated and fixed goal data
        """
        result = {}
        
        # Validate total_days
        total_days = data.get("total_days", 30)
        if not isinstance(total_days, (int, float)) or total_days < 1:
            total_days = 30
        result["total_days"] = int(min(max(total_days, 1), 365))  # Between 1 and 365 days
        
        # Validate hours_per_day
        hours_per_day = data.get("hours_per_day", 2.0)
        if not isinstance(hours_per_day, (int, float)) or hours_per_day < 0.5:
            hours_per_day = 2.0
        result["hours_per_day"] = float(min(max(hours_per_day, 0.5), 12.0))  # Between 0.5 and 12 hours
        
        # Validate topics
        topics = data.get("topics", [])
        if not isinstance(topics, list) or len(topics) == 0:
            topics = self._extract_topics_from_text(original_goal)
        result["topics"] = [str(t).strip() for t in topics if str(t).strip()][:20]  # Max 20 topics
        
        # Ensure we have at least 3 topics
        if len(result["topics"]) < 3:
            result["topics"] = self._expand_topics(result["topics"], original_goal)
        
        # Validate goal_summary
        goal_summary = data.get("goal_summary", "")
        if not goal_summary or not isinstance(goal_summary, str):
            goal_summary = original_goal[:200]  # Use first 200 chars of original
        result["goal_summary"] = goal_summary.strip()
        
        return result
    
    def _extract_topics_from_text(self, text: str) -> List[str]:
        """
        Extract potential topics from text using simple heuristics.
        
        Args:
            text: Text to extract topics from
            
        Returns:
            List of topic strings
        """
        # Common study-related keywords
        keywords = ["learn", "study", "master", "understand", "practice", "build", "create"]
        
        # Split into sentences and words
        words = text.lower().split()
        
        # Extract capitalized words and words after keywords
        topics = []
        for i, word in enumerate(words):
            if word in keywords and i + 1 < len(words):
                topics.append(words[i + 1].capitalize())
        
        # If no topics found, create generic ones
        if not topics:
            topics = ["Fundamentals", "Core Concepts", "Practice", "Advanced Topics", "Projects"]
        
        return topics[:10]
    
    def _expand_topics(self, current_topics: List[str], goal: str) -> List[str]:
        """
        Expand topic list to have at least 3 meaningful topics.
        
        Args:
            current_topics: Current list of topics
            goal: Original goal text
            
        Returns:
            Expanded list of topics
        """
        if len(current_topics) >= 3:
            return current_topics
        
        # Add generic topics based on common patterns
        expanded = current_topics.copy()
        generic_topics = [
            "Introduction and Basics",
            "Core Concepts",
            "Intermediate Topics",
            "Advanced Concepts",
            "Practical Projects",
            "Review and Practice"
        ]
        
        for topic in generic_topics:
            if len(expanded) >= 5:
                break
            if topic not in expanded:
                expanded.append(topic)
        
        return expanded
    
    def _create_default_goal(self) -> Dict[str, Any]:
        """Create a default goal for empty input."""
        return {
            "total_days": 30,
            "hours_per_day": 2.0,
            "topics": [
                "Introduction and Setup",
                "Basic Concepts",
                "Core Skills",
                "Intermediate Topics",
                "Advanced Concepts",
                "Practice Projects",
                "Review and Consolidation"
            ],
            "goal_summary": "General study plan - 30 days of focused learning"
        }
    
    def _create_fallback_goal(self, user_goal: str) -> Dict[str, Any]:
        """
        Create a fallback goal when AI parsing fails.
        
        Args:
            user_goal: Original user goal
            
        Returns:
            Fallback goal dictionary
        """
        # Extract numbers from goal text
        numbers = re.findall(r'\d+', user_goal)
        total_days = int(numbers[0]) if numbers else 30
        total_days = min(max(total_days, 1), 365)
        
        # Extract potential topics
        topics = self._extract_topics_from_text(user_goal)
        if len(topics) < 3:
            topics = self._expand_topics(topics, user_goal)
        
        return {
            "total_days": total_days,
            "hours_per_day": 2.0,
            "topics": topics,
            "goal_summary": user_goal[:200] if user_goal else "Study plan"
        }
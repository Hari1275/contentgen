from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import Client, Content
import google.generativeai as genai
from app.core.config import settings

class MemoryService:
    """Service to maintain context and history for client interactions"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        # Initialize Gemini if API key is available
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.model = None
    
    def get_client_history(self, client_id: int, limit: int = 10) -> Dict[str, Any]:
        """Get client's content history and context for AI generation"""
        # Get client information
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return {"error": "Client not found"}
        
        # Get recent content
        recent_content = self.db.query(Content).filter(
            Content.client_id == client_id
        ).order_by(Content.created_at.desc()).limit(limit).all()
        
        # Format content history
        content_history = []
        for content in recent_content:
            content_history.append({
                "id": content.id,
                "title": content.title,
                "type": content.content_type.value,
                "topic": content.topic,
                "created_at": content.created_at.isoformat(),
                "keywords": content.keywords
            })
        
        # Build context object for AI
        context = {
            "client": {
                "id": client.id,
                "name": client.name,
                "industry": client.industry,
                "brand_voice": client.brand_voice,
                "target_audience": client.target_audience,
                "content_preferences": client.content_preferences
            },
            "content_history": content_history,
            "content_patterns": self._analyze_content_patterns(content_history),
            "conversation_threads": self._get_conversation_threads(client_id)
        }
        
        return context
    
    def _analyze_content_patterns(self, content_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in client's content history"""
        if not content_history:
            return {}
        
        # Extract topics and keywords
        topics = [c.get("topic", "") for c in content_history if c.get("topic")]
        all_keywords = []
        for content in content_history:
            if content.get("keywords"):
                keywords = [k.strip() for k in content.get("keywords", "").split(",")]
                all_keywords.extend(keywords)
        
        # Count keyword frequency
        keyword_frequency = {}
        for keyword in all_keywords:
            if keyword:
                keyword_frequency[keyword] = keyword_frequency.get(keyword, 0) + 1
        
        # Sort by frequency
        top_keywords = sorted(keyword_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "recurring_topics": list(set(topics)),
            "top_keywords": [k[0] for k in top_keywords],
            "content_types": list(set(c.get("type") for c in content_history if c.get("type")))
        }
    
    def _get_conversation_threads(self, client_id: int) -> List[Dict[str, Any]]:
        """Get conversation threads for a client"""
        # This would query a dedicated conversations table
        # For now, return a placeholder
        return []
    
    def store_interaction(self, client_id: int, interaction_type: str, data: Dict[str, Any]) -> bool:
        """Store client interaction for future context"""
        # This would store in a dedicated interactions table
        # For now, we'll just return True as a placeholder
        # In a real implementation, you would create and store an Interaction object
        return True
    
    async def generate_content_suggestions(self, client_id: int, suggestion_count: int = 3) -> List[Dict[str, Any]]:
        """Generate AI-powered content suggestions based on client history and profile"""
        if not self.model:
            return [{"error": "Gemini API key not configured. Please set GEMINI_API_KEY in your .env file."}]
        
        # Get client context
        context = self.get_client_history(client_id)
        if "error" in context:
            return [{"error": context["error"]}]
        
        # Create prompt for the AI model
        prompt = f"""
        You are a content strategist for {context['client']['name']}, a company in the {context['client']['industry']} industry.
        
        Generate {suggestion_count} unique and specific content ideas that would resonate with their target audience: {context['client']['target_audience']}.
        
        The content should match their brand voice: {context['client']['brand_voice']}.
        
        Based on their content history, these topics have been covered: {', '.join(context['content_patterns'].get('recurring_topics', [])[:5] or ['None'])}.
        Popular keywords include: {', '.join(context['content_patterns'].get('top_keywords', [])[:5] or ['None'])}.
        
        For each suggestion, provide:
        1. A specific, compelling title (not generic)
        2. Content type (choose from: blog, social, email, video, infographic, case study, whitepaper)
        3. A detailed description (2-3 sentences) explaining the value to the audience
        4. 3-5 relevant keywords
        5. 3-5 trending hashtags that would work well on social media for this content
        
        Format your response as a JSON array with objects containing title, content_type, description, keywords (as an array), and hashtags (as an array).
        """
        
        try:
            # Generate suggestions using Gemini
            response = await self.model.generate_content_async(prompt)
            response_text = response.text
            
            # Try to parse JSON from the response
            try:
                import json
                import re
                
                # Look for JSON-like content in the response
                json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    suggestions = json.loads(json_str)
                else:
                    # If no JSON found, create structured suggestions from the text
                    lines = response_text.split('\n')
                    suggestions = []
                    current_suggestion = {}
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith('Title:') or line.startswith('1.'):
                            if current_suggestion and 'title' in current_suggestion:
                                suggestions.append(current_suggestion)
                                current_suggestion = {}
                            current_suggestion['title'] = line.split(':', 1)[1].strip() if ':' in line else line.split('.', 1)[1].strip()
                        elif line.startswith('Content Type:') or line.startswith('2.'):
                            current_suggestion['content_type'] = line.split(':', 1)[1].strip() if ':' in line else line.split('.', 1)[1].strip()
                        elif line.startswith('Description:') or line.startswith('3.'):
                            current_suggestion['description'] = line.split(':', 1)[1].strip() if ':' in line else line.split('.', 1)[1].strip()
                        elif line.startswith('Keywords:') or line.startswith('4.'):
                            keywords_text = line.split(':', 1)[1].strip() if ':' in line else line.split('.', 1)[1].strip()
                            current_suggestion['keywords'] = [k.strip() for k in keywords_text.split(',')]
                        elif line.startswith('Hashtags:') or line.startswith('5.'):
                            hashtags_text = line.split(':', 1)[1].strip() if ':' in line else line.split('.', 1)[1].strip()
                            # Ensure hashtags start with #
                            current_suggestion['hashtags'] = [
                                h.strip() if h.strip().startswith('#') else f"#{h.strip()}" 
                                for h in hashtags_text.split(',')
                            ]
                    
                    if current_suggestion and 'title' in current_suggestion:
                        suggestions.append(current_suggestion)
                
                # Ensure we have the requested number of suggestions
                if len(suggestions) < suggestion_count:
                    # Fill in with some generated suggestions
                    for i in range(len(suggestions), suggestion_count):
                        suggestions.append({
                            "title": f"The Future of {context['client']['industry']} in {2024 + i}",
                            "content_type": ["blog", "whitepaper", "case study", "infographic"][i % 4],
                            "description": f"An analysis of upcoming trends in {context['client']['industry']} and how businesses can prepare for the changing landscape.",
                            "keywords": ["innovation", "future trends", context['client']['industry'].lower(), "business strategy"],
                            "hashtags": [f"#{context['client']['industry'].lower().replace(' ', '')}", "#innovation", "#futureof" + context['client']['industry'].lower().replace(' ', ''), "#business"]
                        })
                
                # Limit to requested number and ensure all have required fields
                suggestions = suggestions[:suggestion_count]
                for suggestion in suggestions:
                    if 'title' not in suggestion:
                        suggestion['title'] = f"Content Strategy for {context['client']['industry']}"
                    if 'content_type' not in suggestion:
                        suggestion['content_type'] = "blog"
                    if 'description' not in suggestion:
                        suggestion['description'] = f"Strategic content tailored for {context['client']['target_audience']}."
                    if 'keywords' not in suggestion or not suggestion['keywords']:
                        suggestion['keywords'] = context['content_patterns'].get('top_keywords', [])[:3] or ["content", "strategy", context['client']['industry'].lower()]
                    # Ensure keywords is a list
                    if isinstance(suggestion['keywords'], str):
                        suggestion['keywords'] = [k.strip() for k in suggestion['keywords'].split(',')]
                    
                    # Add hashtags if missing
                    if 'hashtags' not in suggestion or not suggestion['hashtags']:
                        industry_tag = context['client']['industry'].lower().replace(' ', '')
                        suggestion['hashtags'] = [
                            f"#{industry_tag}", 
                            f"#{suggestion['content_type'].lower()}", 
                            f"#trending{industry_tag.capitalize()}", 
                            f"#{context['client']['name'].replace(' ', '').lower()}"
                        ]
                    # Ensure hashtags start with #
                    suggestion['hashtags'] = [
                        h if h.startswith('#') else f"#{h}" 
                        for h in suggestion['hashtags']
                    ]
                
                return suggestions
                
            except Exception as parsing_error:
                                # Fallback to generated suggestions with hashtags
                industry_tag = context['client']['industry'].lower().replace(' ', '')
                return [
                    {
                        "title": f"{context['client']['industry']} Trends for {['Q1', 'Q2', 'Q3', 'Q4'][i % 4]} 2024",
                        "content_type": ["blog", "whitepaper", "social", "email", "video"][i % 5],
                        "description": f"A comprehensive analysis of the latest trends in {context['client']['industry']} with actionable insights for {context['client']['target_audience']}.",
                        "keywords": ["trends", context['client']['industry'].lower(), "innovation", "strategy", "insights"],
                        "hashtags": [
                            f"#{industry_tag}", 
                            f"#{industry_tag}Trends", 
                            f"#2024{industry_tag.capitalize()}", 
                            f"#{['innovation', 'strategy', 'business', 'growth', 'success'][i % 5]}"
                        ]
                    }
                    for i in range(suggestion_count)
                ]
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return [{"error": f"Failed to generate suggestions: {str(e)}"}]




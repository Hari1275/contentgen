import google.generativeai as genai
from app.core.config import settings

class AIService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    async def generate_blog_ideas(self, client_info, num_ideas=5):
        prompt = f"""
        Generate {num_ideas} blog post ideas for a client with the following details:
        - Industry: {client_info.industry}
        - Brand voice: {client_info.brand_voice}
        - Target audience: {client_info.target_audience}
        - Content preferences: {client_info.content_preferences}
        
        For each idea, provide:
        1. Title
        2. Brief description (2-3 sentences)
        3. Key points to cover
        4. Target keywords
        """
        
        response = await self.model.generate_content_async(prompt)
        return response.text
    
    async def generate_blog_post(self, client_info, topic=None):
        topic_text = f" about '{topic}'" if topic else ""
        
        prompt = f"""
        Write a comprehensive blog post{topic_text} for a client with the following details:
        - Industry: {client_info.industry}
        - Brand voice: {client_info.brand_voice}
        - Target audience: {client_info.target_audience}
        - Content preferences: {client_info.content_preferences}
        
        The blog post should have:
        - A compelling title
        - An engaging introduction
        - 3-5 main sections with subheadings
        - A conclusion with call-to-action
        - Be around 800-1000 words
        
        Make sure the content is SEO-friendly and incorporates relevant keywords naturally.
        """
        
        response = await self.model.generate_content_async(prompt)
        return response.text

from crewai import Agent, Task, Crew
from app.core.config import settings
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

class ContentCrewService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Use LangChain's wrapper for Gemini to make it compatible with CrewAI
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=settings.GEMINI_API_KEY)
        # Keep the direct Gemini model for other operations
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
    def create_content_crew(self, client_info):
        # Create specialized agents
        researcher = Agent(
            role="Content Researcher",
            goal="Research trending topics and keywords for the client's industry",
            backstory="You are an expert researcher who finds the most relevant and trending topics in any industry.",
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
        
        writer = Agent(
            role="Content Writer",
            goal="Write high-quality, engaging content that matches the client's brand voice",
            backstory="You are a skilled writer who can adapt to any brand voice and create compelling content.",
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
        
        editor = Agent(
            role="Content Editor",
            goal="Ensure content is error-free, SEO-optimized, and matches client requirements",
            backstory="You are a meticulous editor with an eye for detail and SEO best practices.",
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
        
        return researcher, writer, editor
    
    def generate_blog_post(self, client_info, topic=None):
        # Changed from async to regular function since CrewAI's kickoff is not async
        researcher, writer, editor = self.create_content_crew(client_info)
        
        # Define tasks with expected_output field
        research_task = Task(
            description=f"""
            Research trending topics in {client_info.industry} industry.
            Focus on the interests of {client_info.target_audience}.
            If a specific topic '{topic}' is provided, research that topic in depth.
            Identify 5-7 key points that should be covered.
            Find 3-5 relevant keywords with good search volume.
            Your final answer should include the topic, key points, and keywords.
            """,
            expected_output="A research report with topic, key points, and keywords for the blog post.",
            agent=researcher
        )
        
        writing_task = Task(
            description=f"""
            Using the research provided, write a blog post that matches {client_info.brand_voice} brand voice.
            The content should be engaging for {client_info.target_audience}.
            Include all the key points identified in the research.
            Naturally incorporate the keywords throughout the text.
            The blog post should be 800-1000 words with clear sections and subheadings.
            Your final answer should be the complete blog post with a compelling title.
            """,
            expected_output="A complete blog post with title and well-structured content.",
            agent=writer,
            context=[research_task]
        )
        
        editing_task = Task(
            description=f"""
            Review and edit the blog post to ensure it:
            - Is free of grammatical and spelling errors
            - Properly incorporates the keywords for SEO
            - Matches {client_info.brand_voice} brand voice
            - Is engaging for {client_info.target_audience}
            - Has a clear structure with introduction, body, and conclusion
            - Includes a call-to-action
            Your final answer should be the polished, publication-ready blog post.
            """,
            expected_output="A polished, publication-ready blog post with proper structure and SEO optimization.",
            agent=editor,
            context=[writing_task]
        )
        
        # Create the crew
        content_crew = Crew(
            agents=[researcher, writer, editor],
            tasks=[research_task, writing_task, editing_task],
            verbose=True
        )
        
        # Run the crew - this is a blocking operation
        result = content_crew.kickoff()
        return result




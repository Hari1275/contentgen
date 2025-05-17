import google.generativeai as genai
from app.core.config import settings
import time
from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
from bs4 import BeautifulSoup
import json

class ContentCrewService:
    def __init__(self):
        # Initialize the Gemini API
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=settings.GEMINI_API_KEY)
        else:
            print("Warning: GEMINI_API_KEY not set in environment variables")
            self.llm = None
    
    def _create_agents(self, client_info):
        """Create the agents for content generation"""
        if not self.llm:
            raise ValueError("LLM not initialized. Please check your GEMINI_API_KEY.")
        
        # Define tools for the agents
        tools = []
        
        # Website scraping tool
        if hasattr(client_info, 'website_url') and client_info.website_url:
            from crewai import Tool
            
            scrape_tool = Tool(
                name="WebsiteScraper",
                description="Scrapes content from a website URL",
                func=self._scrape_website
            )
            tools.append(scrape_tool)
        
        # Research Agent - Gathers information about the client and industry
        researcher = Agent(
            role="Research Specialist",
            goal="Gather comprehensive information about the client's industry and target audience",
            backstory="You are a thorough researcher who specializes in industry analysis and audience insights. You provide the foundation for creating relevant content.",
            verbose=True,
            llm=self.llm,
            tools=tools  # Add tools parameter
        )
        
        # Content Strategist - Plans content approach based on research
        strategist = Agent(
            role="Content Strategist",
            goal="Develop a strategic content approach that aligns with client's brand voice and business objectives",
            backstory="You are a seasoned content strategist who transforms research into actionable content plans. You understand how to position content for maximum impact.",
            verbose=True,
            llm=self.llm,
            tools=[]  # Empty tools list if no specific tools needed
        )
        
        # Content Writer - Creates the actual content
        writer = Agent(
            role="Content Writer",
            goal="Create engaging, high-quality content that resonates with the target audience",
            backstory="You are a talented writer who crafts compelling content in various formats. You adapt your writing style to match the client's brand voice and content requirements.",
            verbose=True,
            llm=self.llm,
            tools=[]  # Empty tools list if no specific tools needed
        )
        
        # Visual Designer - Provides visual content suggestions
        designer = Agent(
            role="Visual Content Specialist",
            goal="Suggest visual elements that enhance the written content",
            backstory="You are a creative visual specialist who understands how to complement written content with appropriate visual elements. You provide detailed descriptions for designers to implement.",
            verbose=True,
            llm=self.llm,
            tools=[]  # Empty tools list if no specific tools needed
        )
        
        return researcher, strategist, writer, designer
    
    def _scrape_website(self, url):
        """Tool for the Research Agent to scrape website content"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract key information
            title = soup.title.string if soup.title else ""
            
            # Get meta description
            meta_desc = ""
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta and 'content' in meta.attrs:
                meta_desc = meta['content']
            
            # Get main content
            main_content = ""
            for tag in ['main', 'article', 'div.content', 'div.main']:
                content = soup.select(tag)
                if content:
                    main_content = " ".join([c.get_text(strip=True) for c in content])
                    break
            
            if not main_content and soup.body:
                main_content = soup.body.get_text(strip=True)
            
            # Get about section
            about_section = ""
            about = soup.select('.about, #about, [id*=about], [class*=about]')
            if about:
                about_section = about[0].get_text(strip=True)
            
            return json.dumps({
                "title": title,
                "description": meta_desc,
                "main_content": main_content[:5000],
                "about": about_section
            })
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def run_crew_ai(client_info, topic, content_type="blog", word_count=500, tone=None, keywords=None):
        """Run CrewAI in a separate thread"""
        crew_service = ContentCrewService()
        return crew_service.generate_blog_post(client_info, topic, content_type, word_count, tone, keywords)

    def generate_blog_post(self, client_info, topic, content_type="blog", word_count=500, tone=None, keywords=None):
        """Generate content using CrewAI agents"""
        try:
            print(f"Starting content generation for topic: {topic}")
            
            # Check if LLM is initialized
            if not self.llm:
                return "Error: Gemini API key not configured. Please set GEMINI_API_KEY in your .env file."
            
            # Create agents with more specific roles
            researcher = Agent(
                role="Research Specialist",
                goal="Gather comprehensive information about the client, industry, and topic",
                backstory="You are an expert researcher with years of experience in gathering relevant information for content creation.",
                tools=[], # Initialize with empty tools
                llm=self.llm,
                verbose=True
            )
            
            # Add website scraping tool if URL is available
            if hasattr(client_info, 'website_url') and client_info.website_url:
                from langchain.tools import Tool
                
                scrape_tool = Tool(
                    name="WebsiteScraper",
                    description="Scrapes content from a website URL",
                    func=self._scrape_website
                )
                researcher.tools = [scrape_tool]
            
            strategist = Agent(
                role="Content Strategist",
                goal="Develop effective content strategies that align with client goals",
                backstory="You are a seasoned content strategist who excels at creating content plans that resonate with target audiences.",
                llm=self.llm,
                verbose=True
            )
            
            writer = Agent(
                role="Content Writer",
                goal="Create engaging, high-quality content that meets the client's requirements",
                backstory="You are a professional writer with expertise in creating compelling content across various formats and industries.",
                llm=self.llm,
                verbose=True
            )
            
            designer = Agent(
                role="Visual Designer",
                goal="Recommend visual elements that enhance the written content",
                backstory="You are a creative designer who specializes in visualizing content to maximize engagement and understanding.",
                llm=self.llm,
                verbose=True
            )
            
            # Define research task
            research_task = Task(
                description=f"""
                Research the client's business and industry thoroughly.
                
                Client Information:
                - Name: {client_info.name}
                - Industry: {client_info.industry}
                - Target Audience: {client_info.target_audience}
                - Brand Voice: {client_info.brand_voice}
                
                If a website URL is provided, scrape it for information: {getattr(client_info, 'website_url', 'N/A')}
                
                Research current trends in {client_info.industry} related to: {topic}
                
                Compile your findings in a detailed research report.
                """,
                agent=researcher,
                expected_output="Detailed research report on client business and industry trends"
            )
            
            # Add tone and keywords to the strategy task
            tone_guidance = f"The content should use a {tone} tone." if tone else ""
            keyword_guidance = f"Incorporate these keywords naturally: {keywords}" if keywords else ""
            
            strategy_task = Task(
                description=f"""
                Based on the research report, develop a content strategy for a {content_type} about {topic}.
                
                Consider:
                - How to align with the client's brand voice: {client_info.brand_voice}
                - How to appeal to the target audience: {client_info.target_audience}
                - Key messages to include
                - SEO considerations and keywords
                
                {tone_guidance}
                {keyword_guidance}
                
                The content should be approximately {word_count} words.
                
                Create a content brief with outline, key points, and tone guidance.
                """,
                agent=strategist,
                expected_output="Content brief with outline and strategic direction",
                context=[research_task]
            )
            
            # Define writing task with explicit instructions for formatting
            writing_task = Task(
                description=f"""
                Create a {word_count}-word {content_type} based on the content brief.
                
                The content should be about: {topic}
                
                IMPORTANT FORMATTING INSTRUCTIONS:
                1. Start with a clear, engaging title on the first line
                2. Then add a blank line
                3. Then write the main content with proper paragraphs and sections
                4. Do NOT include any visual suggestions
                5. Do NOT use markdown code blocks or JSON formatting
                6. Output plain text only
                
                For blog format:
                - Title on first line
                - Blank line
                - Introduction paragraph
                - 2-3 main sections with subheadings
                - Conclusion paragraph
                
                Example format:
                Tired of Allergies? Natural Solutions That Work
                
                Allergies affect millions of people worldwide, causing discomfort and disrupting daily life. This article explores...
                
                ## Understanding Allergies
                Allergies occur when your immune system...
                
                ## Natural Remedies
                Several natural approaches can help...
                
                ## Conclusion
                Finding relief from allergies is possible...
                """,
                agent=writer,
                expected_output="Complete content piece with title and body",
                context=[strategy_task]
            )
            
            # Define design task
            design_task = Task(
                description=f"""
                Based on the content created, suggest visual elements that would enhance it.
                
                For the {content_type} about {topic}, provide:
                - Description of 2-3 recommended images/graphics
                - Suggested color scheme (considering client's brand)
                - Layout recommendations
                - Any infographic elements that would enhance understanding
                
                Be specific in your descriptions so designers can create these visuals.
                
                IMPORTANT: Start your response with "VISUAL SUGGESTIONS:" to clearly separate it from the content.
                """,
                agent=designer,
                expected_output="Visual content recommendations",
                context=[writing_task]
            )
            
            # Create and run the crew with sequential process to ensure proper order
            crew = Crew(
                agents=[researcher, strategist, writer, designer],
                tasks=[research_task, strategy_task, writing_task, design_task],
                verbose=2,
                process=Process.sequential
            )
            
            print("Starting crew kickoff")
            result = crew.kickoff()
            print("Crew kickoff completed")
            print(f"Raw result preview: {result[:200]}...")
            
            # Check if we only got visual suggestions without content
            if result.startswith("VISUAL SUGGESTIONS:"):
                print("ERROR: Only received visual suggestions without main content")
                # Generate main content separately
                main_content = self._generate_fallback_content(client_info, topic, content_type, word_count, tone, keywords)
                result = main_content + "\n\n" + result
                print(f"Added fallback content. New result preview: {result[:200]}...")
            
            # Ensure the result has both content and visual suggestions
            if "VISUAL SUGGESTIONS:" not in result:
                # If no visual suggestions section, add a placeholder
                result += "\n\nVISUAL SUGGESTIONS:\nNo specific visual suggestions provided."
            
            return result
        
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in CrewAI content generation: {error_details}")
            return f"Error generating content: {str(e)}"

    def _generate_fallback_content(self, client_info, topic, content_type="blog", word_count=500, tone=None, keywords=None):
        """Generate fallback content when CrewAI fails to produce main content"""
        print("Generating fallback content...")
        
        try:
            # Create a prompt for direct content generation
            tone_text = f" in a {tone} tone" if tone else ""
            keywords_text = f" incorporating these keywords: {keywords}" if keywords else ""
            
            prompt = f"""
            Write a {word_count}-word {content_type} about "{topic}" for {client_info.name}, a company in the {client_info.industry} industry.
            
            The content should match their brand voice: {client_info.brand_voice}
            It should appeal to their target audience: {client_info.target_audience}
            Write it{tone_text}{keywords_text}.
            
            Format the content as follows:
            - Start with an engaging title on the first line
            - Add a blank line after the title
            - Write an introduction that hooks the reader
            - Include 2-3 main sections with subheadings
            - End with a conclusion and call to action
            
            Do not include any visual suggestions or formatting instructions in your response.
            """
            
            # Use the LLM directly to generate content
            from langchain.schema import HumanMessage
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            print(f"Fallback content generated. Preview: {content[:200]}...")
            return content
        
        except Exception as e:
            print(f"Error generating fallback content: {str(e)}")
            # Return a very basic content as last resort
            return f"""
            {topic}
            
            {client_info.name} offers effective solutions for those suffering from allergies. Our Nishamritha Tablets provide natural relief based on Ayurvedic principles.
            
            ## Benefits of Nishamritha Tablets
            These tablets are formulated with natural ingredients that help reduce allergy symptoms without side effects.
            
            ## How It Works
            The unique combination of herbs works to balance your body's immune response to allergens.
            
            ## Conclusion
            Try Nishamritha Tablets today for lasting relief from your allergy symptoms.
            """















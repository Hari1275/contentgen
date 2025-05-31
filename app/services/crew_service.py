import google.generativeai as genai
from app.core.config import settings
import time
from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
from bs4 import BeautifulSoup
import json
# Add import for crewai_tools (with fallback if not installed)
try:
    from crewai_tools import ScrapeWebsiteTool
    CREWAI_TOOLS_AVAILABLE = True
except ImportError:
    CREWAI_TOOLS_AVAILABLE = False
    print("Warning: crewai_tools not installed. Some functionality may be limited.")

class ContentCrewService:
    def __init__(self):
        # Initialize the Gemini API
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=settings.GEMINI_API_KEY)
                # Test the API key with a simple query
                response = self.model.generate_content("Hello")
                print("Gemini API initialized successfully")
            except Exception as e:
                print(f"Error initializing Gemini API: {str(e)}")
                self.model = None
                self.llm = None
        else:
            print("Warning: GEMINI_API_KEY not set in environment variables")
            self.model = None
            self.llm = None
    
    def _create_agents(self, client_info):
        """Create the agents for content generation"""
        if not self.llm:
            raise ValueError("LLM not initialized. Please check your GEMINI_API_KEY.")
        
        # Define tools for the agents
        tools = []
        
        # Website scraping tool
        if hasattr(client_info, 'website_url') and client_info.website_url:
            try:
                from crewai_tools import ScrapeWebsiteTool
                
                # Initialize the tool with the website URL
                scrape_tool = ScrapeWebsiteTool(website_url=client_info.website_url)
                tools.append(scrape_tool)
                print(f"Added ScrapeWebsiteTool for URL: {client_info.website_url}")
            except ImportError:
                print("Warning: crewai_tools not installed. Falling back to langchain Tool.")
                from langchain.tools import Tool
                
                scrape_tool = Tool(
                    name="WebsiteScraper",
                    description="Scrapes content from a website URL",
                    func=self._scrape_website
                )
                tools.append(scrape_tool)
                print(f"Added langchain Tool for URL: {client_info.website_url}")
        
        # Research Agent - Gathers information about the client and industry
        researcher = Agent(
            role="Research Specialist",
            goal="Gather comprehensive information about the client's industry, target audience, and topic to inform content creation",
            backstory="""You are an expert researcher with years of experience in digital marketing research. 
            You excel at finding relevant industry trends, competitor insights, and audience preferences.
            You're known for your ability to extract valuable insights from websites and identify what makes content perform well in specific industries.""",
            verbose=True,
            llm=self.llm,
            tools=tools,
            allow_delegation=True,
            max_iterations=3  # Allow multiple research iterations if needed
        )
        
        # Content Strategist - Plans content approach based on research
        strategist = Agent(
            role="Content Strategist",
            goal="Develop a strategic content approach that aligns with client's brand voice and business objectives",
            backstory="""You are a seasoned content strategist who transforms research into actionable content plans.
            You understand how to position content for maximum impact and engagement.
            You excel at identifying the key messages that will resonate with specific target audiences and determining the optimal content structure.""",
            verbose=True,
            llm=self.llm,
            tools=[],
            allow_delegation=False,  # Strategist doesn't need to delegate
            max_iterations=2  # Allow refinement of strategy
        )
        
        # Content Writer - Creates the actual content
        writer = Agent(
            role="Content Writer",
            goal="Create engaging, high-quality content that resonates with the target audience and drives desired actions",
            backstory="""You are a professional content writer with expertise in creating compelling marketing content across various industries.
            You know how to adapt your writing style to match different brand voices and how to structure content for maximum engagement.
            You're skilled at incorporating SEO keywords naturally while maintaining readability and persuasiveness.""",
            verbose=True,
            llm=self.llm,
            tools=[],
            allow_delegation=True,  # Can delegate to researcher if needed
            max_iterations=2  # Allow content refinement
        )
        
        # Visual Designer - Provides visual content suggestions
        designer = Agent(
            role="Visual Content Specialist",
            goal="Suggest visual elements that enhance the written content and reinforce key messages",
            backstory="""You are a creative visual specialist who understands how to complement written content with appropriate visual elements.
            You provide detailed descriptions for designers to implement, focusing on images, graphics, and layout that will enhance the message.
            You have a strong sense of brand consistency and know how to use visuals to increase engagement and comprehension.""",
            verbose=True,
            llm=self.llm,
            tools=[],
            allow_delegation=False,  # Designer doesn't need to delegate
            max_iterations=1  # Visual suggestions usually only need one iteration
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

    def _scrape_website(self, url):
        """Fallback method for website scraping when crewai_tools is not available"""
        try:
            print(f"Scraping website: {url}")
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract text from paragraphs, headings, and list items
            text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
            extracted_text = "\n\n".join([elem.get_text().strip() for elem in text_elements if elem.get_text().strip()])
            
            # Extract meta description if available
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and 'content' in meta_desc.attrs:
                extracted_text = f"META DESCRIPTION: {meta_desc['content']}\n\n{extracted_text}"
            
            # Extract title if available
            title = soup.find('title')
            if title:
                extracted_text = f"TITLE: {title.get_text()}\n\n{extracted_text}"
            
            print(f"Successfully scraped {len(extracted_text)} characters from {url}")
            return extracted_text
        except Exception as e:
            print(f"Error scraping website {url}: {str(e)}")
            return f"Error scraping website: {str(e)}"

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
            
            # Create agents with enhanced capabilities
            researcher, strategist, writer, designer = self._create_agents(client_info)
            
            # Define research task with more specific instructions
            research_task = Task(
                description=f"""
                Research the client's business, industry, and topic thoroughly to inform content creation.
                
                Client Information:
                - Name: {client_info.name}
                - Industry: {client_info.industry}
                - Target Audience: {client_info.target_audience}
                - Brand Voice: {client_info.brand_voice}
                
                If a website URL is provided, scrape it for information: {getattr(client_info, 'website_url', 'N/A')}
                
                Your research should include:
                1. Current trends in {client_info.industry} related to: {topic}
                2. Common pain points for the target audience regarding this topic
                3. Competitor approaches to this topic (if available)
                4. Key statistics or data points that would make the content more credible
                5. Potential keywords for SEO optimization
                
                Compile your findings in a detailed research report that will guide content creation.
                """,
                agent=researcher,
                expected_output="Detailed research report on client business, industry trends, and topic insights",
                async_execution=False,  # Ensure this completes before moving to strategy
                output_file="research_report.txt"  # Save research output for reference
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
                context=[research_task],
                async_execution=False,
                output_file="content_brief.txt"
            )
            
            # Define writing task with explicit instructions for formatting
            writing_task = Task(
                description=f"""
                Create a {word_count}-word {content_type} based on the research and content brief.
                
                The content should be about: {topic}
                
                IMPORTANT CONTENT REQUIREMENTS:
                1. Write in the client's brand voice: {client_info.brand_voice}
                2. Target the specific audience: {client_info.target_audience}
                3. Include a clear value proposition early in the content
                4. Use a compelling call-to-action at the end
                5. Naturally incorporate these keywords: {keywords or "relevant industry terms"}
                6. Use a {tone or "professional"} tone throughout
                
                IMPORTANT FORMATTING INSTRUCTIONS:
                1. Start with a clear, engaging title on the first line
                2. Then add a blank line
                3. Then write the main content with proper paragraphs and sections
                4. Use subheadings (##) to break up the content
                5. Keep paragraphs short (3-4 sentences maximum)
                6. Do NOT include any visual suggestions
                7. Output plain text only
                
                Example format:
                Tired of Allergies? Natural Solutions That Work
                
                Allergies affect millions of people worldwide, causing discomfort and disrupting daily life. This article explores natural solutions that can provide lasting relief.
                
                ## Understanding Allergies
                Allergies occur when your immune system...
                """,
                agent=writer,
                expected_output="Complete content piece with title and body",
                context=[strategy_task],
                async_execution=False,
                output_file="content.txt"
            )
            
            # Define design task - make it clear this should be separate from content
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
                Your entire response should be ONLY visual suggestions, not content.
                """,
                agent=designer,
                expected_output="Visual content recommendations",
                context=[writing_task],
                async_execution=False,
                output_file="visual_suggestions.txt"
            )
            
            # Create and run the crew with sequential process to ensure proper order
            crew = Crew(
                agents=[researcher, strategist, writer, designer],
                tasks=[research_task, strategy_task, writing_task, design_task],
                verbose=2,
                process=Process.sequential,
                manager_llm=self.llm  # Use the same LLM for the manager
            )
            
            print("Starting crew kickoff")
            result = crew.kickoff()
            print("Crew kickoff completed")
            print(f"Raw result preview: {result[:200]}...")
            
            # Check if we only got visual suggestions without content
            if result.startswith("VISUAL SUGGESTIONS:"):
                print("ERROR: Only received visual suggestions without main content")
                # Try to read content from output file
                try:
                    with open("content.txt", "r") as f:
                        main_content = f.read()
                    result = main_content + "\n\n" + result
                    print(f"Added content from file. New result preview: {result[:200]}...")
                except:
                    # Generate main content separately as fallback
                    main_content = self._generate_fallback_content(client_info, topic, content_type, word_count, tone, keywords)
                    result = main_content + "\n\n" + result
                    print(f"Added fallback content. New result preview: {result[:200]}...")
            
            # Ensure the result has both content and visual suggestions
            if "VISUAL SUGGESTIONS:" not in result:
                # Try to read visual suggestions from output file
                try:
                    with open("visual_suggestions.txt", "r") as f:
                        visual_content = f.read()
                    if not visual_content.startswith("VISUAL SUGGESTIONS:"):
                        visual_content = "VISUAL SUGGESTIONS:\n" + visual_content
                    result += "\n\n" + visual_content
                except:
                    # If no visual suggestions section, add a placeholder
                    result += "\n\nVISUAL SUGGESTIONS:\nNo specific visual suggestions provided."
            
            return result
        
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in CrewAI content generation: {error_details}")
            return f"Error generating content: {str(e)}"

    def _generate_fallback_content(self, client_info, topic, content_type="blog", word_count=500, tone=None, keywords=None):
        """Generate fallback content when the crew approach fails"""
        print(f"Generating fallback content for topic: {topic}")
        
        # Prepare keywords string
        keywords_str = ", ".join(keywords) if keywords and isinstance(keywords, list) else keywords or ""
        
        # Create a direct prompt for content generation
        prompt = f"""
        Create a {word_count}-word {content_type} about "{topic}" for a client in the {client_info.industry} industry.
        
        Client details:
        - Brand voice: {client_info.brand_voice}
        - Target audience: {client_info.target_audience}
        
        Content requirements:
        - Use a {tone or "professional"} tone
        - Naturally incorporate these keywords: {keywords_str}
        - Include a clear introduction, 2-3 main sections with subheadings, and a conclusion
        - Add a compelling call-to-action at the end
        
        Format the content as follows:
        1. Start with a clear, engaging title
        2. Add a blank line after the title
        3. Write the main content with proper paragraphs and sections
        4. Use subheadings (##) to break up the content
        
        Do NOT include any visual suggestions or formatting instructions in the output.
        """
        
        try:
            # Generate content directly using the model
            response = self.model.generate_content(prompt)
            content = response.text
            print(f"Fallback content generated. Preview: {content[:200]}...")
            return content
        except Exception as e:
            print(f"Error generating fallback content: {str(e)}")
            # Return a very basic fallback as last resort
            return f"""
            {topic}
            
            Are you tired of allergies disrupting your daily life? Nishamritha Tablets offer a natural, Ayurvedic solution to provide lasting relief from allergy symptoms.
            
            ## Understanding Allergies
            Allergies occur when your immune system reacts to foreign substances that are typically harmless. These reactions can cause sneezing, itching, and other uncomfortable symptoms that affect your quality of life.
            
            ## The Ayurvedic Approach
            Ayurveda, India's ancient system of medicine, takes a holistic approach to treating allergies by addressing the root cause rather than just the symptoms.
            
            ## Nishamritha Tablets: A Natural Solution
            Nishamritha Tablets combine powerful herbs and natural ingredients that have been used for centuries in Ayurvedic medicine to treat allergic conditions.
            
            ## Conclusion
            Don't let allergies control your life. Try Nishamritha Tablets and experience the natural relief that comes from this time-tested Ayurvedic formula.
            """


    def _get_content_format_instructions(self, content_type):
        """Get formatting instructions based on content type"""
        if content_type.lower() == "blog":
            return """
            Format the content as follows:
            1. Start with a clear, engaging title
            2. Add a blank line after the title
            3. Write an introduction that hooks the reader
            4. Use 2-4 main sections with subheadings (##)
            5. Include a conclusion with a call-to-action
            6. Keep paragraphs short (3-4 sentences maximum)
            """
        elif content_type.lower() in ["social", "social_media"]:
            return """
            Format the content as follows:
            1. Start with an attention-grabbing headline
            2. Add a blank line after the headline
            3. Write 2-3 short paragraphs (1-2 sentences each)
            4. Include 3-5 relevant hashtags at the end
            5. Add a clear call-to-action
            """
        elif content_type.lower() in ["email", "newsletter"]:
            return """
            Format the content as follows:
            1. Start with a compelling subject line
            2. Add a blank line after the subject line
            3. Begin with a personalized greeting
            4. Write 3-4 short paragraphs
            5. Use bullet points for key information
            6. End with a strong call-to-action
            7. Include a professional sign-off
            """
        else:
            # Default format for other content types
            return """
            Format the content as follows:
            1. Start with a clear, engaging title
            2. Add a blank line after the title
            3. Write the main content with proper paragraphs
            4. Use subheadings where appropriate
            5. End with a conclusion or summary
            """

    def _extract_content_parts(self, result):
        """Extract title, main content, and visual suggestions from the result"""
        # Initialize variables
        title = ""
        main_content = ""
        visual_suggestions = ""
        
        # Check if result contains visual suggestions
        if "VISUAL SUGGESTIONS:" in result:
            # Split content and visual suggestions
            parts = result.split("VISUAL SUGGESTIONS:", 1)
            main_content = parts[0].strip()
            visual_suggestions = "VISUAL SUGGESTIONS:" + parts[1].strip()
        else:
            main_content = result.strip()
        
        # Extract title from main content
        if main_content:
            lines = main_content.split('\n', 2)
            if len(lines) >= 1:
                title = lines[0].strip()
                # Remove markdown heading markers if present
                title = title.lstrip('#').strip()
                
                # If there are more lines, the rest is the body
                if len(lines) >= 3:
                    main_content = lines[2].strip()  # Skip the title and the blank line
                elif len(lines) == 2:
                    main_content = ""  # Only title and blank line
        
        return title, main_content, visual_suggestions

    def generate_social_media_post(self, client_info, topic, platform="instagram", word_count=100, tone=None, keywords=None):
        """Generate social media content for specific platforms"""
        try:
            print(f"Starting social media content generation for {platform} on topic: {topic}")
            
            # Check if LLM is initialized
            if not self.llm:
                return "Error: Gemini API key not configured. Please set GEMINI_API_KEY in your .env file."
            
            # Create agents
            researcher, strategist, writer, designer = self._create_agents(client_info)
            
            # Platform-specific guidance
            platform_guidance = {
                "instagram": "Create engaging, visual-first content with 1-2 paragraphs and 5-10 relevant hashtags.",
                "twitter": "Create concise content under 280 characters with 1-3 relevant hashtags.",
                "linkedin": "Create professional content with 2-3 paragraphs focusing on industry insights and value.",
                "facebook": "Create conversational content with 2-3 paragraphs that encourages engagement."
            }.get(platform.lower(), "Create platform-appropriate social media content.")
            
            # Define research task
            research_task = Task(
                description=f"""
                Research the client's business, industry, and topic for a {platform} post.
                
                Client Information:
                - Name: {client_info.name}
                - Industry: {client_info.industry}
                - Target Audience: {client_info.target_audience}
                - Brand Voice: {client_info.brand_voice}
                
                If a website URL is provided, scrape it for information: {getattr(client_info, 'website_url', 'N/A')}
                
                Research current trends on {platform} related to: {topic}
                Identify popular hashtags and engagement patterns for this topic on {platform}.
                
                Compile your findings in a brief research report.
                """,
                agent=researcher,
                expected_output="Research report for social media content",
                output_file="social_research.txt"
            )
            
            # Define writing task
            writing_task = Task(
                description=f"""
                Create a {platform} post about {topic} based on the research.
                
                {platform_guidance}
                
                IMPORTANT REQUIREMENTS:
                1. Write in the client's brand voice: {client_info.brand_voice}
                2. Target the specific audience: {client_info.target_audience}
                3. Use a {tone or "engaging"} tone
                4. Include relevant hashtags appropriate for {platform}
                5. Keep the content to approximately {word_count} words
                6. Include a clear call-to-action
                
                Format the content appropriately for {platform}.
                Do NOT include any visual suggestions in the main content.
                """,
                agent=writer,
                expected_output=f"Complete {platform} post",
                context=[research_task],
                output_file="social_content.txt"
            )
            
            # Define design task
            design_task = Task(
                description=f"""
                Based on the {platform} post created, suggest visual elements that would enhance it.
                
                For this {platform} post about {topic}, provide:
                - Description of 1-2 recommended images/graphics specific to {platform}
                - Color and style recommendations
                - Any text overlay suggestions
                - Layout recommendations specific to {platform}
                
                Be specific in your descriptions so designers can create these visuals.
                
                IMPORTANT: Start your response with "VISUAL SUGGESTIONS:" to clearly separate it from the content.
                """,
                agent=designer,
                expected_output="Visual recommendations for social media post",
                context=[writing_task],
                output_file="social_visuals.txt"
            )
            
            # Create and run the crew
            crew = Crew(
                agents=[researcher, writer, designer],
                tasks=[research_task, writing_task, design_task],
                verbose=2,
                process=Process.sequential
            )
            
            print(f"Starting crew kickoff for {platform} content")
            result = crew.kickoff()
            
            # Process and return the result
            title, main_content, visual_suggestions = self._extract_content_parts(result)
            
            # For social media, we might not have a formal title
            if not title and main_content:
                # Use the first line as the title
                lines = main_content.split('\n', 1)
                title = lines[0].strip()
                if len(lines) > 1:
                    main_content = lines[1].strip()
            
            # Combine the parts
            final_content = title
            if main_content:
                final_content += "\n\n" + main_content
            if visual_suggestions:
                final_content += "\n\n" + visual_suggestions
            
            return final_content
        
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in social media content generation: {error_details}")
            return f"Error generating social media content: {str(e)}"



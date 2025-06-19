import google.generativeai as genai
from app.core.config import settings
import time
import random
from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
from bs4 import BeautifulSoup
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ServiceUnavailable, ResourceExhausted
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
        has_website = False

        # Website scraping tool - conditionally add based on client website URL
        if hasattr(client_info, 'website_url') and client_info.website_url and client_info.website_url.strip():
            has_website = True
            try:
                from crewai_tools import ScrapeWebsiteTool

                # Initialize the tool with the website URL
                scrape_tool = ScrapeWebsiteTool(website_url=client_info.website_url)
                tools.append(scrape_tool)
                print(f"✅ Website scraping ENABLED - Added ScrapeWebsiteTool for URL: {client_info.website_url}")
                print("🔍 Content generation will include ingredient/menu information from client website")
            except ImportError:
                print("Warning: crewai_tools not installed. Falling back to langchain Tool.")
                from langchain.tools import Tool

                scrape_tool = Tool(
                    name="WebsiteScraper",
                    description="Scrapes content from a website URL to find ingredient and menu information",
                    func=self._scrape_website
                )
                tools.append(scrape_tool)
                print(f"✅ Website scraping ENABLED - Added langchain Tool for URL: {client_info.website_url}")
                print("🔍 Content generation will include ingredient/menu information from client website")
        else:
            print("❌ Website scraping DISABLED - No website URL provided")
            print("📝 Content generation will proceed with general ingredient knowledge only")

        # Store website availability for use in task descriptions
        self.has_website_data = has_website
        self.website_url = client_info.website_url if has_website else None

        # Research Agent - Gathers information about the client and industry
        researcher = Agent(
            role="Customer-Focused Research Specialist",
            goal="Gather information about the client's industry, target audience, and topic with special focus on natural ingredients, simple language, and customer engagement strategies",
            backstory="""You are an expert researcher who specializes in natural products, health, and wellness industries.
            You excel at finding ingredient information, health benefits, and customer pain points.
            You understand what makes content relatable to everyday customers - using simple words, focusing on real benefits,
            and highlighting natural ingredients that people can understand and trust. You're known for finding content
            approaches that make customers feel confident and engaged.""",
            verbose=True,
            llm=self.llm,
            tools=tools,
            allow_delegation=True,
            max_iterations=3  # Allow multiple research iterations if needed
        )

        # Content Strategist - Plans content approach based on research
        strategist = Agent(
            role="Customer Engagement Content Strategist",
            goal="Develop content strategies that use simple, engaging language and highlight natural ingredients to build customer trust and drive action",
            backstory="""You are a content strategist who specializes in making complex health and wellness topics easy to understand.
            You excel at creating content strategies that use everyday language, focus on real customer benefits, and highlight
            natural ingredients in ways that build trust. You understand that customers want simple, honest information about
            products that can help them feel better. You're known for creating content plans that make customers feel confident
            and excited about natural solutions.""",
            verbose=True,
            llm=self.llm,
            tools=[],
            allow_delegation=False,  # Strategist doesn't need to delegate
            max_iterations=2  # Allow refinement of strategy
        )

        # Content Writer - Creates the actual content
        writer = Agent(
            role="Simple Language Content Writer",
            goal="Create engaging, easy-to-read content using simple English words and natural ingredient names that customers can easily understand and trust",
            backstory="""You are a content writer who specializes in health and wellness topics for everyday customers.
            You excel at taking complex information and making it simple and relatable. You use everyday words instead of
            technical jargon, mention specific natural ingredients by name (like turmeric, ginger, honey), and focus on
            real benefits that customers care about. You write like you're talking to a friend - warm, helpful, and honest.
            Your content makes customers feel confident about trying natural products because you explain things clearly.""",
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, ResourceExhausted)),
        reraise=True
    )
    def generate_blog_post(self, client_info, topic, content_type="blog", word_count=500, tone=None, keywords=None):
        """Generate content using CrewAI agents"""
        try:
            print(f"Starting content generation for topic: {topic}")

            # Check if LLM is initialized
            if not self.llm:
                return "Error: Gemini API key not configured. Please set GEMINI_API_KEY in your .env file."

            # Create agents with enhanced capabilities
            researcher, strategist, writer, designer = self._create_agents(client_info)

            # Define research task with conditional website scraping instructions
            website_instruction = ""
            if self.has_website_data:
                website_instruction = f"""
                WEBSITE SCRAPING AVAILABLE: Use the website scraping tool to gather specific ingredient and menu information from: {self.website_url}
                - Look for ingredient lists, menu items, product descriptions
                - Extract specific natural ingredients mentioned on the website
                - Find any health benefits or product claims mentioned
                - Note the language style used on the website for consistency
                """
            else:
                website_instruction = """
                NO WEBSITE DATA AVAILABLE: Use your general knowledge of natural ingredients and industry best practices.
                - Focus on commonly known natural ingredients (turmeric, ginger, honey, green tea, etc.)
                - Use general health and wellness knowledge for this industry
                - Apply standard natural product benefits and language
                """

            research_task = Task(
                description=f"""
                Research the client's business, industry, and topic thoroughly to inform content creation with focus on customer engagement.

                Client Information:
                - Name: {client_info.name}
                - Industry: {client_info.industry}
                - Target Audience: {client_info.target_audience}
                - Brand Voice: {client_info.brand_voice}

                {website_instruction}

                Your research should include:
                1. Current trends in {client_info.industry} related to: {topic}
                2. Common pain points for the target audience regarding this topic
                3. Natural ingredients and their simple, everyday names that relate to this topic
                4. Customer-friendly benefits and simple explanations
                5. Words and phrases that customers actually use (avoid technical jargon)
                6. Competitor approaches that use simple, engaging language
                7. Potential keywords that are easy to understand

                IMPORTANT: Do NOT use emojis or special Unicode characters in your output. Use plain text only.
                FOCUS ON: Simple language, natural ingredient names, customer benefits, and engagement strategies.
                Compile your findings in a detailed research report that will guide content creation.
                """,
                agent=researcher,
                expected_output="Detailed research report focusing on customer engagement, simple language, and natural ingredients",
                async_execution=False  # Ensure this completes before moving to strategy
            )

            # Add tone and keywords to the strategy task
            tone_guidance = f"The content should use a {tone} tone." if tone else ""
            keyword_guidance = f"Incorporate these keywords naturally: {keywords}" if keywords else ""

            strategy_task = Task(
                description=f"""
                Based on the research report, develop a content strategy for a {content_type} about {topic} that focuses on customer engagement.

                Consider:
                - How to align with the client's brand voice: {client_info.brand_voice}
                - How to appeal to the target audience: {client_info.target_audience}
                - Key messages using simple, everyday language
                - Natural ingredients to highlight by name (like turmeric, ginger, honey, etc.)
                - Customer benefits in plain English
                - SEO considerations using easy-to-understand keywords

                {tone_guidance}
                {keyword_guidance}

                STRATEGY FOCUS:
                - Use simple words that customers understand
                - Mention specific natural ingredients by name
                - Focus on real benefits customers care about
                - Make content feel friendly and trustworthy
                - Avoid technical jargon or complex terms

                IMPORTANT: Do NOT use emojis or special Unicode characters in your output. Use plain text only.
                The content should be approximately {word_count} words.

                Create a content brief with outline, key points, ingredient mentions, and simple language guidance.
                """,
                agent=strategist,
                expected_output="Content brief with customer-focused strategy, simple language guidelines, and ingredient recommendations",
                context=[research_task],
                async_execution=False
            )

            # Define writing task with explicit instructions for formatting
            writing_task = Task(
                description=f"""
                Create a {word_count}-word {content_type} based on the research and content brief using simple, engaging language.

                The content should be about: {topic}

                IMPORTANT CONTENT REQUIREMENTS:
                1. Write in the client's brand voice: {client_info.brand_voice}
                2. Target the specific audience: {client_info.target_audience}
                3. Use SIMPLE, EVERYDAY WORDS that customers easily understand
                4. Mention SPECIFIC NATURAL INGREDIENTS by name (like turmeric, ginger, honey, aloe vera, etc.)
                5. Focus on REAL BENEFITS customers care about (feel better, sleep better, more energy, etc.)
                6. Write like you're talking to a friend - warm, helpful, and honest
                7. Include a clear value proposition early in the content
                8. Use a compelling call-to-action at the end
                9. Naturally incorporate these keywords: {keywords or "relevant natural terms"}
                10. Use a {tone or "friendly and helpful"} tone throughout

                LANGUAGE GUIDELINES:
                - Use "help" instead of "facilitate"
                - Use "natural" instead of "organic compounds"
                - Use "feel better" instead of "therapeutic benefits"
                - Use "works well" instead of "demonstrates efficacy"
                - Mention ingredients like: turmeric, ginger, honey, green tea, etc.
                - Focus on how customers will feel: energized, calm, healthy, strong

                IMPORTANT FORMATTING INSTRUCTIONS:
                1. Start with a clear, engaging title on the first line
                2. Then add a blank line
                3. Then write the main content with proper paragraphs and sections
                4. Use subheadings (##) to break up the content
                5. Keep paragraphs short (3-4 sentences maximum)
                6. Do NOT include any visual suggestions
                7. Output plain text only
                8. CRITICAL: Do NOT use emojis or special Unicode characters anywhere in your content

                Example format:
                Feel Better Naturally: Simple Solutions That Really Work

                Tired of feeling run down? Natural ingredients like turmeric and ginger can help you feel stronger and more energized every day.

                ## Why Natural Ingredients Work
                Your body knows how to use natural ingredients like honey and green tea...
                """,
                agent=writer,
                expected_output="Complete content piece with simple language, ingredient names, and customer-focused benefits",
                context=[strategy_task],
                async_execution=False
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

                IMPORTANT:
                1. Start your response with "VISUAL SUGGESTIONS:" to clearly separate it from the content.
                2. Your entire response should be ONLY visual suggestions, not content.
                3. Do NOT use emojis or special Unicode characters in your output. Use plain text only.
                """,
                agent=designer,
                expected_output="Visual content recommendations",
                context=[writing_task],
                async_execution=False
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
            try:
                result = crew.kickoff()
                print("Crew kickoff completed")
                print(f"Raw result preview: {result[:200]}...")

                # Clean any emojis or special Unicode characters
                result = self._clean_unicode_content(str(result))
                print("Content cleaned of Unicode characters")

            except (ServiceUnavailable, ResourceExhausted) as e:
                print(f"⚠️ Gemini API overloaded: {str(e)}")
                print("🔄 Falling back to simple content generation...")
                result = self._generate_fallback_content(client_info, topic, content_type, word_count, tone, keywords)
                result += "\n\nVISUAL SUGGESTIONS:\nDue to API limitations, visual suggestions are not available at this time."
                result = self._clean_unicode_content(result)

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

        # Check if website data is available for ingredient sourcing
        ingredient_guidance = ""
        if hasattr(self, 'has_website_data') and self.has_website_data:
            ingredient_guidance = f"""
            INGREDIENT SOURCING: Since the client has a website ({self.website_url}), focus on ingredients that would typically be found in their industry.
            If this is a health/wellness business, emphasize natural ingredients commonly used in such businesses.
            """
        else:
            ingredient_guidance = """
            INGREDIENT SOURCING: Use general knowledge of natural ingredients commonly known and trusted by consumers.
            Focus on widely recognized natural ingredients like turmeric, ginger, honey, green tea, aloe vera, etc.
            """

        # Create a direct prompt for content generation
        prompt = f"""
        Create a {word_count}-word {content_type} about "{topic}" for a client in the {client_info.industry} industry using simple, engaging language.

        Client details:
        - Brand voice: {client_info.brand_voice}
        - Target audience: {client_info.target_audience}

        {ingredient_guidance}

        Content requirements:
        - Use a {tone or "friendly and helpful"} tone
        - Use SIMPLE, EVERYDAY WORDS that customers easily understand
        - Mention SPECIFIC NATURAL INGREDIENTS by name (like turmeric, ginger, honey, aloe vera, etc.)
        - Focus on REAL BENEFITS customers care about (feel better, sleep better, more energy, etc.)
        - Write like you're talking to a friend - warm, helpful, and honest
        - Naturally incorporate these keywords: {keywords_str}
        - Include a clear introduction, 2-3 main sections with subheadings, and a conclusion
        - Add a compelling call-to-action at the end

        Language guidelines:
        - Use "help" instead of "facilitate"
        - Use "natural" instead of "organic compounds"
        - Use "feel better" instead of "therapeutic benefits"
        - Use "works well" instead of "demonstrates efficacy"
        - Mention ingredients like: turmeric, ginger, honey, green tea, etc.
        - Focus on how customers will feel: energized, calm, healthy, strong

        Format the content as follows:
        1. Start with a clear, engaging title
        2. Add a blank line after the title
        3. Write the main content with proper paragraphs and sections
        4. Use subheadings (##) to break up the content

        Do NOT include any visual suggestions or formatting instructions in the output.
        """

        try:
            # Generate content directly using the model with retry logic
            response = self._generate_with_retry(prompt)
            content = response.text
            # Clean any Unicode characters
            content = self._clean_unicode_content(content)
            print(f"Fallback content generated. Preview: {content[:200]}...")
            return content
        except Exception as e:
            print(f"Error generating fallback content: {str(e)}")
            # Return a very basic fallback as last resort
            return f"""
            {topic}

            Tired of sneezing and itchy eyes? Natural ingredients like turmeric and ginger can help you feel better without harsh chemicals.

            ## Why Allergies Make You Feel Bad
            When your body meets things like pollen or dust, it tries to fight them off. This causes sneezing, runny nose, and watery eyes that make you feel miserable.

            ## Natural Ingredients That Help
            For thousands of years, people have used simple natural ingredients to feel better. Turmeric helps calm your body's reaction. Ginger soothes irritation. Honey can ease throat discomfort.

            ## Simple Solutions That Work
            Instead of complicated treatments, try natural ingredients your body recognizes. These gentle helpers work with your body, not against it. Many people feel relief in just a few days.

            ## Start Feeling Better Today
            You don't have to suffer through another allergy season. Try natural solutions with ingredients like turmeric, ginger, and honey. Your body will thank you for choosing gentle, natural relief.
            """

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=5, max=30),
        retry=retry_if_exception_type((ServiceUnavailable, ResourceExhausted)),
        reraise=True
    )
    def _generate_with_retry(self, prompt):
        """Generate content with retry logic for handling API overload"""
        print(f"🔄 Attempting content generation (with retry logic)...")

        # Add random delay to avoid hitting rate limits
        delay = random.uniform(1, 3)
        print(f"⏱️ Adding {delay:.1f}s delay to avoid rate limits...")
        time.sleep(delay)

        try:
            response = self.model.generate_content(prompt)
            print("✅ Content generation successful!")
            return response
        except (ServiceUnavailable, ResourceExhausted) as e:
            print(f"⚠️ API overloaded (503/429): {str(e)}")
            print("🔄 Will retry with exponential backoff...")
            raise  # Re-raise to trigger retry
        except Exception as e:
            print(f"❌ Other error: {str(e)}")
            raise

    def _clean_unicode_content(self, content):
        """Remove emojis and problematic Unicode characters that cause encoding issues"""
        import re

        # Remove emojis and other problematic Unicode characters
        # This regex removes most emojis and special symbols
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"  # enclosed characters
            "]+",
            flags=re.UNICODE
        )

        cleaned_content = emoji_pattern.sub('', content)

        # Also remove any other problematic characters
        cleaned_content = cleaned_content.encode('ascii', 'ignore').decode('ascii')

        print(f"Cleaned content: removed {len(content) - len(cleaned_content)} problematic characters")
        return cleaned_content

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
                "instagram": """Create engaging, visual-first content with 1-2 short paragraphs and 8-15 relevant hashtags.
                IMPORTANT: Always include hashtags at the end of the post. Use a mix of:
                - Popular hashtags (#health #wellness #natural)
                - Niche hashtags (#ayurveda #herbalremedy #naturalhealing)
                - Branded hashtags (related to the client's brand)
                - Location hashtags if relevant
                Format hashtags on separate lines at the end.""",
                "twitter": "Create concise content under 280 characters with 1-3 relevant hashtags.",
                "linkedin": "Create professional content with 2-3 paragraphs focusing on industry insights and value.",
                "facebook": "Create conversational content with 2-3 paragraphs that encourages engagement.",
                "social": "Create engaging social media content with 1-2 paragraphs and 5-8 relevant hashtags."
            }.get(platform.lower(), "Create platform-appropriate social media content.")

            # Define research task with conditional website scraping
            website_instruction = ""
            if self.has_website_data:
                website_instruction = f"""
                WEBSITE SCRAPING AVAILABLE: Use the website scraping tool to gather specific ingredient and menu information from: {self.website_url}
                - Look for ingredient lists, menu items, product descriptions
                - Extract specific natural ingredients mentioned on the website
                - Find any health benefits or product claims mentioned
                - Note the language style used on the website for consistency
                """
            else:
                website_instruction = """
                NO WEBSITE DATA AVAILABLE: Use your general knowledge of natural ingredients and industry best practices.
                - Focus on commonly known natural ingredients (turmeric, ginger, honey, green tea, etc.)
                - Use general health and wellness knowledge for this industry
                - Apply standard natural product benefits and language
                """

            research_task = Task(
                description=f"""
                Research the client's business, industry, and topic for a {platform} post.

                Client Information:
                - Name: {client_info.name}
                - Industry: {client_info.industry}
                - Target Audience: {client_info.target_audience}
                - Brand Voice: {client_info.brand_voice}

                {website_instruction}

                Research current trends on {platform} related to: {topic}
                Identify popular hashtags and engagement patterns for this topic on {platform}.

                Compile your findings in a brief research report.
                """,
                agent=researcher,
                expected_output="Research report for social media content",
                output_file="social_research.txt"
            )

            # Define writing task with enhanced Instagram hashtag requirements
            if platform.lower() == "instagram":
                writing_description = f"""
                Create an Instagram post about {topic} based on the research.

                {platform_guidance}

                SPECIFIC INSTAGRAM REQUIREMENTS:
                1. Write in the client's brand voice: {client_info.brand_voice}
                2. Target the specific audience: {client_info.target_audience}
                3. Use a {tone or "engaging"} tone
                4. Keep the main content to approximately {word_count or 100} words
                5. Include a clear call-to-action
                6. MANDATORY: End with 8-15 relevant hashtags

                HASHTAG REQUIREMENTS:
                - Include popular health/wellness hashtags: #health #wellness #natural #healthylifestyle
                - Include industry-specific hashtags related to {client_info.industry}
                - Include topic-specific hashtags related to {topic}
                - Use a mix of popular and niche hashtags
                - Format hashtags at the end, each on a new line or separated by spaces
                - Example format:

                  #health #wellness #natural #ayurveda #herbalremedy #naturalhealing #healthylife #organic #plantbased #holistichealth

                Do NOT include any visual suggestions in the main content.
                """
            else:
                writing_description = f"""
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
                """

            writing_task = Task(
                description=writing_description,
                agent=writer,
                expected_output=f"Complete {platform} post with hashtags",
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



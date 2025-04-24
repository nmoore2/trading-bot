from openai import OpenAI
from config import OPENAI_API_KEY

class GPTSignalChecker:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
    def analyze_signal(self, formatted_data):
        """Analyze trading signals using GPT-4"""
        try:
            # Send request to GPT
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": """You are a professional crypto trading analyst. 
                    Analyze market data and provide clear, concise trading recommendations.
                    Focus on risk management and objective technical analysis.
                    
                    Your response MUST follow this exact format:
                    
                    ANALYSIS:
                    [2-3 sentences about current market conditions]
                    
                    STRENGTHS:
                    - [bullet points of positive factors]
                    
                    RISKS:
                    - [bullet points of risk factors]
                    
                    RECOMMENDATION:
                    Action: [MUST be one of: BUY, SELL, or WAIT]
                    Confidence: [Low/Medium/High]
                    Reasoning: [1-2 sentences]"""},
                    {"role": "user", "content": formatted_data}
                ],
                temperature=0.7,
                max_tokens=350
            )
            
            # Extract and format the response
            analysis = response.choices[0].message.content.strip()
            
            # Add a separator for better readability
            formatted_response = "\n" + "="*50 + "\nGPT ANALYSIS:\n" + "="*50 + "\n" + analysis + "\n" + "="*50 + "\n"
            
            return formatted_response
            
        except Exception as e:
            print(f"Error in GPT analysis: {e}")
            return None 
import openai
from config import OPENAI_API_KEY

class GPTSignalChecker:
    def __init__(self):
        openai.api_key = OPENAI_API_KEY
        
    def analyze_setup(self, market_data):
        """
        Use GPT to analyze the trading setup and provide a recommendation
        
        Args:
            market_data (dict): Dictionary containing market data and indicators
            
        Returns:
            dict: Analysis results including recommendation and reasoning
        """
        try:
            # Format the prompt with market data
            prompt = self._format_prompt(market_data)
            
            # Get GPT's analysis
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """You are an expert crypto trader analyzing market setups.
                    You should only recommend entering a trade if ALL signal conditions are met AND the risk/reward ratio is favorable.
                    Be conservative in your analysis and err on the side of caution.
                    Your response should clearly state whether to ENTER or WAIT, followed by your reasoning."""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            # Extract the response
            analysis = response.choices[0].message.content
            
            # Parse the response
            recommendation = {
                'enter_trade': 'ENTER' in analysis.upper() and 'WAIT' not in analysis.upper(),
                'analysis': analysis,
                'signal_type': 'BUY' if 'ENTER' in analysis.upper() else None
            }
            
            return recommendation
            
        except Exception as e:
            print(f"Error getting GPT analysis: {str(e)}")
            return None
            
    def _format_prompt(self, data):
        """Format market data into a prompt for GPT"""
        return f"""Please analyze this trading setup for {data['market_data']['symbol']}:

MARKET DATA:
Current Price: ${data['market_data']['price']['current']:,.2f}
Daily Change: {data['market_data']['price']['price_change_pct']:.2f}%

SIGNAL CONDITIONS:
1. VWAP Reclaim: {"Yes" if data['signal_analysis']['signals']['vwap_reclaim'] else "No"}
2. Rising Volume (5-bar): {"Yes" if data['signal_analysis']['signals']['rising_volume'] else "No"}
3. RSI(5) Cross Above 50: {"Yes" if data['signal_analysis']['signals']['rsi_cross_50'] else "No"}

CURRENT INDICATORS:
- RSI(5): {data['technical_indicators']['rsi']:.1f}
- Current Price vs VWAP: ${(data['market_data']['price']['current'] - data['technical_indicators']['vwap']):.2f}
- Volume vs 5-bar Average: {data['technical_indicators']['volume']['current'] / data['technical_indicators']['volume']['average'] if data['technical_indicators']['volume']['average'] > 0 else 1.0:.1f}x

TRADE LEVELS:
Entry: ${data['signal_analysis']['levels']['entry']:,.2f}
Stop Loss: ${data['signal_analysis']['levels']['stop_loss']:,.2f}
Target: ${data['signal_analysis']['levels']['target']:,.2f}
Risk/Reward: {data['signal_analysis']['levels']['risk_reward_ratio']:.1f}

Based on these specific conditions, should we enter a LONG trade or WAIT?
Consider:
1. All three signal conditions must be met (VWAP reclaim, Rising Volume, RSI cross)
2. Risk/Reward ratio should be at least 2:1
3. Current market context

Please provide your analysis and recommendation.""" 
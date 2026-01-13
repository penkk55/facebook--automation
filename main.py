import asyncio
import pyotp
import logging
from typing import Optional
from droidrun import DroidAgent, DroidrunConfig
from llama_index.llms.openai import OpenAI # Import the specific class
import os

# 1. Setup Logging (Professionalism Criteria)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FB-Automation")

class FBLoginAutomation:
    def __init__(self, uid: str, password: str, twofa_key: str):
        self.uid = uid
        self.password = password
        self.twofa_key = twofa_key
        self.config = DroidrunConfig()
        
    def generate_otp(self) -> str:
        """Calculates 6-digit TOTP code."""
        try:
            # ลบช่องว่างออกเผื่อมีติดมา
            clean_key = self.twofa_key.replace(" ", "")
            totp = pyotp.TOTP(clean_key)
            return totp.now()
        except Exception as e:
            logger.error(f"Failed to generate OTP: {e}")
            return ""


    def build_goal(self) -> str:
        """Constructs a clear, step-by-step goal for the AI Agent."""
        otp = self.generate_otp()

        return (
            "1. Open the target application.\n"
            "2. Wait for the login screen to appear.\n"
            f"3. Ensure you are NOT on the 'Create new account' screen. "
            f"If that screen is displayed, tap the top-left back button to return. "
            f"Once on the login screen, enter the username '{self.uid}' into the username field only.\n"

            # f"3. DONT click the create new account (if happned to in that page click back topleft)Enter the username '{self.uid}' into the username field only.\n"
            "4. Click the 'Continue' button.\n"
            f"5. Enter the username '{self.uid}' into the username field and Enter the password '{self.password}' into the password field.\n"
            "6. Click the 'Login' button.\n"
            f"7. When the one-time code screen appears, input the 6-digit code '{otp}'.\n"
            "8. Click the 'Continue' button.\n"
            "9. Determine the final state:\n"
            "   - Success: main/home screen is visible.\n"
            "   - Restricted: a warning or limited-access message is shown.\n"
            "   - Checkpoint: verification or additional confirmation is required."
        )


    async def execute(self):
        """Runs the automation and handles errors."""
        llm_model = OpenAI(model="gpt-4", api_key=os.getenv("OPENAI_API_KEY"))
        agent = DroidAgent(
            goal=self.build_goal(),
            config=self.config,
            llms=llm_model
        )

        logger.info(f"🚀 Starting automation for UID: {self.uid}")
        
        try:
            # Run the agent and wait for completion
            result = await agent.run()
            
            # Print Professional Summary
            print("\n" + "="*30)
            print(f"STATUS: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
            print(f"REASON: {result.reason}")
            print(f"FINAL STATE: {self.classify_status(result)}")
            print("="*30)
            
            return result
            
        except Exception as e:
            logger.error(f"Critical error during agent execution: {e}")
            return None

    def classify_status(self, result) -> str:
        """
        Logic Check Criteria: แยกแยะผลลัพธ์จากข้อความที่ Agent ส่งกลับมา
        """
        reason = result.reason.lower()
        if result.success and "home" in reason:
            return "✅ Success: Logged In"
        elif "restricted" in reason or "limited" in reason:
            return "⚠️ Restricted: Account Flagged"
        else:
            return "❌ Checkpoint: Identity/Credential Issue"

# --- Main Entry Point ---
async def main():
    
## case 1 success
    test_uid = "1768304079"
    test_pass = "fucknoob94"
    test_2fa = "2LHSR3DZIDJKBJ4XANX62IMR6V7BIPTV"

    ## case 2 restricted account
    # test_uid = "100004054953628"
    # test_pass="@MINHQUAN123"
    # test_2fa = "2COWKPZVTENXNBQSANCUNOY64ISZJ6HY"

    ## case wrong password
    # test_uid = "12345678"
    # test_pass = "12345678"
    # test_2fa = "2LHSR3DZIDJKBJ4XANX62IMR6V7BIPTR"

    bot = FBLoginAutomation(test_uid, test_pass, test_2fa)
    await bot.execute()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")

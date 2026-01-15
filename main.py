import asyncio
import pyotp
import logging
import os
from droidrun.tools import AdbTools

# Setup Professional Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FB-Hybrid")

class FBLoginAutomation:
    def __init__(self, uid, password, twofa_key, serial="emulator-5554"):
        self.uid = uid
        self.password = password
        self.twofa_key = twofa_key
        self.package = "com.facebook.katana"
        self.tools = AdbTools(serial=serial)
        self.is_connected = False

    def generate_otp(self) -> str:
        """Calculates 6-digit TOTP code safely."""
        try:
            clean_key = self.twofa_key.replace(" ", "")
            totp = pyotp.TOTP(clean_key)
            return totp.now()
        except Exception as e:
            logger.error(f"OTP Generation failed: {e}")
            return ""

    async def ensure_connection(self):
        """Resilient connection handler."""
        if not self.is_connected:
            try:
                await self.tools.connect()
                self.is_connected = True
                logger.info("✅ ADB Connected")
            except Exception as e:
                logger.error(f"ADB Connection Failed: {e}")
                raise

    async def wait_for_index(self, index: int, timeout: int = 20) -> bool:
        """
        Explicit Wait Logic: Polls the UI until the index is found.
        Prevents script death if the app is slow or net lags.
        """
        for i in range(timeout):
            try:
                # Refresh state to update cache
                await self.tools.get_state()
                # Check if index exists in the current clickable cache
                if any(el.get('index') == index for el in self.tools.clickable_elements_cache):
                    return True
            except Exception:
                pass
            
            logger.info(f"⏳ Waiting for UI element {index}... ({i+1}/{timeout})")
            await asyncio.sleep(2)
        return False

    async def execute(self):
        """Main Execution Flow with Exception Handling."""
        try:
            await self.ensure_connection()

            # --- STEP 1: START APP ---
            logger.info("🏠 Resetting to Home and Launching FB...")
            await self.tools.press_key(3) # HOME
            await self.tools.start_app(self.package)

            await self.tools.get_state()

            # --- STEP 2A: USERNAME ---
            if not await self.wait_for_index(13):
                raise Exception("Username field (13) never appeared")
            
            logger.info("🎯 Entering Username...")
            await self.tools.tap_by_index(13)
            await self.tools.input_text(self.uid)
            await asyncio.sleep(1)

             # --- STEP 2B: PASSWORD ---
            logger.info("🎯 Entering Password...")
            await self.tools.tap_by_index(15)
            await self.tools.input_text(self.password)
            await asyncio.sleep(1)



           # --- STEP 3: LOGIN ---
            logger.info("➡️ Tapping Login Button (Index 17)...")
            await self.tools.tap_by_index(16)
            await asyncio.sleep(2)

           # --- STEP 3.1: WRONG PASSWORD / SECURITY CHECK ---
            logger.info("🔍 Checking for login errors at Index 12...")
            await self.tools.get_state()
            # ใช้ wait_for_index เพื่อรอให้ Index 12 ปรากฏขึ้นมา (Timeout 5 วินาที)
            if await self.wait_for_index(12, timeout=5):
                # ดึงข้อมูลจาก Cache ล่าสุดที่ get_state() ใน wait_for_index ทำไว้
                a11y_tree = self.tools.clickable_elements_cache
                
                # ค้นหาโหนดที่มี Index 12
                node_12 = next((el for el in a11y_tree if el.get('index') == 12), None)
                
                if node_12:
                    node_text = node_12.get('text', '')
                    logger.info(f"🔎 Found Index 12 with text: '{node_text}'")

                    # ตรวจสอบว่าตรงกับข้อความที่ต้องการหรือไม่
                    if "Check your email" in node_text or "Need help finding your account?" in node_text:
                        logger.warning(f"❌ Login Issue Detected: {node_text}")
                        
                        # ดึง formatted text ล่าสุดเพื่อส่งไป classify
                        formatted, _, _, _ = await self.tools.get_state()
                        return f"❌ FAILED: {self.classify_final_state(formatted)}"

            # หากไม่เจอ Index 12 หรือข้อความไม่ตรง ให้ทำ Step 3.2 ต่อไป (2FA/Home)
            logger.info("✅ No immediate errors detected, proceeding to 2FA/Home check.")

            # --- STEP 3.2: SMART CHECK (2FA vs HOME) ---
            logger.info("⏳ Determining next screen (2FA or Home)...")
            is_2fa_needed = False
            
            for i in range(20):
                formatted, _, a11y_tree, _ = await self.tools.get_state()
                ui_text = formatted.lower()
                
                # เช็คหน้า 2FA จากปุ่ม 'Try another way' (Index 21)
                if any(el.get('index') == 21 and "try another way" in el.get('text', '').lower() for el in a11y_tree):
                    logger.info("🔑 2FA Screen Detected: 'Try another way' (Index 21) is visible.")
                    is_2fa_needed = True
                    break
                
                # เช็คหน้า Home
                if "home" in ui_text or "what's on your mind" in ui_text:
                    logger.info("🏠 Success! News Feed detected. Skipping 2FA.")
                    is_2fa_needed = False
                    break
                
                logger.info(f"⏳ Waiting for screen transition... ({i+1}/20)")
                await asyncio.sleep(1)

            # --- STEP 4: 2FA HANDLING ---
            if is_2fa_needed:
                logger.info("🛠 Navigating to OTP Input...")
                
                # 1. แตะ 'Try another way' (Index 21)
                await self.tools.tap_by_index(21)
                await asyncio.sleep(3)
                
                # 2. เลือกวิธีการรับรหัส (จาก Logic เดิมของคุณคือ Index 18 แล้วกด Continue 25)
                await self.tools.get_state()
                logger.info("Selecting OTP Method (Index 18)...")
                await self.tools.tap_by_index(18)
                await asyncio.sleep(1)
                
                logger.info("Tapping Continue to get OTP field (Index 25)...")
                await self.tools.tap_by_index(25)
                
                # 3. รอช่องกรอกรหัส (Explicit Wait)
                logger.info("⏳ Waiting for OTP code field (Index 17)...")
                if await self.wait_for_index(17, timeout=15):
                    otp = self.generate_otp()
                    logger.info(f"🔢 Generated OTP: {otp}")
                    
                    await self.tools.tap_by_index(17)
                    await self.tools.input_text(otp)
                    await asyncio.sleep(1)
                    
                    # 4. กดปุ่มยืนยันรหัสตัวสุดท้าย (Index 21)
                    logger.info("➡️ Submitting OTP (Index 21)...")
                    await self.tools.tap_by_index(21)
            else:
                logger.info("⏩ 2FA was not triggered or already handled.")
            
            # --- STEP 5: FINAL CLASSIFICATION ---
            await asyncio.sleep(10)
            formatted, _, _, phone_state = await self.tools.get_state()
            return self.classify_final_state(formatted)

        except Exception as e:
            logger.error(f"❌ Automation Error: {e}")
            return f"Error: {str(e)}"

    def classify_final_state(self, ui_text: str) -> str:
        """Logic Check: Determines if restricted, success, or checkpoint."""
        text = ui_text.lower()
        if "restricted" in text or "account disabled" in text:
            return "⚠️ RESTRICTED"
        if "home" in text or "whats on your mind" in text:
            return "✅ SUCCESS"
        if "confirm your identity" in text or "checkpoint" or "need help finding your account?" in text:
            return "❌ CHECKPOINT"
        return "❓ UNKNOWN (Manual check required)"

# for debugging
    async def debug_fb_ui():
        tools = AdbTools(serial="emulator-5554")
        raw_data = await tools.get_state()
        
        print("\n--- 🔍 RAW DATA TYPE INSPECTION ---")
        print(f"Type of raw_data: {type(raw_data)}")
        
        # If it's a tuple, let's see what's inside each part
        if isinstance(raw_data, tuple):
            print(f"Tuple length: {len(raw_data)}")
            for i, item in enumerate(raw_data):
                print(f"  Part {i} type: {type(item)}")
                print(f"  Part {i} content: {item}")
                # If this part is the dictionary, that's our UI tree
                if isinstance(item, dict):
                    root_node = item
        elif isinstance(raw_data, dict):
            root_node = raw_data
        else:
            print("❌ Data is not a dict or tuple. Raw content:", raw_data)
            return

        print("\n--- 📱 FACEBOOK UI TREE ---")
        
        def print_all(node, indent=0):
            # If it's a string, just print it (sometimes nodes are just labels)
            if isinstance(node, str):
                print(f"{'  ' * indent}[String Content]: {node}")
                return

            if isinstance(node, dict):
                text = node.get("text") or node.get("content_desc") or ""
                rid = node.get("resource_id") or node.get("resourceId") or ""
                idx = node.get("index", "?")
                
                # Print even if it has no text (to see the structure)
                label = f"[Idx: {idx}]"
                if text: label += f" Text: '{text}'"
                if rid:  label += f" ID: {rid}"
                if not text and not rid: label += " (Container/Layout)"
                
                print(f"{'  ' * indent}{label}")

                children = node.get("children")
                if isinstance(children, list):
                    for child in children:
                        print_all(child, indent + 1)
            
            elif isinstance(node, list):
                for item in node:
                    print_all(item, indent)

        print_all(root_node)
        print("--- 🏁 END OF DUMP ---\n")

# --- Execution ---
async def main():

# case : "success"
    test_uid = "1768304079"
    test_pass = "fucknoob94"
    test_2fa = "2LHSR3DZIDJKBJ4XANX62IMR6V7BIPTV"

    # Case: Restricted Account
    # test_uid = "100004054953628"
    # test_pass = "@MINHQUAN123"
    # test_2fa = "2COWKPZVTENXNBQSANCUNOY64ISZJ6HY"

    # Case: Wrong Password
    # test_uid = "1768304079"
    # test_pass = "12345678"
    # test_2fa = "2LHSR3DZIDJKBJ4XANX62IMR6V7BIPTR"

    

    bot = FBLoginAutomation(test_uid, test_pass, test_2fa)
    result = await bot.execute()
    
    print("\n" + "="*40)
    print(f"FINAL RESULT: {result}")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(main())

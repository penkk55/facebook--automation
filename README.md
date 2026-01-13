# FB Login Automation (Demo / Research Project)

> ⚠️ **Disclaimer**  
> This project is intended for **research, prototyping, and automation framework testing** only.  
> It demonstrates how to structure an AI-driven Android automation workflow using `droidrun`, OTP generation, and state classification logic.  
> It is **not** intended for unauthorized access to third-party services.

---

## Overview

This project demonstrates an **AI-driven Android automation flow** using:

- **droidrun** for Android UI control
- **LLM (OpenAI via llama_index)** for goal-driven agent reasoning
- **pyotp** for Time-based One-Time Password (TOTP) generation
- **asyncio** for non-blocking execution
- **structured logging** for observability

The automation is built around a reusable class that:
1. Accepts login credentials (demo data)
2. Generates a 6-digit OTP
3. Constructs a clear, step-by-step goal for an AI agent
4. Executes the agent on an Android emulator
5. Classifies the final UI state into predefined outcomes

---

## Project Structure


import asyncio
import traceback
from videosdk.agents import Agent, AgentSession, RealTimePipeline, JobContext, RoomOptions, WorkerJob, Options
from videosdk.plugins.google import GeminiRealtime, GeminiLiveConfig
from dotenv import load_dotenv
import os
import logging
logging.basicConfig(level=logging.INFO)

# Load .env from the same directory as this script (so it works regardless of cwd)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)
# Strip in case .env has trailing space/newline (can cause "Token is invalid")
VIDEOSDK_AUTH_TOKEN = (os.getenv("VIDEOSDK_AUTH_TOKEN") or "").strip() or None

# Define the agent's behavior and personality
class MyVoiceAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="You are a helpful AI assistant that answers phone calls. Keep your responses concise and friendly.",
        )

    async def on_enter(self) -> None:
        await self.session.say("Hello! I'm your real-time assistant. How can I help you today?")

    async def on_exit(self) -> None:
        await self.session.say("Goodbye! It was great talking with you!")

async def start_session(context: JobContext):
    # Configure the Gemini model for real-time voice
    model = GeminiRealtime(
        model="gemini-2.5-flash-native-audio-preview-12-2025",
        api_key=os.getenv("GOOGLE_API_KEY"),
        config=GeminiLiveConfig(
            voice="Leda",
            response_modalities=["AUDIO"]
        )
    )
    pipeline = RealTimePipeline(model=model)
    session = AgentSession(agent=MyVoiceAgent(), pipeline=pipeline)

    try:
        await context.connect()
        await session.start()
        await asyncio.Event().wait()
    finally:
        await session.close()
        await context.shutdown()

def make_context() -> JobContext:
    room_options = RoomOptions()
    return JobContext(room_options=room_options)

if __name__ == "__main__":
    try:
        if not VIDEOSDK_AUTH_TOKEN:
            raise ValueError(
                "VIDEOSDK_AUTH_TOKEN not found. Add it to your .env file in the Voice_agent folder, e.g.:\n"
                'VIDEOSDK_AUTH_TOKEN="your-token-here"'
            )
        # Register the agent with a unique ID
        options = Options(
            agent_id="MyTelephonyAgent", # CRITICAL: Unique identifier for routing
            register=True, # REQUIRED: Register with VideoSDK for telephony
            max_processes=10, # Concurrent calls to handle
            host="localhost",
            port=8081,
            auth_token=VIDEOSDK_AUTH_TOKEN,  # Pass token from .env so Worker sees it
        )
        job = WorkerJob(entrypoint=start_session, jobctx=make_context, options=options)
        job.start()
    except Exception as e:
        traceback.print_exc()

import logging
from dotenv import load_dotenv
from typing import Literal

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions,function_tool,RunContext
from livekit.plugins import (
    openai,
    noise_cancellation,
    silero,
    
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents import BackgroundAudioPlayer, AudioConfig, BuiltinAudioClip

from  utils import get_user_presence

logger = logging.getLogger("annotated-tool-args")
logger.setLevel(logging.INFO)

load_dotenv()
import requests
import os
DIAMY_GRAPH_ACCESS_TOKEN = os.getenv("DIAMY_GRAPH_ACCESS_TOKEN")
logger.info(f'The microsoft graph token: {DIAMY_GRAPH_ACCESS_TOKEN[0:10]}.....')


system_prompt = """
                You are an assistant communicating only in French via voice. 
                Your role is to help callers to check if their correspondant is available or not.
"""


from pydantic import BaseModel, Field, EmailStr

from typing import Annotated, List,Optional
from datetime import datetime


class Client(BaseModel):
    last_name:   str= Field(...,description="The client's name")
    email:  str= Field(...,description="The client's email")

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=system_prompt)
    
    async def on_enter(self):



        email = "cbornecque@w3tel.com"  # Replace with actual email
        url = f"https://graph.microsoft.com/v1.0/users/{email}"
        headers = {
            "Authorization": f"Bearer {DIAMY_GRAPH_ACCESS_TOKEN}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logger.info("✅ User exists:")
            user_id = response.json()['id']
            logger.info(f"User id is: {user_id}")
            availability = get_user_presence(user_id)['raw']['availability']
            logger.info(f'availability: {availability}')
        elif response.status_code == 404:
            logger.info("❌ User not found")
        else:
            logger.error(f"⚠️ Error {response.status_code}: {response.text}")

        # Logic to check the correpondent availability

        called_email = "Bornecque"
        available = True
        status = 'available' if available else 'not available'
        if available:
            message = "Tell the caller that the correspondant they are trying to reach is {}. You will now transfer the call.".format(status)
        else:
            message = (
                "Tell the caller that the correspondant they are trying to reach is {}. "
                "If he or she is not available, tell the user that you can help by sending an email to the correspondant if it is urgent."
            ).format(status)
        await self.session.generate_reply(
            instructions = message
            )
    
    @function_tool()
    async def book_slot(
          self,
          context: RunContext,
          client:Client,
          slot:str,
          haircut_category:str,
      ) -> dict:
          """Book a slot for a service.

          Args:
              client: the client information need to make an appointment
              slot: The slot to book.
              haircut_category: The category of the haircut chosen by the client.

          Returns:
              A confirmation message
          """
          
          logger.info(f"The context is  {context.function_call.model_json_schema()}")

          logger.info(f"The client is  {client}")
          logger.info(f"The slot is     {slot}")
          logger.info(f"The haircut_category is  {haircut_category}")


          # Logic - Insert in DataBase

          return {"success": "Ok"}

    @function_tool()
    async def send_email(
          self,
          context: RunContext,
          to: str,
      ) -> dict:
          """Send an email to a client.

          Args:
              to: The email of the client.

          Returns:
              A confirmation message
          """

          logger.info(f"Context   {context}")
          logger.info(f"to   {to}")

          return {"success": "Ok"}

    @function_tool()
    async def get_availability(
        self,
        context: RunContext,
        date_range:str
    )-> dict:
      """Get availability for a date range.

      Args:
          date_range: The date range to get availability for.

      Returns:
          A list of available slots.
      """
      return {'available_dates':["20/10","25/10","28/10"]}

    @function_tool()
    async def has_appointment(
        self,
        context: RunContext,
        name:str
    )-> dict:
      """Check if an appointment exists.

      Args:
          name: The id of the appointment to check.

      Returns:
          A confirmation message.
      """
      return {'has_appointment':True,"appointment_id":"10010202"}


    @function_tool()
    async def cancel_appointment(
        self,
        context: RunContext,
        appointment_id:str
    )-> dict:
      """Cancel an appointment.

      Args:
          appointment_id: The id of the appointment to cancel.

      Returns:
          A confirmation message.
      """

      return {'success':True}

    @function_tool()
    async def haircut_prices(
        self,
        context: RunContext,
        category:Literal["standard_cut", "skin_fade", "beard_trim", "shave", "combo_cut_and_beard"],
    )-> dict:
      """Get haircut prices.

      Args:
          category: The category of the haircut.

      Returns:
          a dictionnary of haircut prices.
      """
      haircut_prices = {
              "standard_cut": '20 euro',
              "skin_fade": '25 euro',
              "beard_trim": '10 euro',
              "shave": '15 euro',
              "combo_cut_and_beard": '30 euro'}



      return haircut_prices[category]


async def entrypoint(ctx: agents.JobContext):
    logger.info(f'Entry Point: {agents.JobContext}')
    await ctx.connect()

    session = AgentSession(

        stt=openai.STT(language="fr",model="gpt-4o-transcribe"),
        llm=openai.LLM(model="gpt-4o-mini"),
          tts = openai.TTS(
                            model="gpt-4o-mini-tts",
                            voice="alloy",
                            instructions="Speak in a friendly and conversational tone.",
                        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            # LiveKit Cloud enhanced noise cancellation
            # - If self-hosting, omit this parameter
            # - For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(), 
        ),
    )

    await session.generate_reply(
       instructions="greet the user and tell me that you will check if his correspondant is available or not to forward the call."
    )

    background_audio = BackgroundAudioPlayer(
      # play office ambience sound looping in the background
      ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.8),
      # play keyboard typing sound when the agent is thinking
      thinking_sound=[
               AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.8),
               #AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.7),
               #AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE,volume=0.5),

         ],
    )
    await background_audio.start(room=ctx.room, agent_session=session)

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
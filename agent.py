import logging
from dotenv import load_dotenv, set_key
from typing import Literal

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions,function_tool,RunContext, ChatContext
from livekit.plugins import (
    openai,
    noise_cancellation,
    silero,
    
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents import BackgroundAudioPlayer, AudioConfig, BuiltinAudioClip

from  utils import get_user_presence, get_access_token

import requests
import os



logger = logging.getLogger("agent.py")
logger.setLevel(logging.INFO)

load_dotenv()

tenant_id = os.getenv("tenant_id")
client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")

access_token = get_access_token(tenant_id,client_id,client_secret).get('access_token')
phonepilote_token  = os.getenv("PHONE_PILOT")


assert access_token, "MG Access token is missing!"
assert phonepilote_token, "PP Access token is missing!"




from pydantic import BaseModel, Field, EmailStr

from typing import Annotated, List,Optional
from datetime import datetime


class Client(BaseModel):
    last_name:   str= Field(...,description="The client's name")
    email:  str= Field(...,description="The client's email")

class Diamanda(Agent):
     
    def __init__(self) -> None:

        self.agent_name = self.__class__.__name__

        system_prompt = (
                f"Vous êtes un assistant qui communique uniquement en français. et Votre nom est {self.agent_name}"
                f"Vous êtes toujours poli, professionnel et clair."
                f"Votre role principale est de dériger les appelants selon leur besoin vers le service le plus adapté en transferant leur appels"
                f"les services sont les suivant: Support technique"
            )

        super().__init__(instructions=system_prompt)
        
      
            
    @function_tool()
    async def on_enter(self):
        """Use this tool check the availability of a user when a caller connect with you."""
        
        # When receiving a call, you get the caller's name from the phone number, and the called user's email and name from the database.
        # For example, if the caller phone number is "+32471234567", you can get the caller's name from your database.
        email, called_name = "cbornecque@w3tel.com" , "Cédric Bornécque"
        sipExtension = "8933180963004"

        caller_name = "Mazouz Abderahim"
        SIP = 8933180963014

        url_mg = f"https://graph.microsoft.com/v1.0/users/{email}"
        url_pp = f"https://extranet.w3tel.com/api/voip/v1/users/{SIP}/1/1000/undefined"

        microsoft_graph_response = requests.get(url_mg, headers={"Authorization": f"Bearer {access_token}"})
        phonepilote_response     = requests.get(url_pp,  headers={"Authorization": f"{phonepilote_token}"})

        microsoft_graph_response.raise_for_status()
        phonepilote_response.raise_for_status()

        # Availability on Microsoft Graph
        user_id = microsoft_graph_response.json()['id']
        availability  = get_user_presence(user_id)['raw']['availability']
        
        # Availability on Phone Pilot
        users = phonepilote_response.json()['users']
        user = [u for u in users if u["sipExtension"] == sipExtension]
        status = user[0]['status']

        logger.info(f"Status: {status}")
        
        if (availability != "Available") or (status != 1) :

            instructions = (
                f"Dites Bonjour à {caller_name}, puis présentez-vous"
                f"Informez l'appelant que {called_name} est actuellement indisponible. "
                f"Demandez-lui ensuite la raison de son appel soit: "
                f"- Afin de pouvoir le diriger vers le groupe le plus adapté à son besoin. "
                f"Ou,"
                f"- D'envoyer un message au correspondant "
            )


            await self.session.generate_reply(
                    instructions = instructions,
                    allow_interruptions=False

                )
       
        else: # Disponible
            instructions = (
                f"Bonjour {caller_name}, je me présente, je suis {self.agent_name} l'assistante de {called_name}. "
                f"{called_name} est actuellement disponible."
                f"Si vous souhaitez  parler directement à {called_name}, je peux lui transférer votre appel immédiatement."
            )


            await self.session.say(
                    text = instructions,
                    allow_interruptions=False
                )


        
    
    @function_tool()
    async def check_technical_support_availability(
          self,
          context: RunContext,
      ) -> dict:
        """
        Vérifie si le support technique est disponible au moment de l'appel.

        Args:
            

        Returns:
            dict: Clef = ID agent technique, valeur = booléen indiquant disponibilité.
        """

        # Mock des agents techniques avec leur disponibilité
        technical_agents = {
        "Kévin": {
            "availability": True,
            "current_task": "Support incident #1234",
            "last_active": "2025-06-06T09:45:00Z",
            "expertise": ["réseau", "serveurs"],
            "contact": "kevin@example.com",
            "response_time_sec": 15,
            "shift": "matin",
        },
        "Aubin": {
            "availability": False,
            "current_task": None,
            "last_active": "2025-06-06T08:00:00Z",
            "expertise": ["base de données", "sécurité"],
            "contact": "aubin@example.com",
            "response_time_sec": None,
            "shift": "après-midi",
        },
        "Cédric": {
            "availability": True,
            "current_task": "Maintenance système",
            "last_active": "2025-06-06T09:30:00Z",
            "expertise": ["systèmes Linux", "virtualisation"],
            "contact": "cedric@example.com",
            "response_time_sec": 20,
            "shift": "matin",
        },
    }

        return technical_agents

    @function_tool()
    async def send_email(
          self,
          context: RunContext,
          content: str,
      ) -> dict:
          """Send an email to the correspondant.

          Args:
              content: The the email content of the correpondant.

          Returns:
              A confirmation message
          """

          logger.info(f"Context: {context}")
          logger.info(f"email Content  {content}")

          return {"success": "Ok"}

    @function_tool()
    async def call_transfert(
        self,
        context: RunContext,
        distination:str
    )-> dict:
      """Use this Tool to Transfert the call to its distination.

      Args:
          distination: the phone number to the destination

      Returns:
          A confirmation message.
      """
      return {'sucess':'ok'}


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
    logger.info("CONNECTED")
    logger.info(f"{'- Worker ID':<13}: {ctx.worker_id}")
    logger.info(f"{'- Agent ID':<13}: {ctx.agent}")
    logger.info(f"{'- Room':<13}: {ctx.room}")
    logger.info(f"{'- Proc user id':<13}: {ctx.proc.userdata}")
    logger.info(f"{'- Proc pid':<13}: {ctx.proc.pid}")
        

    session = AgentSession(

        stt=openai.STT(language="fr",model="gpt-4o-transcribe"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts = openai.TTS(
                            model="gpt-4o-mini-tts",
                            voice="alloy",
                        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    await session.start(
        room=ctx.room,
        agent=Diamanda(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(), 
        ),
    )

    background_audio = BackgroundAudioPlayer(
      # play office ambience sound looping in the background
      ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.8),
      # play keyboard typing sound when the agent is thinking
      thinking_sound=[
               AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.8),
         ],
    )
    await background_audio.start(room=ctx.room, agent_session=session)

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
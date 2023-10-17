import json
import logging
import os
import sys
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Body
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

from global_data import add_key_value_pair
from memory_config import config_manager
from voice.streaming.constants import INITIAL_MESSAGE
from voice.streaming.models.agent import ChatGPTAgentConfig
from voice.streaming.models.audio_encoding import AudioEncoding
from voice.streaming.models.message import BaseMessage
from voice.streaming.models.synthesizer import ElevenLabsSynthesizerConfig
from voice.streaming.models.telephony import TwilioConfig
from voice.streaming.models.transcriber import DeepgramTranscriberConfig
from voice.streaming.telephony.conversation.outbound_call import OutboundCall
from voice.streaming.telephony.server.base import TelephonyServer, InboundCallConfig

load_dotenv()

app = FastAPI(docs_url=None)

# Configure CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# First we will open up our TelephonyServer, which opens a path at
# our BASE_URL. Once we have a path, we can request a call from
# Twilio to Zoom's dial-in service or any phone number.

# We need a base URL for Twilio to talk to:
# If you're self-hosting and have an open IP/domain, set it here or in your env.
BASE_URL = os.environ.get("BASE_URL")

# If you're using Replit, open domains are handled for you.
if os.environ.get('REPL_SLUG') is not None:
    BASE_URL = f"{os.environ.get('REPL_SLUG')}.{os.environ.get('REPL_OWNER')}.repl.co"

# If neither of the above are true, we need a tunnel.
if not BASE_URL:
    from pyngrok import ngrok

    ngrok_auth = os.environ.get("NGROK_AUTH_TOKEN")
    if ngrok_auth is not None:
        ngrok.set_auth_token(ngrok_auth)
    port = sys.argv[sys.argv.index("--port") +
                    1] if "--port" in sys.argv else 3000

    # Open a ngrok tunnel to the dev server
    BASE_URL = ngrok.connect(port).public_url.replace("https://", "")
    logger.info("ngrok tunnel \"{}\" -> \"http://127.0.0.1:{}\"".format(
        BASE_URL, port))

# Now we need a Twilio account and number from which to make our call.
# You can make an account here: https://www.twilio.com/docs/iam/access-tokens#step-2-api-key
TWILIO_CONFIG = TwilioConfig(
    account_sid=os.environ.get("TWILIO_ACCOUNT_SID") or "<your twilio account sid>",
    auth_token=os.environ.get("TWILIO_AUTH_TOKEN") or "<your twilio auth token>",
)


# You can use your free number of buy a premium one here:
# https://www.twilio.com/console/phone-numbers/search
# Once you have one, set it here or in your env.
def set_twilio_phone(number):
    return number


# We store the state of the call in memory, but you can also use Redis.
# https://docs.voice.dev/telephony#accessing-call-information-in-your-agent
CONFIG_MANAGER = config_manager  # RedisConfigManager()


# Now, we'll configure our agent and its objective.
# We'll use ChatGPT here, but you can import other models like
# GPT4AllAgent and ChatAnthropicAgent.
# Don't forget to set OPENAI_API_KEY!

def read_file_contents(chosen_script):
    try:
        with open(f"prompt_script_{chosen_script}.json", 'r') as file:
            data = json.load(file)
            contents = [item['content'] for item in data]
            return contents
    except FileNotFoundError:
        return None


def create_agent_config(script_type, voice_type, custom_script_type, temperature):
    if script_type == 0:
        data = json.loads(custom_script_type)
        contents = [item['content'] for item in data]
    else:
        contents = read_file_contents(script_type)

    if voice_type == "female" or voice_type == "female-andrea" or voice_type == "tiffany":
        if script_type == 3 or script_type == 4:
            contents[1] = contents[1].replace("Chris", "Jacky")
            contents[0] = contents[0].replace("Chris", "Jacky")

        if script_type == 2:
            contents[0] = contents[0].replace("Mike", "Jacky")

        if script_type == 1:
            contents[0] = contents[0].replace("Chris", "Jacky")

    add_key_value_pair(INITIAL_MESSAGE, contents[1])
    return ChatGPTAgentConfig(
        initial_message=BaseMessage(text=contents[1]),
        prompt_preamble=contents[0],
        model_name="gpt-3.5-turbo-16k-0613",
        temperature=temperature,
        generate_responses=True,
    )


# Now we'll give our agent a voice and ears.
# Our default speech to text engine is DeepGram, so you'll need to set
# the env variable DEEPGRAM_API_KEY to your Deepgram API key.
# https://deepgram.com/

# We use StreamElements for speech synthesis here because it's fast and
# free, but there are plenty of other options that are slower but
# higher quality (like Eleven Labs below, needs key) available in
# voice.streaming.models.synthesizer.
# SYNTH_CONFIG = StreamElementsSynthesizerConfig.from_telephone_output_device()

def create_synthesizer_config(voice_id, stability, similarity_boost, optimize_streaming_latency):
    api_key = os.environ.get("ELEVEN_LABS_API_KEY") or "<your EL token>"
    model_id = "eleven_monolingual_v1"  # You can adjust this if needed

    return ElevenLabsSynthesizerConfig.from_telephone_output_device(
        api_key=api_key,
        voice_id=voice_id,
        stability=stability,
        similarity_boost=similarity_boost,
        optimize_streaming_latency=optimize_streaming_latency,
        model_id=model_id,
    )


MALE_VOICE_ID = os.environ.get("DEFAULT_MALE_VOICE_ID")
FEMALE_VOICE_ID = os.environ.get("DEFAULT_FEMALE_VOICE_ID")
ANDREA_VOICE_ID = os.environ.get("ANDREA_VOICE_ID")
TIFFANY_VOICE_ID=os.environ.get("TIFFANY_VOICE_ID")
GILFOY_VOICE_ID=os.environ.get("GILFOY_VOICE_ID")
CHRISTOPHER_VOICE_ID=os.environ.get("CHRISTOPHER_VOICE_ID")
RYAN_KURK_VOICE_ID=os.environ.get("RYAN_KURK_VOICE_ID")
STEVE_VOICE_ID=os.environ.get("STEVE_VOICE_ID")
MAXI_ARAYA_VOICE_ID=os.environ.get("MAXI_ARAYA_VOICE_ID")

STABILITY = os.environ.get("DEFAULT_STABILITY")
SIMILARITY_BOOST = os.environ.get("DEFAULT_SIMILARITY_BOOST")
OPTIMIZE_STREAMING_LATENCY = os.environ.get("DEFAULT_OPTIMIZE_STREAMING_LATENCY")
DEFAULT_SAMPLING_RATE = 8000
DEFAULT_AUDIO_ENCODING = AudioEncoding.MULAW
DEFAULT_CHUNK_SIZE = 20 * 160


def create_telephony_server(twilio_config):
    # Let's create and expose that TelephonyServer.
    telephony_server = TelephonyServer(
        base_url=BASE_URL,
        config_manager=CONFIG_MANAGER,
        inbound_call_configs=[
            InboundCallConfig(url="/inbound_call",
                              agent_config=create_agent_config(1, "male", "", 0.4),
                              twilio_config=twilio_config,
                              transcriber_config=DeepgramTranscriberConfig(
                                  sampling_rate=DEFAULT_SAMPLING_RATE,
                                  audio_encoding=DEFAULT_AUDIO_ENCODING,
                                  chunk_size=DEFAULT_CHUNK_SIZE,
                                  model='phonecall',
                                  tier='nova',
                                  min_interrupt_confidence=0.6,
                              ),
                              synthesizer_config=create_synthesizer_config(MALE_VOICE_ID, STABILITY, SIMILARITY_BOOST,
                                                                           OPTIMIZE_STREAMING_LATENCY))
        ],
        logger=logger,
    )

    app.include_router(telephony_server.get_router())


# OutboundCall asks Twilio to call to_phone using our Twilio phone number
# and open an audio stream to our TelephonyServer.
def start_outbound_call(to_phone: Optional[str], agent_config: Optional[ChatGPTAgentConfig],
                        synth_config: Optional[ElevenLabsSynthesizerConfig], caller: Optional[str], twilio_config):
    if to_phone:
        outbound_call = OutboundCall(base_url=BASE_URL,
                                     to_phone=to_phone,
                                     from_phone=caller or set_twilio_phone(os.environ.get("OUTBOUND_CALLER_NUMBER")),
                                     config_manager=CONFIG_MANAGER,
                                     agent_config=agent_config or create_agent_config(1, "male", "", 0.4),
                                     twilio_config=twilio_config,
                                     transcriber_config=DeepgramTranscriberConfig(
                                         sampling_rate=DEFAULT_SAMPLING_RATE,
                                         audio_encoding=DEFAULT_AUDIO_ENCODING,
                                         chunk_size=DEFAULT_CHUNK_SIZE,
                                         model='phonecall',
                                         tier='nova',
                                         min_interrupt_confidence=0.6
                                     ),
                                     synthesizer_config=synth_config or create_synthesizer_config(
                                         MALE_VOICE_ID,
                                         STABILITY,
                                         SIMILARITY_BOOST,
                                         OPTIMIZE_STREAMING_LATENCY))
        outbound_call.start()


# Expose the starter webpage
@app.get("/")
async def root(request: Request):
    env_vars = {
        "BASE_URL": BASE_URL,
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "DEEPGRAM_API_KEY": os.environ.get("DEEPGRAM_API_KEY"),
        "TWILIO_ACCOUNT_SID": os.environ.get("TWILIO_ACCOUNT_SID"),
        "TWILIO_AUTH_TOKEN": os.environ.get("TWILIO_AUTH_TOKEN"),
        "OUTBOUND_CALLER_NUMBER": os.environ.get("OUTBOUND_CALLER_NUMBER"),
        "ELEVEN_LABS_API_KEY": os.environ.get("ELEVEN_LABS_API_KEY"),
        "ASSEMBLY_AI_API_KEY": os.environ.get("ASSEMBLY_AI_API_KEY")
    }

    return templates.TemplateResponse("index.html", {
        "request": request,
        "env_vars": env_vars
    })


@app.post("/start_outbound_call")
async def api_start_outbound_call(
        caller: Optional[str] = Body(os.environ.get("OUTBOUND_CALLER_NUMBER")),
        to_phone: Optional[str] = Body(None),
        gpt_temperature: Optional[float] = Body(0.4),
        voice_type: Optional[str] = Body("male"),  # Default to female if not provided
        custom_voice_type: Optional[str] = Body(""),
        stability: Optional[float] = Body(0.5),
        similarity_boost: Optional[float] = Body(1.0),
        optimize_streaming_latency: Optional[int] = Body(3),  # Default to 0.0 if not provided
        script_type: Optional[int] = Body(1),
        custom_script_type: Optional[str] = Body(None),
        twilio_account_sid: Optional[str] = Body(None),
        twilio_auth_token: Optional[str] = Body(None)
):
    input_parameters = {
        "caller": caller,
        "to_phone": to_phone,
        "gpt_temperature": gpt_temperature,
        "voice_type": voice_type,
        "custom_voice_type": custom_voice_type,
        "stability": stability,
        "similarity_boost": similarity_boost,
        "optimize_streaming_latency": optimize_streaming_latency,
        "script_type": script_type,
    }

    twilio_config = TwilioConfig(
        account_sid=twilio_account_sid,
        auth_token=twilio_auth_token,
    )

    print(input_parameters)

    voice_id = ""
    if voice_type == "female":
        voice_id = FEMALE_VOICE_ID
    elif voice_type == "male":
        voice_id = MALE_VOICE_ID
    elif voice_type == "female-andrea":
        voice_id = ANDREA_VOICE_ID
    elif voice_type == "tiffany":
        voice_id = TIFFANY_VOICE_ID
    elif voice_type == "gilfoy":
        voice_id = GILFOY_VOICE_ID
    elif voice_type == "christopher":
        voice_id = CHRISTOPHER_VOICE_ID
    elif voice_type == "ryan_kurk":
        voice_id = RYAN_KURK_VOICE_ID
    elif voice_type == "steve":
        voice_id = STEVE_VOICE_ID
    elif voice_type == "maxi_araya":
        voice_id = MAXI_ARAYA_VOICE_ID
    elif custom_voice_type:
        voice_id = custom_voice_type

    create_telephony_server(twilio_config)
    agent_config = create_agent_config(script_type, voice_type, custom_script_type, gpt_temperature)
    synth_config = create_synthesizer_config(voice_id, stability, similarity_boost, optimize_streaming_latency)
    start_outbound_call(to_phone, agent_config, synth_config, caller, twilio_config)

    # Return the input parameters in the response
    return {"status": "success", "data": input_parameters}


uvicorn.run(app, host="0.0.0.0", port=3000)

LANGUAGES_TO_TIER_MODEL = {
    'es-419': ('nova', 'phonecall'),
    'es': ('nova', 'phonecall'),
    'en-US': ('nova', 'phonecall'),
    'en-NZ': ('nova', 'phonecall'),
    'en-IN': ('nova', 'phonecall'),
    'en-GB': ('nova', 'phonecall'),
    'en-AU': ('nova', 'phonecall'),
    # ... (and so on for all languages in the nova tier)
    'da': ('enhanced', 'phonecall'),
    'nl': ('enhanced', 'phonecall'),
    'fr': ('enhanced', 'phonecall'),
    'de': ('enhanced', 'phonecall'),
    'hi': ('enhanced', 'phonecall'),
    'it': ('enhanced', 'phonecall'),
    'ja': ('enhanced', 'phonecall'),
    'no': ('enhanced', 'phonecall'),
    'ko': ('enhanced', 'phonecall'),
    'no': ('enhanced', 'phonecall'),
    'pl': ('enhanced', 'phonecall'),
    'pt': ('enhanced', 'phonecall'),
    'pt-BR': ('enhanced', 'phonecall'), 
    'pt-PT': ('enhanced', 'phonecall'),
    'sv': ('enhanced', 'phonecall'),
    'ta': ('enhanced', 'phonecall'),
    # ... (and so on for all languages in the enhanced tier)
    'zh': ('base', 'phonecall'),
    'zh-CN': ('base', 'phonecall'),
    'zh-TW': ('base', 'phonecall'),
    'fr-CA': ('base', 'phonecall'),
    'id': ('base', 'phonecall'),
    'ru': ('base', 'phonecall'),
    'tr': ('base', 'phonecall'),
    'uk': ('base', 'phonecall'),
    # ... (and so on for all languages in the base tier)
}

def get_deepgram_config_for_language(language_code):
    tier, model = LANGUAGES_TO_TIER_MODEL.get(language_code, (None, None))
    if tier and model:
        return DeepgramTranscriberConfig(
            sampling_rate=DEFAULT_SAMPLING_RATE,
            audio_encoding=DEFAULT_AUDIO_ENCODING,
            chunk_size=DEFAULT_CHUNK_SIZE,
            model=model,
            min_interrupt_confidence=0.6,
            language=language_code,  # Assuming Deepgram accepts this as a parameter
            tier=tier
        )
    else:
        # Handle case where language isn't in our list, maybe raise an error or use a default
        pass
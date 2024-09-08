from aiohttp import web
import base64
import os
from datetime import datetime
import logging
import asyncio
from transformers import AutoModelForCausalLM, AutoTokenizer
from PIL import Image

import random
import time
import io
model_id = "vikhyatk/moondream2"
revision = "2024-08-26"



UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

EXPRESSION_ADJECTIVES = [
   "Happiness",
   "Sadness",
   "Anger",
   "Fear",
   "Surprise",
   "Disgust",
   "Contempt",
   "Embarrassment",
   "Excitement",
   "Guilt",
   "Pride",
   "Satisfaction",
   "Shame",
]
USER_SCORES = {
    "expression_matching": [],
    "eye_contact": [],
}

model = None
tokenizer = None
async def get_moondream():
    global model, tokenizer
    if model is not None:
        return model, tokenizer
    model = AutoModelForCausalLM.from_pretrained(
        model_id, trust_remote_code=True, revision=revision
    )
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)

    return model, tokenizer


async def grade_image(file_path: str, target_expression: str):
    model, tokenizer = await get_moondream()

    image = Image.open(file_path)
    start_ts = time.time()
    enc_image = model.encode_image(image)
    # print(model.answer_question(enc_image, "Describe this image.", tokenizer))
    eye_contact_answer = model.answer_question(enc_image, "Is this person looking at the camera? Start answer with Yes or No.", tokenizer)
    logging.info(eye_contact_answer)
    expression_answer = model.answer_question(enc_image, "Does this person look {target_expression}? Start answer with Yes or No.", tokenizer)
    logging.info(expression_answer)
    did_match = "yes" in expression_answer.lower()
    eye_contact = "yes" in eye_contact_answer.lower()
    end_ts = time.time()
    print(f"eval complete duration={end_ts-start_ts}")
    return did_match, eye_contact

async def generate_game(request: web.BaseRequest) -> web.Response:
    try:
        # use bag shuffle twice
        BAG_COUNT = 2
        goals = []
        for _ in range(BAG_COUNT):
            bag = EXPRESSION_ADJECTIVES.copy()
            random.shuffle(bag)
            goals.extend(bag)
        return web.json_response({
                            "goals": goals
        })
    except Exception as e:
        logging.exception(e)
        return web.Response(status=500)


async def handle_upload(request: web.BaseRequest) -> web.Response:
    try:
        reader = await request.multipart()
        
        # Get the image file
        field = await reader.next()
        assert field.name == 'image'
        image_bytes = await field.read()
        logging.info(f"Received image size: {len(image_bytes)} bytes")

        # Get the goal
        field = await reader.next()
        assert field.name == 'goal'
        expression = await field.text()

        if not image_bytes:
            return web.Response(status=400, text='no image received')

        
        # Generate a unique filename
        filename = f"webcam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # Save the image
        image = Image.open(io.BytesIO(image_bytes))
        image.save(filepath, 'JPEG')
        did_match, eye_contact = await grade_image(filepath, expression)
        return web.json_response({
                            "goal": expression,
                            "did_match": did_match,
                            "eye_contact": eye_contact
        })

    except Exception as e:
        logging.exception(e)
        return web.Response(status=500, text="Server error")

FRONTEND_DIR = "frontend"

async def init_app():
    app = web.Application()

    # Add static file handling
    app.router.add_static('/static/', path=FRONTEND_DIR, name='static')
    
    # Add route for the main page
    async def index(request):
        return web.FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))

    app.router.add_get('/', index)
    app.router.add_get('/start', generate_game);
    app.router.add_routes([web.post("/submit", handle_upload)])
    return app

if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    app = asyncio.get_event_loop().run_until_complete(init_app())
    web.run_app(app, host='0.0.0.0', port=3000)


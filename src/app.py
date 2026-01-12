import io
import base64
import pytesseract  # type: ignore
from PIL import Image, UnidentifiedImageError
from flask import Flask, render_template, request

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", title="Home")


@app.route("/results", methods=["POST"])
def result():
    try:
        data = request.form.get("data")
        if not data:
            return "Bad Request: No image data in request", 400

        if "," not in data:
            return "Bad Request: Invalid image data", 400

        image_data = base64.b64decode(data.split(",")[1])
        image = Image.open(io.BytesIO(image_data))
        text = pytesseract.image_to_string(image, lang='rus+eng')
        if not text:
            return "Bad Request: No text found in the image", 400

        text = "\n".join([line.strip() for line in text.split("\n") if line.strip()])

        return text, 200
    except UnidentifiedImageError:
        return "Bad Request: The image is not supported", 400
    except Exception as e:
        return f"Internal Server Error: {e}", 500

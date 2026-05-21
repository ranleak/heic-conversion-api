import io
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import RedirectResponse
import modal

# Define the environment and dependencies for Modal
image = modal.Image.debian_slim().pip_install(
    "fastapi",
    "python-multipart", # Required for handling File/Form uploads
    "pillow",
    "pillow-heif"       # Adds HEIC support to Pillow
)

# Initialize the Modal App and FastAPI
app = modal.App("heic-converter-app")
web_app = FastAPI(title="Advanced HEIC Converter API")

# New route for redirect
@web_app.get("/", include_in_schema=False)
async def redirect_to_docs():
    """Redirects the base URL to the interactive API documentation."""
    return RedirectResponse(url="/docs")

@web_app.post("/convert/")
async def convert_image(
    file: UploadFile = File(...),
    output_format: str = Form(default="jpeg", description="Output format: jpeg, png, or webp"),
    quality: int = Form(default=85, description="Image quality (1-100) for jpeg/webp"),
    optimize: bool = Form(default=True, description="Optimize output file size")
):
    """
    Upload a HEIC file and convert it to JPEG, PNG, or WebP.
    Includes advanced options for quality and optimization.
    """
    # Validate format
    output_format = output_format.lower()
    if output_format not in ["jpeg", "png", "webp"]:
        raise HTTPException(status_code=400, detail="Unsupported output format. Choose jpeg, png, or webp.")

    # Validate file extension roughly
    if not file.filename.lower().endswith(('.heic', '.heif')):
        raise HTTPException(status_code=400, detail="File must be a HEIC/HEIF image.")

    try:
        # Import inside the function so it executes properly in the Modal container
        from PIL import Image
        import pillow_heif

        # Register the HEIF opener with Pillow
        pillow_heif.register_heif_opener()

        # Read the uploaded file into memory
        file_bytes = await file.read()
        
        # Start the timer
        start_time = time.perf_counter()

        # Open the HEIC image
        img = Image.open(io.BytesIO(file_bytes))

        # Handle color modes (JPEG doesn't support RGBA/alpha channels)
        if output_format == "jpeg" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Process and save to a new memory buffer
        output_buffer = io.BytesIO()
        
        # PNG doesn't use the 'quality' kwarg in the same way, but it uses 'optimize'
        save_kwargs = {"format": output_format.upper(), "optimize": optimize}
        if output_format in ["jpeg", "webp"]:
            save_kwargs["quality"] = quality

        img.save(output_buffer, **save_kwargs)
        
        # Stop the timer
        end_time = time.perf_counter()
        conversion_time = round(end_time - start_time, 4)

        # Prepare the response
        output_buffer.seek(0)
        media_types = {
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp"
        }
        
        # Return the image with the conversion time injected into the headers
        return Response(
            content=output_buffer.getvalue(),
            media_type=media_types[output_format],
            headers={
                "Content-Disposition": f'attachment; filename="converted.{output_format}"',
                "X-Conversion-Time-Seconds": str(conversion_time)
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting image: {str(e)}")

# Bind the FastAPI app to Modal
@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    return web_app
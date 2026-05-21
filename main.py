import io
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import RedirectResponse
import modal

# Define the environment: Install system-level libvips and the Python wrapper
image = (
    modal.Image.debian_slim()
    .apt_install("libvips", "libvips-dev") # System libraries required for pyvips
    .pip_install(
        "fastapi",
        "python-multipart", 
        "pyvips"            # Replaces pillow and pillow-heif
    )
)

# Initialize the Modal App and FastAPI
app = modal.App("heic-converter-app")
web_app = FastAPI(title="Advanced HEIC Converter API")

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
    Upload a HEIC file and convert it to JPEG, PNG, or WebP using multi-core pyvips.
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
        import pyvips

        # Explicitly tell libvips to utilize the 8 CPU cores provisioned
        pyvips.concurrency_set(8)

        # Read the uploaded file into memory
        file_bytes = await file.read()
        
        # Start the timer
        start_time = time.perf_counter()

        # Load the HEIC image directly from the memory buffer
        img = pyvips.Image.new_from_buffer(file_bytes, "")

        # Process and output to a new memory buffer based on the requested format
        if output_format == "jpeg":
            # JPEG does not support alpha channels. Flatten against a white background.
            if img.hasalpha():
                img = img.flatten(background=[255, 255, 255])
            
            output_bytes = img.jpegsave_buffer(Q=quality, optimize_coding=optimize)
            
        elif output_format == "webp":
            output_bytes = img.webpsave_buffer(Q=quality)
            
        elif output_format == "png":
            # PNG doesn't use the standard 'Q' parameter in pyvips; it uses 'compression'.
            # We map the 'optimize' toggle to max compression (9) or standard (6).
            compression_level = 9 if optimize else 6
            output_bytes = img.pngsave_buffer(compression=compression_level)

        # Stop the timer
        end_time = time.perf_counter()
        conversion_time = round(end_time - start_time, 4)

        # Prepare the response
        media_types = {
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp"
        }
        
        # Return the image with the conversion time injected into the headers
        return Response(
            content=output_bytes,
            media_type=media_types[output_format],
            headers={
                "Content-Disposition": f'attachment; filename="converted.{output_format}"',
                "X-Conversion-Time-Seconds": str(conversion_time)
            }
        )

    except pyvips.Error as e:
        # Catch specific pyvips C-bindings errors
        raise HTTPException(status_code=500, detail=f"Image processing error: {e.args}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting image: {str(e)}")

# Bind the FastAPI app to Modal
@app.function(
    image=image,
    cpu=8.0,
    memory=2048
)
@modal.asgi_app()
def fastapi_app():
    return web_app
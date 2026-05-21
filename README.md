# Serverless HEIC Image Converter

A serverless FastAPI application to be deployed on [Modal.com](https://modal.com) that converts Apple's HEIC/HEIF images to standard web-friendly formats (JPEG, PNG, WebP).

It features advanced optimization options, handles alpha channel preservation (where applicable), and returns the processing time via custom HTTP headers.

## Features

- **Serverless Scaling:** Runs completely on Modal's serverless infrastructure.
- **Native HEIC Support:** Uses `pillow-heif` to read HEIC formats efficiently.
- **Advanced Options:** Control output format, image quality, and file optimization.
- **Performance Metrics:** Returns exact conversion time in the response headers.
- **Interactive UI:** Includes an automatic Swagger UI via FastAPI.

## Prerequisites

1. Python 3.8
2. A [Modal](https://modal.com) account
3. Modal CLI installed and authenticated:
   ```
   pip install modal
   modal setup
   ```

## Running and Deploying

### Development Mode

To run the app dynamically and watch for local file changes, use the `serve` command. Modal will provide a temporary HTTPS URL.

```
modal serve main.py
```

### Production Deployment

To deploy the app permanently to your Modal workspace:

```
modal deploy main.py
```

## API Reference

### Main Endpoint

`POST /convert/`
Uploads a HEIC file and returns the converted image.

### Form Data Parameters

| Parameter       | Type         | Default      | Description                                                     |
| :-------------- | :----------- | :----------- | :-------------------------------------------------------------- |
| `file`          | `UploadFile` | **Required** | The `.heic` or `.heif` image file to convert.                   |
| `output_format` | `string`     | `jpeg`       | The desired output format (`jpeg`, `png`, or `webp`).           |
| `quality`       | `int`        | `85`         | Image quality from `1` to `100` (applies to `jpeg` and `webp`). |
| `optimize`      | `boolean`    | `true`       | Apply secondary file size optimization during save.             |

### Response Headers

Along with the binary file download, the API attaches the following custom header:

- `X-Conversion-Time-Seconds`: The exact time (in seconds) it took the server to decode and encode the image.

## Usage Examples

### 1. Using Swagger UI (Interactive)

Once your Modal app is running, navigate to: `https://<YOUR_MODAL_WORKSPACE>--heic-converter-app-fastapi-app.modal.run/docs`.

From there, you can visually upload files, tweak parameters, and download the converted images directly in your browser.

### 2. Using cURL

You can hit the API directly from your terminal. _(Note: The `-i` flag ensures the response headers, including the conversion time, are printed to your terminal.)_

```
curl -X POST "https://<YOUR_MODAL_WORKSPACE>--heic-converter-app-fastapi-app.modal.run/convert/" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@my_vacation_photo.HEIC" \
  -F "output_format=webp" \
  -F "quality=90" \
  -F "optimize=true" \
  -i \
  --output converted_photo.webp
```

### 3. Using Python (Requests)

```python
import requests

url = "https://<YOUR_MODAL_WORKSPACE>--heic-converter-app-fastapi-app.modal.run/convert/"

with open("image.heic", "rb") as f:
    files = {"file": ("image.heic", f, "image/heic")}
    data = {
        "output_format": "jpeg",
        "quality": 85,
        "optimize": True
    }

    response = requests.post(url, files=files, data=data)

if response.status_code == 200:
    # Save the output image
    with open("output.jpg", "wb") as out_file:
        out_file.write(response.content)

    # Read the custom header
    print(f"Conversion took: {response.headers.get('X-Conversion-Time-Seconds')}s")
else:
    print(f"Error: {response.text}")
```

Enjoy! Made with ❤ in North Carolina, by a developer for developers.

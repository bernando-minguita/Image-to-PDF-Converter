# Image to PDF Converter

A desktop image-to-PDF converter built with Python and Tkinter, with a modern light UI.

## Features

- Add multiple images or add every supported image in a folder
- Reorder pages using the up/down controls or `Ctrl + Up` / `Ctrl + Down`
- Remove selected images or clear the list
- Output path selection
- Page sizes: Fit to image, A4, Letter, A3
- Orientation: Auto, Portrait, Landscape
- Adjustable margins
- Quality options
- Progress indicator and clear error messages
- Open the resulting PDF from the app
- All processing is local

## Supported formats

JPG/JPEG, PNG, BMP, TIFF, WEBP, GIF, and other image formats Pillow can read. For animated or multi-frame images, only the first frame is used.

## Requirements

- Python 3.10 or newer
- Pillow

## Setup on Windows

1. Extract the ZIP to a folder.
2. Double-click `install_dependencies.bat` once to install Pillow.
3. Double-click `run_app.bat` to start the application.

You can also run it from a terminal:

```bat
py image_to_pdf.py
```

If Pillow is already installed, skip the installation step.

## Notes

- If the destination PDF already exists, the app asks before replacing it.
- The application creates the output directory if it does not exist.
- Images are converted to RGB for PDF compatibility.
